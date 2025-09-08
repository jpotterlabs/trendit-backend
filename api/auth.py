from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from passlib.context import CryptContext
from datetime import datetime, timedelta, timezone
import secrets
import hashlib
import jwt
import os
from typing import Optional
from sqlalchemy import func, and_

from models.database import get_db
from models.models import User, APIKey, SubscriptionStatus, PaddleSubscription, SubscriptionTier, UsageRecord

router = APIRouter(prefix="/auth", tags=["authentication"])

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT settings
SECRET_KEY = os.getenv("JWT_SECRET_KEY")
if not SECRET_KEY:
    raise RuntimeError("JWT_SECRET_KEY must be set in environment variables")
ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "30"))

security = HTTPBearer()

# Pydantic models for requests/responses
class UserRegister(BaseModel):
    email: EmailStr
    password: str
    username: Optional[str] = None

class UserLogin(BaseModel):
    email: EmailStr
    password: str
    username: Optional[str] = None  # Allow optional username field from frontend

class UserResponse(BaseModel):
    id: int
    email: str
    username: Optional[str]
    is_active: bool
    subscription_status: str
    created_at: datetime

class Token(BaseModel):
    access_token: str
    token_type: str

class APIKeyRequest(BaseModel):
    name: str

class APIKeyResponse(BaseModel):
    id: int
    name: str
    key: str  # Only returned once during creation
    created_at: datetime
    expires_at: Optional[datetime]

class APIKeyListResponse(BaseModel):
    id: int
    name: str
    is_active: bool
    created_at: datetime
    expires_at: Optional[datetime]
    last_used_at: Optional[datetime]

class AdminTestUserRequest(BaseModel):
    admin_key: str

# Utility functions
def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def generate_api_key() -> tuple[str, str]:
    """Generate API key and its hash. Returns (raw_key, hashed_key)"""
    raw_key = f"tk_{secrets.token_urlsafe(32)}"  # tk_ prefix for Trendit Key
    hashed_key = hashlib.sha256(raw_key.encode()).hexdigest()
    return raw_key, hashed_key

# Dependency functions
async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """Get current user from JWT token"""
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user = db.query(User).filter(User.id == int(user_id)).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account is inactive",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user

async def get_current_user_from_api_key(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """Get current user from API key"""
    if not credentials.credentials.startswith("tk_"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key format",
        )
    
    # Hash the provided key to compare with stored hash
    key_hash = hashlib.sha256(credentials.credentials.encode()).hexdigest()
    
    # Check API key with proper SQLAlchemy syntax and expiry enforcement
    now = datetime.now(timezone.utc)
    api_key = db.query(APIKey).filter(
        and_(
            APIKey.key_hash == key_hash,
            APIKey.is_active.is_(True),
            (APIKey.expires_at.is_(None)) | (APIKey.expires_at > now),
        )
    ).first()
    
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
        )
    
    # Update last used timestamp
    api_key.last_used_at = datetime.now(timezone.utc)
    db.commit()
    
    user = db.query(User).filter(User.id == api_key.user_id).first()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is inactive",
        )
    
    return user

def _get_user_tier_limits(user: User, db: Session) -> tuple[SubscriptionTier, dict]:
    """Get user's subscription tier and usage limits"""
    # Import here to avoid circular imports
    from services.paddle_service import paddle_service
    
    # Check if user has an active Paddle subscription
    paddle_subscription = db.query(PaddleSubscription).filter(
        PaddleSubscription.user_id == user.id,
        PaddleSubscription.status == SubscriptionStatus.ACTIVE
    ).first()
    
    if paddle_subscription:
        tier = paddle_subscription.tier
        limits = paddle_service.get_tier_limits(tier)
    else:
        # Default to FREE tier for users without subscription
        tier = SubscriptionTier.FREE
        limits = paddle_service.get_tier_limits(tier)
    
    return tier, limits

def _get_current_usage(user_id: int, usage_type: str, period_start: datetime, db: Session) -> int:
    """Get current usage for user in current billing period"""
    return db.query(func.count(UsageRecord.id)).filter(
        UsageRecord.user_id == user_id,
        UsageRecord.usage_type == usage_type,
        UsageRecord.created_at >= period_start
    ).scalar() or 0

def _calculate_billing_period(user: User, db: Session) -> tuple[datetime, datetime]:
    """Calculate billing period for user"""
    from services.paddle_service import paddle_service
    
    paddle_subscription = db.query(PaddleSubscription).filter(
        PaddleSubscription.user_id == user.id,
        PaddleSubscription.status == SubscriptionStatus.ACTIVE
    ).first()
    
    if paddle_subscription:
        return paddle_service.calculate_billing_period(paddle_subscription)
    else:
        # Use calendar month for free users
        now = datetime.utcnow()
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        if now.month == 12:
            next_month = month_start.replace(year=now.year + 1, month=1)
        else:
            next_month = month_start.replace(month=now.month + 1)
        return month_start, next_month

def _record_usage(user: User, usage_type: str, endpoint: str, period_start: datetime, period_end: datetime, db: Session):
    """Record usage event"""
    # Get subscription ID if exists
    paddle_subscription = db.query(PaddleSubscription).filter(
        PaddleSubscription.user_id == user.id,
        PaddleSubscription.status == SubscriptionStatus.ACTIVE
    ).first()
    
    subscription_id = paddle_subscription.id if paddle_subscription else None
    
    usage_record = UsageRecord(
        user_id=user.id,
        subscription_id=subscription_id,
        usage_type=usage_type,
        endpoint=endpoint,
        billing_period_start=period_start,
        billing_period_end=period_end,
        request_metadata={}
    )
    db.add(usage_record)
    db.commit()

async def require_active_subscription_with_usage_tracking(
    usage_type: str,
    endpoint: str,
    user: User = Depends(get_current_user_from_api_key),
    db: Session = Depends(get_db)
) -> User:
    """
    Enhanced subscription check with usage tracking and rate limiting
    
    Args:
        usage_type: Type of usage (api_call, export, sentiment_analysis)
        endpoint: Endpoint name for tracking
        user: Authenticated user
        db: Database session
        
    Returns:
        User object if access is allowed
        
    Raises:
        HTTPException: If subscription inactive or usage limits exceeded
    """
    # Get user's tier and limits
    tier, limits = _get_user_tier_limits(user, db)
    
    # Calculate billing period
    period_start, period_end = _calculate_billing_period(user, db)
    
    # Check current usage
    current_usage = _get_current_usage(user.id, usage_type, period_start, db)
    
    # Get usage limit for this type
    usage_limit_key = f"{usage_type}_per_month"
    usage_limit = limits.get(usage_limit_key, 0)
    
    # Check if user has exceeded limits (-1 means unlimited for enterprise)
    if usage_limit != -1 and current_usage >= usage_limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Usage limit exceeded. {current_usage}/{usage_limit} {usage_type} used this month. Upgrade your plan for higher limits.",
            headers={
                "X-RateLimit-Limit": str(usage_limit),
                "X-RateLimit-Remaining": str(max(0, usage_limit - current_usage)),
                "X-RateLimit-Reset": str(int(period_end.timestamp())),
                "X-User-Tier": tier.value
            }
        )
    
    # For free users, ensure they have basic subscription check
    if tier == SubscriptionTier.FREE and user.subscription_status != SubscriptionStatus.ACTIVE:
        # Allow free tier usage but warn about limits
        pass
    elif tier != SubscriptionTier.FREE and user.subscription_status != SubscriptionStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="Active subscription required to access this endpoint",
        )
    
    # Record the usage
    _record_usage(user, usage_type, endpoint, period_start, period_end, db)
    
    # Add usage info to response headers for API consumers
    user._usage_info = {
        "tier": tier.value,
        "current_usage": current_usage + 1,  # Include this request
        "usage_limit": usage_limit,
        "period_start": period_start.isoformat(),
        "period_end": period_end.isoformat()
    }
    
    return user

# Convenience dependency functions for different usage types
async def require_api_call_limit(
    user: User = Depends(get_current_user_from_api_key),
    db: Session = Depends(get_db)
) -> User:
    """Check API call limits"""
    return await require_active_subscription_with_usage_tracking(
        "api_calls", "general_api", user, db
    )

async def require_export_limit(
    user: User = Depends(get_current_user_from_api_key),
    db: Session = Depends(get_db)
) -> User:
    """Check export limits"""
    return await require_active_subscription_with_usage_tracking(
        "exports", "data_export", user, db
    )

async def require_sentiment_limit(
    user: User = Depends(get_current_user_from_api_key),
    db: Session = Depends(get_db)
) -> User:
    """Check sentiment analysis limits"""
    return await require_active_subscription_with_usage_tracking(
        "sentiment_analysis", "sentiment_api", user, db
    )

# Legacy function for backward compatibility
async def require_active_subscription(
    user: User = Depends(get_current_user_from_api_key)
) -> User:
    """Legacy subscription check - use specific usage tracking functions instead"""
    if user.subscription_status != SubscriptionStatus.ACTIVE:
        # Allow free tier users for now, but this should be migrated
        pass
    return user

# Authentication endpoints
@router.post("/register", response_model=UserResponse)
async def register(user_data: UserRegister, db: Session = Depends(get_db)):
    """Register a new user account"""
    # Check if user already exists
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create new user
    hashed_password = hash_password(user_data.password)
    db_user = User(
        email=user_data.email,
        username=user_data.username or user_data.email.split("@")[0],
        password_hash=hashed_password,
        is_active=True,
        subscription_status=SubscriptionStatus.INACTIVE
    )
    
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    return UserResponse(
        id=db_user.id,
        email=db_user.email,
        username=db_user.username,
        is_active=db_user.is_active,
        subscription_status=db_user.subscription_status.value,
        created_at=db_user.created_at
    )

@router.post("/login", response_model=Token)
async def login(user_credentials: UserLogin, db: Session = Depends(get_db)):
    """Login and receive access token"""
    user = db.query(User).filter(User.email == user_credentials.email).first()
    
    if not user or not verify_password(user_credentials.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account is inactive"
        )
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(user.id)}, expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer"}

# API Key management endpoints
@router.post("/api-keys", response_model=APIKeyResponse)
async def create_api_key(
    key_request: APIKeyRequest, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)  # We'll define this dependency
):
    """Create a new API key for the authenticated user"""
    raw_key, hashed_key = generate_api_key()
    
    db_api_key = APIKey(
        user_id=current_user.id,
        key_hash=hashed_key,
        name=key_request.name,
        is_active=True
    )
    
    db.add(db_api_key)
    db.commit()
    db.refresh(db_api_key)
    
    return APIKeyResponse(
        id=db_api_key.id,
        name=db_api_key.name,
        key=raw_key,  # Only returned once!
        created_at=db_api_key.created_at,
        expires_at=db_api_key.expires_at
    )

@router.get("/api-keys", response_model=list[APIKeyListResponse])
async def list_api_keys(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all API keys for the authenticated user (without revealing the keys)"""
    api_keys = db.query(APIKey).filter(APIKey.user_id == current_user.id).all()
    
    return [
        APIKeyListResponse(
            id=key.id,
            name=key.name,
            is_active=key.is_active,
            created_at=key.created_at,
            expires_at=key.expires_at,
            last_used_at=key.last_used_at
        )
        for key in api_keys
    ]

@router.delete("/api-keys/{key_id}")
async def delete_api_key(
    key_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete an API key"""
    api_key = db.query(APIKey).filter(
        APIKey.id == key_id,
        APIKey.user_id == current_user.id
    ).first()
    
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found"
        )
    
    db.delete(api_key)
    db.commit()
    
    return {"message": "API key deleted successfully"}

# Admin/Testing endpoints
@router.post("/create-test-user")
async def create_test_user(
    request: AdminTestUserRequest,
    db: Session = Depends(get_db)
) -> dict:
    """Create a test user with predefined credentials (admin only)"""
    # Check admin key
    expected_admin_key = os.getenv("ADMIN_SECRET_KEY")
    if not expected_admin_key or request.admin_key != expected_admin_key:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid admin key"
        )
    
    # Define test user credentials
    test_email = "test@trendit.dev"
    test_password = "TestPassword123"  # nosec B105 - Intentional test password for admin endpoint
    test_username = "trendit_tester"
    
    # Check if test user already exists
    existing_user = db.query(User).filter(User.email == test_email).first()
    if existing_user:
        # Update existing user to ensure it's active with known password
        existing_user.password_hash = hash_password(test_password)
        existing_user.is_active = True
        existing_user.subscription_status = SubscriptionStatus.ACTIVE  # Give active subscription for testing
        db.commit()
        db.refresh(existing_user)
        
        # Create a new API key for the user (atomic operation)
        raw_key, hashed_key = generate_api_key()
        
        # Delete old API keys and create new one atomically
        db.query(APIKey).filter(APIKey.user_id == existing_user.id).delete(synchronize_session=False)
        
        db_api_key = APIKey(
            user_id=existing_user.id,
            key_hash=hashed_key,
            name="Test API Key",
            is_active=True
        )
        db.add(db_api_key)
        db.commit()
        
        return {
            "message": "Test user updated successfully",
            "user": {
                "id": existing_user.id,
                "email": test_email,
                "username": test_username,
                "password": test_password
            },
            "api_key": raw_key
        }
    
    # Create new test user
    hashed_password = hash_password(test_password)
    db_user = User(
        email=test_email,
        username=test_username,
        password_hash=hashed_password,
        is_active=True,
        subscription_status=SubscriptionStatus.ACTIVE  # Give active subscription for testing
    )
    
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    # Create API key for the test user
    raw_key, hashed_key = generate_api_key()
    
    db_api_key = APIKey(
        user_id=db_user.id,
        key_hash=hashed_key,
        name="Test API Key",
        is_active=True
    )
    
    db.add(db_api_key)
    db.commit()
    
    return {
        "message": "Test user created successfully",
        "user": {
            "id": db_user.id,
            "email": test_email,
            "username": test_username,
            "password": test_password
        },
        "api_key": raw_key
    }
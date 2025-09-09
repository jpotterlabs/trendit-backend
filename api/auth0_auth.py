"""
Auth0 Authentication Endpoints for Trendit

Provides Auth0 OAuth integration endpoints that work alongside existing auth system
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, Dict, Any
from models.database import get_db
from models.models import User, APIKey, SubscriptionStatus
from services.auth0_service import auth0_service
from api.auth import create_access_token, generate_api_key
import logging

logger = logging.getLogger(__name__)

# Security scheme for Auth0 Bearer tokens
auth0_bearer = HTTPBearer(auto_error=False)

router = APIRouter(prefix="/auth0", tags=["Auth0 Authentication"])

class Auth0CallbackRequest(BaseModel):
    """Request model for Auth0 callback with access token"""
    access_token: str
    id_token: Optional[str] = None

class Auth0LoginResponse(BaseModel):
    """Response model for successful Auth0 login"""
    message: str
    user: Dict[str, Any]
    jwt_token: str
    api_key: str

class Auth0UserInfo(BaseModel):
    """User info from Auth0"""
    sub: str
    email: str
    name: Optional[str] = None
    picture: Optional[str] = None
    email_verified: Optional[bool] = None

# Dependency: Get current user from Auth0 JWT token
async def get_current_auth0_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(auth0_bearer),
    db: Session = Depends(get_db)
) -> Optional[User]:
    """
    Dependency to get current user from Auth0 JWT token
    Returns None if no token or invalid token (for optional auth)
    """
    if not credentials:
        return None
    
    try:
        # Verify Auth0 JWT token
        claims = auth0_service.verify_jwt_token(credentials.credentials)
        
        # Get or create user from claims
        user = auth0_service.get_or_create_user(claims, db)
        
        return user
        
    except HTTPException:
        # Let the endpoint handle the error
        raise
    except Exception as e:
        logger.error(f"Auth0 authentication error: {e}")
        return None

# Dependency: Require Auth0 authentication
async def require_auth0_user(
    user: Optional[User] = Depends(get_current_auth0_user)
) -> User:
    """
    Dependency that requires Auth0 authentication
    Raises 401 if user is not authenticated
    """
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Auth0 authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user

@router.post("/callback", response_model=Auth0LoginResponse)
async def auth0_callback(
    callback_data: Auth0CallbackRequest,
    db: Session = Depends(get_db)
):
    """
    Handle Auth0 callback with access token
    
    This endpoint receives the access token from the frontend after successful OAuth,
    validates it with Auth0, creates/updates the user, and returns Trendit JWT + API key
    """
    try:
        # Verify the access token and get user info from Auth0
        user_info = auth0_service.get_user_info(callback_data.access_token)
        
        logger.info(f"Auth0 callback for user_id: {user_info.get('sub')}")
        
        # Create user claims format expected by get_or_create_user
        auth0_claims = {
            "sub": user_info.get("sub"),
            "email": user_info.get("email"),
            "name": user_info.get("name"),
            "picture": user_info.get("picture"),
            "email_verified": user_info.get("email_verified", False)
        }
        
        # Get or create user in our database
        user = auth0_service.get_or_create_user(auth0_claims, db)
        
        # Generate Trendit JWT token (same as existing auth system)
        jwt_token = create_access_token({"sub": str(user.id)})
        
        # Check if user has an API key, create one if not
        existing_api_key = db.query(APIKey).filter(
            APIKey.user_id == user.id,
            APIKey.is_active.is_(True),
            APIKey.name.in_(["Auth0 Login Key", "Auth0 Login Key (Renewed)"])
        ).first()
        
        if existing_api_key:
            # Rotate: deactivate old key and create a new one (keeps audit fields)
            existing_api_key.is_active = False
            raw_key, key_hash = generate_api_key()
            
            new_api_key = APIKey(
                user_id=user.id,
                name="Auth0 Login Key (Renewed)",
                key_hash=key_hash,
                is_active=True
            )
            db.add(new_api_key)
            db.commit()
            
            api_key = raw_key
        else:
            # Create new API key using existing system
            raw_key, key_hash = generate_api_key()
            
            new_api_key = APIKey(
                user_id=user.id,
                name="Auth0 Login Key",
                key_hash=key_hash,
                is_active=True
            )
            db.add(new_api_key)
            db.commit()
            
            api_key = raw_key
        
        # Prepare user info for response
        user_data = {
            "id": user.id,
            "email": user.email,
            "username": user.username,
            "subscription_status": user.subscription_status.value,
            "auth0_provider": user.auth0_provider,
            "created_at": user.created_at.isoformat()
        }
        
        logger.info(f"Auth0 login successful for user_id={user.id} via {user.auth0_provider}")
        
        return Auth0LoginResponse(
            message="Login successful",
            user=user_data,
            jwt_token=jwt_token,
            api_key=api_key
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Auth0 callback error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process Auth0 callback"
        )

@router.get("/userinfo")
async def get_auth0_user_info(
    current_user: User = Depends(require_auth0_user)
):
    """
    Get current user information (for Auth0 authenticated users)
    """
    return {
        "id": current_user.id,
        "email": current_user.email,
        "username": current_user.username,
        "subscription_status": current_user.subscription_status.value,
        "auth0_provider": current_user.auth0_provider,
        "created_at": current_user.created_at.isoformat()
    }

@router.post("/refresh")
async def refresh_auth0_session(
    current_user: User = Depends(require_auth0_user),
    db: Session = Depends(get_db)
):
    """
    Refresh JWT token for Auth0 authenticated user
    """
    # Generate new JWT token
    jwt_token = create_access_token({"sub": str(current_user.id)})
    
    # Get user's API key
    api_key_record = db.query(APIKey).filter(
        APIKey.user_id == current_user.id,
        APIKey.is_active == True
    ).first()
    
    api_key = api_key_record.key_hash[:8] + "..." if api_key_record else None
    
    return {
        "message": "Token refreshed",
        "jwt_token": jwt_token,
        "api_key": api_key
    }

# Health check endpoint for Auth0 integration
@router.get("/health")
async def auth0_health_check():
    """Check Auth0 service health"""
    try:
        # Try to fetch JWKS to verify Auth0 connectivity
        jwks = auth0_service.get_jwks()
        
        return {
            "status": "healthy",
            "auth0_domain": auth0_service.domain,
            "jwks_keys": len(jwks.get("keys", [])),
            "message": "Auth0 integration is working"
        }
    except Exception as e:
        logger.error(f"Auth0 health check failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Auth0 service unavailable"
        )
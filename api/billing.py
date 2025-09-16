"""
Trendit Billing API Endpoints

Provides subscription management functionality integrated with Paddle Billing:
- Checkout session creation
- Subscription status and management
- Upgrade/downgrade operations
- Usage analytics and limits
- Customer portal access

All endpoints require API key authentication and integrate with existing
subscription gating system.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from pydantic import BaseModel, Field
import logging

from models.database import get_db
from models.models import (
    User, PaddleSubscription, SubscriptionTier, SubscriptionStatus,
    UsageRecord, BillingEvent
)
from services.paddle_service import paddle_service
from api.auth import get_current_user_from_api_key, require_subscription_api_limit
from sqlalchemy import func

router = APIRouter(prefix="/api/billing", tags=["billing"])
logger = logging.getLogger(__name__)

# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class CheckoutRequest(BaseModel):
    """Request to create checkout session"""
    tier: SubscriptionTier = Field(..., description="Subscription tier to purchase")
    trial_days: Optional[int] = Field(None, ge=0, le=30, description="Optional trial period in days")
    success_url: Optional[str] = Field(None, description="Success redirect URL")
    cancel_url: Optional[str] = Field(None, description="Cancel redirect URL")

class CheckoutResponse(BaseModel):
    """Checkout session response"""
    checkout_url: str
    tier: str
    price: float
    trial_days: Optional[int] = None
    expires_at: Optional[str] = None

class SubscriptionStatusResponse(BaseModel):
    """Current subscription status and usage"""
    tier: str
    status: str
    current_period_end: Optional[str] = None
    next_billed_at: Optional[str] = None
    price_per_month: float
    currency: str = "USD"
    
    # Usage limits
    limits: Dict[str, int]
    
    # Current usage
    current_usage: Dict[str, int]
    usage_percentage: Dict[str, float]
    
    # Trial information
    is_trial: bool = False
    trial_end_date: Optional[str] = None
    
    # Management URLs
    customer_portal_url: Optional[str] = None

class UpgradeRequest(BaseModel):
    """Request to upgrade/downgrade subscription"""
    new_tier: SubscriptionTier = Field(..., description="Target subscription tier")

class UsageAnalyticsResponse(BaseModel):
    """Detailed usage analytics"""
    billing_period: Dict[str, str]
    daily_usage: Dict[str, Dict[str, int]]
    endpoint_usage: Dict[str, int]
    total_usage_this_period: Dict[str, int]
    usage_trends: Dict[str, Any]

# ============================================================================
# SUBSCRIPTION MANAGEMENT ENDPOINTS
# ============================================================================

@router.post("/checkout/create", response_model=CheckoutResponse)
async def create_checkout_session(
    request: CheckoutRequest,
    current_user: User = Depends(get_current_user_from_api_key),
    db: Session = Depends(get_db)
):
    """Create Paddle checkout session for subscription upgrade
    
    Creates a secure checkout session with Paddle for the specified tier.
    Handles existing subscription checks and customer creation.
    """
    try:
        # Validate Paddle service configuration
        if not paddle_service.is_configured():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Billing service is not properly configured"
            )
        
        # Check if user already has active subscription of same or higher tier
        if current_user.paddle_subscription:
            current_tier = current_user.paddle_subscription.tier
            current_status = current_user.paddle_subscription.status
            
            if (current_status == SubscriptionStatus.ACTIVE and
                current_tier != SubscriptionTier.FREE):
                
                # Check if trying to downgrade
                tier_order = {SubscriptionTier.FREE: 0, SubscriptionTier.PRO: 1, SubscriptionTier.PREMIUM: 2}
                if tier_order[request.tier] <= tier_order[current_tier]:
                    return {
                        "error": "subscription_conflict",
                        "message": f"Already subscribed to {current_tier.value} tier",
                        "current_tier": current_tier.value,
                        "current_status": current_status.value,
                        "customer_portal_url": current_user.paddle_subscription.customer_portal_url
                    }
        
        # Set default URLs if not provided
        success_url = request.success_url or "https://trendit.com/billing/success"
        cancel_url = request.cancel_url or "https://trendit.com/billing/cancel"
        
        # Create or get Paddle customer
        if (not current_user.paddle_subscription or 
            not current_user.paddle_subscription.paddle_customer_id):
            
            customer_data = await paddle_service.create_customer(current_user)
            customer_id = customer_data["data"]["id"]
            
            # Create or update local subscription record
            if not current_user.paddle_subscription:
                paddle_subscription = PaddleSubscription(
                    user_id=current_user.id,
                    paddle_customer_id=customer_id,
                    tier=SubscriptionTier.FREE  # Will be updated after payment
                )
                db.add(paddle_subscription)
            else:
                current_user.paddle_subscription.paddle_customer_id = customer_id
            
            db.commit()
            db.refresh(current_user)
        
        # Create checkout URL
        checkout_url = await paddle_service.create_checkout_url(
            user=current_user,
            tier=request.tier,
            success_url=success_url,
            cancel_url=cancel_url,
            trial_days=request.trial_days
        )
        
        # Get tier pricing
        tier_config = paddle_service.tier_config[request.tier]
        
        logger.info(f"Created checkout session for user {current_user.id}, tier {request.tier.value}")
        
        return CheckoutResponse(
            checkout_url=checkout_url,
            tier=request.tier.value,
            price=tier_config["price"],
            trial_days=request.trial_days,
            expires_at=(datetime.utcnow() + timedelta(hours=1)).isoformat()  # Checkout expires in 1 hour
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Checkout creation failed for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create checkout session"
        )

@router.get("/subscription/status", response_model=SubscriptionStatusResponse)
async def get_subscription_status(
    current_user: User = Depends(require_subscription_api_limit),
    db: Session = Depends(get_db)
):
    """Get current user's subscription status and usage analytics
    
    Returns comprehensive subscription information including:
    - Current tier and billing status
    - Usage limits and current consumption
    - Trial information
    - Management URLs
    """
    try:
        # Get or create paddle subscription record
        if not current_user.paddle_subscription:
            paddle_subscription = PaddleSubscription(
                user_id=current_user.id,
                tier=SubscriptionTier.FREE,
                status=SubscriptionStatus.INACTIVE
            )
            db.add(paddle_subscription)
            db.commit()
            current_user.paddle_subscription = paddle_subscription
        
        subscription = current_user.paddle_subscription
        
        # Get tier limits
        tier_limits = paddle_service.get_tier_limits(subscription.tier)
        
        # Calculate current billing period
        period_start, period_end = paddle_service.calculate_billing_period(subscription)
        
        # Get current usage for this billing period
        current_usage = {}
        usage_percentage = {}
        
        for usage_type in ["api_call", "export", "sentiment_analysis"]:
            # Query usage for current billing period
            usage_count = db.query(func.sum(UsageRecord.cost_units)).filter(
                UsageRecord.user_id == current_user.id,
                UsageRecord.usage_type == usage_type,
                UsageRecord.billing_period_start >= period_start,
                UsageRecord.billing_period_end <= period_end
            ).scalar() or 0
            
            current_usage[usage_type] = int(usage_count)
            
            # Calculate usage percentage
            limit_key = f"{usage_type.replace('_', '_')}s_per_month" if usage_type.endswith("_call") else f"{usage_type.replace('_', '_')}_per_month"
            if limit_key == "api_calls_per_month":
                limit_key = "api_calls_per_month"
            elif limit_key == "exports_per_month":
                limit_key = "exports_per_month"
            elif limit_key == "sentiment_analysiss_per_month":
                limit_key = "sentiment_analysis_per_month"
            
            limit = tier_limits.get(limit_key, 0)
            usage_percentage[usage_type] = (usage_count / limit * 100) if limit > 0 else 0
        
        return SubscriptionStatusResponse(
            tier=subscription.tier.value,
            status=subscription.status.value,
            current_period_end=subscription.current_period_end.isoformat() if subscription.current_period_end else None,
            next_billed_at=subscription.next_billed_at.isoformat() if subscription.next_billed_at else None,
            price_per_month=subscription.price_per_month or 0.0,
            currency=subscription.currency,
            limits=tier_limits,
            current_usage=current_usage,
            usage_percentage=usage_percentage,
            is_trial=subscription.is_trial,
            trial_end_date=subscription.trial_end_date.isoformat() if subscription.trial_end_date else None,
            customer_portal_url=subscription.customer_portal_url
        )
        
    except Exception as e:
        logger.error(f"Failed to get subscription status for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve subscription status"
        )

@router.post("/subscription/upgrade")
async def upgrade_subscription(
    request: UpgradeRequest,
    current_user: User = Depends(get_current_user_from_api_key),
    db: Session = Depends(get_db)
):
    """Upgrade or downgrade existing subscription
    
    Modifies the current Paddle subscription to the new tier.
    Handles proration and billing cycle adjustments automatically.
    """
    try:
        if (not current_user.paddle_subscription or 
            not current_user.paddle_subscription.paddle_subscription_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No active subscription found. Please create a new subscription first."
            )
        
        subscription = current_user.paddle_subscription
        
        # Handle downgrade to FREE tier (cancellation)
        if request.new_tier == SubscriptionTier.FREE:
            await paddle_service.cancel_subscription(subscription.paddle_subscription_id)
            return {
                "message": "Subscription will be cancelled at the end of current billing period",
                "current_period_end": subscription.current_period_end.isoformat() if subscription.current_period_end else None,
                "new_tier": "free"
            }
        
        # Handle upgrade/downgrade between paid tiers
        subscription_data = await paddle_service.update_subscription(
            subscription.paddle_subscription_id,
            request.new_tier
        )
        
        # Update local database (webhook will also update, but this provides immediate response)
        subscription.tier = request.new_tier
        tier_limits = paddle_service.get_tier_limits(request.new_tier)
        subscription.monthly_api_calls_limit = tier_limits["api_calls_per_month"]
        subscription.monthly_exports_limit = tier_limits["exports_per_month"] 
        subscription.monthly_sentiment_limit = tier_limits["sentiment_analysis_per_month"]
        subscription.data_retention_days = tier_limits["data_retention_days"]
        subscription.price_per_month = paddle_service.tier_config[request.new_tier]["price"]
        
        db.commit()
        
        logger.info(f"Upgraded subscription for user {current_user.id} to {request.new_tier.value}")
        
        return {
            "message": "Subscription updated successfully",
            "new_tier": request.new_tier.value,
            "new_price": subscription.price_per_month,
            "effective_immediately": True
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Subscription upgrade failed for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upgrade subscription"
        )

@router.post("/subscription/cancel")
async def cancel_subscription(
    current_user: User = Depends(get_current_user_from_api_key),
    db: Session = Depends(get_db)
):
    """Cancel subscription at end of current billing period
    
    Schedules cancellation with Paddle. User retains access until
    the end of their current billing period.
    """
    try:
        if (not current_user.paddle_subscription or 
            not current_user.paddle_subscription.paddle_subscription_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No active subscription found"
            )
        
        subscription = current_user.paddle_subscription
        
        if subscription.status != SubscriptionStatus.ACTIVE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot cancel subscription with status: {subscription.status.value}"
            )
        
        # Cancel with Paddle
        await paddle_service.cancel_subscription(subscription.paddle_subscription_id)
        
        logger.info(f"Initiated cancellation for user {current_user.id}")
        
        return {
            "message": "Subscription will be cancelled at the end of current billing period",
            "current_period_end": subscription.current_period_end.isoformat() if subscription.current_period_end else None,
            "access_until": subscription.current_period_end.isoformat() if subscription.current_period_end else None,
            "can_reactivate": True
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Subscription cancellation failed for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to cancel subscription"
        )

# ============================================================================
# USAGE ANALYTICS ENDPOINTS
# ============================================================================

@router.get("/usage/analytics", response_model=UsageAnalyticsResponse)
async def get_usage_analytics(
    days: int = 30,
    current_user: User = Depends(get_current_user_from_api_key),
    db: Session = Depends(get_db)
):
    """Get detailed usage analytics for current user
    
    Provides comprehensive usage data including:
    - Daily usage breakdown
    - Endpoint-specific usage
    - Usage trends and projections
    """
    try:
        if not current_user.paddle_subscription:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No subscription record found"
            )
        
        subscription = current_user.paddle_subscription
        
        # Calculate billing period
        period_start, period_end = paddle_service.calculate_billing_period(subscription)
        
        # Calculate analytics date range
        analytics_start = datetime.utcnow() - timedelta(days=days)
        
        # Get usage records for the period
        usage_records = db.query(UsageRecord).filter(
            UsageRecord.user_id == current_user.id,
            UsageRecord.created_at >= analytics_start
        ).all()
        
        # Organize data by day and usage type
        daily_usage = {}
        endpoint_usage = {}
        total_usage_this_period = {}
        
        for record in usage_records:
            date_key = record.created_at.date().isoformat()
            
            # Daily usage breakdown
            if date_key not in daily_usage:
                daily_usage[date_key] = {}
            
            if record.usage_type not in daily_usage[date_key]:
                daily_usage[date_key][record.usage_type] = 0
            
            daily_usage[date_key][record.usage_type] += record.cost_units
            
            # Endpoint usage
            if record.endpoint not in endpoint_usage:
                endpoint_usage[record.endpoint] = 0
            endpoint_usage[record.endpoint] += record.cost_units
            
            # Total usage in current billing period
            if (record.billing_period_start >= period_start and
                record.billing_period_end <= period_end):
                
                if record.usage_type not in total_usage_this_period:
                    total_usage_this_period[record.usage_type] = 0
                total_usage_this_period[record.usage_type] += record.cost_units
        
        # Calculate usage trends
        usage_trends = {
            "average_daily_usage": {},
            "projected_monthly_usage": {},
            "busiest_day": None,
            "most_used_endpoint": max(endpoint_usage.items(), key=lambda x: x[1])[0] if endpoint_usage else None
        }
        
        # Calculate averages and projections
        for usage_type in total_usage_this_period:
            avg_daily = total_usage_this_period[usage_type] / max(days, 1)
            usage_trends["average_daily_usage"][usage_type] = round(avg_daily, 2)
            usage_trends["projected_monthly_usage"][usage_type] = round(avg_daily * 30, 0)
        
        return UsageAnalyticsResponse(
            billing_period={
                "start": period_start.isoformat(),
                "end": period_end.isoformat()
            },
            daily_usage=daily_usage,
            endpoint_usage=endpoint_usage,
            total_usage_this_period=total_usage_this_period,
            usage_trends=usage_trends
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Usage analytics failed for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve usage analytics"
        )

# ============================================================================
# UTILITY ENDPOINTS
# ============================================================================

@router.get("/tiers")
async def get_subscription_tiers():
    """Get available subscription tiers and pricing
    
    Returns public pricing information for all tiers.
    No authentication required.
    """
    return {
        "tiers": {
            "free": {
                "name": "Free",
                "price": 0,
                "currency": "USD",
                "interval": "month",
                "features": [
                    "100 API calls per month",
                    "5 data exports per month",
                    "50 sentiment analyses per month", 
                    "30-day data retention",
                    "Community support"
                ],
                "limits": paddle_service.tier_config[SubscriptionTier.FREE]["limits"]
            },
            "pro": {
                "name": "Pro",
                "price": 29,
                "currency": "USD", 
                "interval": "month",
                "features": [
                    "10,000 API calls per month",
                    "100 data exports per month",
                    "2,000 sentiment analyses per month",
                    "1-year data retention",
                    "Priority email support",
                    "Advanced analytics"
                ],
                "limits": paddle_service.tier_config[SubscriptionTier.PRO]["limits"]
            },
            "enterprise": {
                "name": "Enterprise",
                "price": 299,
                "currency": "USD",
                "interval": "month", 
                "features": [
                    "100,000 API calls per month",
                    "1,000 data exports per month",
                    "20,000 sentiment analyses per month",
                    "Unlimited data retention",
                    "Phone & chat support",
                    "Custom integrations",
                    "Dedicated account manager"
                ],
                "limits": paddle_service.tier_config[SubscriptionTier.PREMIUM]["limits"]
            }
        }
    }

@router.get("/health")
async def billing_health_check():
    """Health check for billing service"""
    return {
        "status": "healthy",
        "paddle_configured": paddle_service.is_configured(),
        "timestamp": datetime.utcnow().isoformat()
    }
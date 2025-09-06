"""
Paddle Webhook Handler for Trendit

Processes Paddle Billing API webhooks to maintain subscription state synchronization.
Handles all subscription lifecycle events including:
- Subscription creation, updates, cancellation
- Payment success and failure events  
- Customer updates
- Transaction completion events

All events are verified using Paddle's 2025 enhanced security signatures
and logged for audit purposes.
"""

from fastapi import APIRouter, Request, HTTPException, Depends, status
from sqlalchemy.orm import Session
from typing import Dict, Any
import json
import logging
from datetime import datetime

from models.database import get_db
from models.models import (
    PaddleSubscription, BillingEvent, User, SubscriptionStatus, SubscriptionTier
)
from services.paddle_service import paddle_service

router = APIRouter(prefix="/api/webhooks", tags=["webhooks"])
logger = logging.getLogger(__name__)

# ============================================================================
# WEBHOOK PROCESSING
# ============================================================================

@router.post("/paddle")
async def handle_paddle_webhook(
    request: Request,
    db: Session = Depends(get_db)
):
    """Main Paddle webhook endpoint
    
    Receives and processes all Paddle Billing API webhooks with:
    - Signature verification using 2025 enhanced security
    - Event routing to specific handlers
    - Comprehensive error handling and logging
    - Audit trail creation
    """
    try:
        # Get raw payload and headers
        payload = await request.body()
        signature = request.headers.get("paddle-signature")
        timestamp = request.headers.get("paddle-timestamp")
        
        if not signature or not timestamp:
            logger.error("Missing Paddle webhook signature or timestamp headers")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing required webhook headers"
            )
        
        # Verify webhook authenticity
        if not paddle_service.verify_webhook(payload, signature, timestamp):
            logger.error("Invalid Paddle webhook signature")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid webhook signature"
            )
        
        # Parse event data
        try:
            event_data = json.loads(payload.decode())
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in Paddle webhook: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid JSON payload"
            )
        
        event_type = event_data.get("event_type")
        event_id = event_data.get("event_id")
        
        if not event_type or not event_id:
            logger.error("Missing event_type or event_id in Paddle webhook")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid webhook payload structure"
            )
        
        logger.info(f"Processing Paddle webhook: {event_type} (ID: {event_id})")
        
        # Check for duplicate events
        existing_event = db.query(BillingEvent).filter(
            BillingEvent.paddle_event_id == event_id
        ).first()
        
        if existing_event:
            logger.info(f"Duplicate Paddle webhook event {event_id}, ignoring")
            return {"status": "success", "message": "Duplicate event ignored"}
        
        # Route to specific event handlers
        handlers = {
            "subscription.created": handle_subscription_created,
            "subscription.updated": handle_subscription_updated,
            "subscription.canceled": handle_subscription_canceled,
            "subscription.resumed": handle_subscription_resumed,
            "subscription.paused": handle_subscription_paused,
            "transaction.completed": handle_transaction_completed,
            "transaction.payment_failed": handle_payment_failed,
            "customer.updated": handle_customer_updated,
            "subscription.trial_ended": handle_trial_ended,
        }
        
        # Process the event
        processing_status = "processed"
        processing_error = None
        
        try:
            if event_type in handlers:
                await handlers[event_type](event_data, db)
                logger.info(f"Successfully processed {event_type} event {event_id}")
            else:
                logger.warning(f"Unhandled Paddle webhook event type: {event_type}")
                processing_status = "ignored"
        
        except Exception as handler_error:
            logger.error(f"Error processing {event_type} event {event_id}: {handler_error}")
            processing_status = "failed"
            processing_error = str(handler_error)
            # Don't raise here - we want to store the event for debugging
        
        # Store event for audit purposes
        await store_billing_event(event_data, processing_status, processing_error, db)
        
        return {
            "status": "success",
            "event_type": event_type,
            "event_id": event_id,
            "processing_status": processing_status
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Critical error in Paddle webhook processing: {e}")
        
        # Try to store failed event if possible
        try:
            event_data = {"error": str(e), "timestamp": datetime.utcnow().isoformat()}
            await store_billing_event(event_data, "critical_failure", str(e), db)
        except:
            pass  # If we can't even store the error, just log it
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Critical webhook processing error"
        )

# ============================================================================
# SUBSCRIPTION EVENT HANDLERS
# ============================================================================

async def handle_subscription_created(event_data: Dict[str, Any], db: Session):
    """Handle subscription.created webhook event"""
    
    subscription_data = event_data["data"]
    customer_id = subscription_data["customer_id"]
    paddle_subscription_id = subscription_data["id"]
    
    logger.info(f"Processing subscription creation for customer {customer_id}")
    
    # Find existing paddle subscription by customer ID
    paddle_subscription = db.query(PaddleSubscription).filter(
        PaddleSubscription.paddle_customer_id == customer_id
    ).first()
    
    if not paddle_subscription:
        logger.error(f"No paddle subscription found for customer {customer_id}")
        return
    
    # Update subscription with Paddle data
    paddle_subscription.paddle_subscription_id = paddle_subscription_id
    paddle_subscription.status = SubscriptionStatus.ACTIVE
    
    # Extract billing period information
    current_period = subscription_data.get("current_billing_period", {})
    if current_period:
        paddle_subscription.current_period_start = datetime.fromisoformat(
            current_period["starts_at"].replace("Z", "+00:00")
        )
        paddle_subscription.current_period_end = datetime.fromisoformat(
            current_period["ends_at"].replace("Z", "+00:00")
        )
    
    # Set next billing date
    if subscription_data.get("next_billed_at"):
        paddle_subscription.next_billed_at = datetime.fromisoformat(
            subscription_data["next_billed_at"].replace("Z", "+00:00")
        )
    
    # Determine tier and set limits based on price
    for item in subscription_data.get("items", []):
        price_id = item["price"]["id"]
        tier = paddle_service.get_tier_from_price_id(price_id)
        
        if tier:
            paddle_subscription.tier = tier
            paddle_subscription.paddle_price_id = price_id
            
            # Set limits based on tier
            tier_limits = paddle_service.get_tier_limits(tier)
            paddle_subscription.monthly_api_calls_limit = tier_limits["api_calls_per_month"]
            paddle_subscription.monthly_exports_limit = tier_limits["exports_per_month"]
            paddle_subscription.monthly_sentiment_limit = tier_limits["sentiment_analysis_per_month"]
            paddle_subscription.data_retention_days = tier_limits["data_retention_days"]
            
            # Set pricing
            paddle_subscription.price_per_month = paddle_service.tier_config[tier]["price"]
            break
    
    # Handle trial period
    trial_end_at = subscription_data.get("trial_end_at")
    if trial_end_at:
        paddle_subscription.is_trial = True
        paddle_subscription.trial_end_date = datetime.fromisoformat(
            trial_end_at.replace("Z", "+00:00")
        )
    
    # Set currency
    if subscription_data.get("currency_code"):
        paddle_subscription.currency = subscription_data["currency_code"]
    
    db.commit()
    
    logger.info(f"Subscription created successfully for user {paddle_subscription.user_id}")

async def handle_subscription_updated(event_data: Dict[str, Any], db: Session):
    """Handle subscription.updated webhook event"""
    
    subscription_data = event_data["data"]
    paddle_subscription_id = subscription_data["id"]
    
    logger.info(f"Processing subscription update for {paddle_subscription_id}")
    
    # Find subscription by Paddle ID
    paddle_subscription = db.query(PaddleSubscription).filter(
        PaddleSubscription.paddle_subscription_id == paddle_subscription_id
    ).first()
    
    if not paddle_subscription:
        logger.error(f"No subscription found for Paddle ID {paddle_subscription_id}")
        return
    
    # Update status
    paddle_status = subscription_data.get("status")
    if paddle_status == "active":
        paddle_subscription.status = SubscriptionStatus.ACTIVE
    elif paddle_status == "canceled":
        paddle_subscription.status = SubscriptionStatus.CANCELLED
    elif paddle_status == "paused":
        paddle_subscription.status = SubscriptionStatus.SUSPENDED
    
    # Update billing period
    current_period = subscription_data.get("current_billing_period", {})
    if current_period:
        paddle_subscription.current_period_start = datetime.fromisoformat(
            current_period["starts_at"].replace("Z", "+00:00")
        )
        paddle_subscription.current_period_end = datetime.fromisoformat(
            current_period["ends_at"].replace("Z", "+00:00")
        )
    
    # Update next billing date
    if subscription_data.get("next_billed_at"):
        paddle_subscription.next_billed_at = datetime.fromisoformat(
            subscription_data["next_billed_at"].replace("Z", "+00:00")
        )
    
    # Check for tier changes (upgrades/downgrades)
    for item in subscription_data.get("items", []):
        price_id = item["price"]["id"]
        tier = paddle_service.get_tier_from_price_id(price_id)
        
        if tier and tier != paddle_subscription.tier:
            logger.info(f"Tier change detected: {paddle_subscription.tier.value} -> {tier.value}")
            paddle_subscription.tier = tier
            paddle_subscription.paddle_price_id = price_id
            
            # Update limits
            tier_limits = paddle_service.get_tier_limits(tier)
            paddle_subscription.monthly_api_calls_limit = tier_limits["api_calls_per_month"]
            paddle_subscription.monthly_exports_limit = tier_limits["exports_per_month"]
            paddle_subscription.monthly_sentiment_limit = tier_limits["sentiment_analysis_per_month"]
            paddle_subscription.data_retention_days = tier_limits["data_retention_days"]
            
            # Update pricing
            paddle_subscription.price_per_month = paddle_service.tier_config[tier]["price"]
    
    db.commit()
    
    logger.info(f"Subscription updated successfully for user {paddle_subscription.user_id}")

async def handle_subscription_canceled(event_data: Dict[str, Any], db: Session):
    """Handle subscription.canceled webhook event"""
    
    subscription_data = event_data["data"]
    paddle_subscription_id = subscription_data["id"]
    
    logger.info(f"Processing subscription cancellation for {paddle_subscription_id}")
    
    # Find subscription
    paddle_subscription = db.query(PaddleSubscription).filter(
        PaddleSubscription.paddle_subscription_id == paddle_subscription_id
    ).first()
    
    if not paddle_subscription:
        logger.error(f"No subscription found for Paddle ID {paddle_subscription_id}")
        return
    
    # Update to cancelled status and downgrade to free tier
    paddle_subscription.status = SubscriptionStatus.CANCELLED
    paddle_subscription.tier = SubscriptionTier.FREE
    
    # Set free tier limits
    free_limits = paddle_service.get_tier_limits(SubscriptionTier.FREE)
    paddle_subscription.monthly_api_calls_limit = free_limits["api_calls_per_month"]
    paddle_subscription.monthly_exports_limit = free_limits["exports_per_month"]
    paddle_subscription.monthly_sentiment_limit = free_limits["sentiment_analysis_per_month"]
    paddle_subscription.data_retention_days = free_limits["data_retention_days"]
    paddle_subscription.price_per_month = 0.0
    
    # Clear trial status
    paddle_subscription.is_trial = False
    paddle_subscription.trial_end_date = None
    
    db.commit()
    
    logger.info(f"Subscription cancelled and downgraded to free for user {paddle_subscription.user_id}")

async def handle_subscription_resumed(event_data: Dict[str, Any], db: Session):
    """Handle subscription.resumed webhook event"""
    
    subscription_data = event_data["data"]
    paddle_subscription_id = subscription_data["id"]
    
    logger.info(f"Processing subscription resume for {paddle_subscription_id}")
    
    # Find subscription
    paddle_subscription = db.query(PaddleSubscription).filter(
        PaddleSubscription.paddle_subscription_id == paddle_subscription_id
    ).first()
    
    if paddle_subscription:
        paddle_subscription.status = SubscriptionStatus.ACTIVE
        db.commit()
        logger.info(f"Subscription resumed for user {paddle_subscription.user_id}")

async def handle_subscription_paused(event_data: Dict[str, Any], db: Session):
    """Handle subscription.paused webhook event"""
    
    subscription_data = event_data["data"]
    paddle_subscription_id = subscription_data["id"]
    
    logger.info(f"Processing subscription pause for {paddle_subscription_id}")
    
    # Find subscription
    paddle_subscription = db.query(PaddleSubscription).filter(
        PaddleSubscription.paddle_subscription_id == paddle_subscription_id
    ).first()
    
    if paddle_subscription:
        paddle_subscription.status = SubscriptionStatus.SUSPENDED
        db.commit()
        logger.info(f"Subscription paused for user {paddle_subscription.user_id}")

# ============================================================================
# PAYMENT & TRANSACTION EVENT HANDLERS
# ============================================================================

async def handle_transaction_completed(event_data: Dict[str, Any], db: Session):
    """Handle transaction.completed webhook event"""
    
    transaction_data = event_data["data"]
    customer_id = transaction_data.get("customer_id")
    
    logger.info(f"Processing completed transaction for customer {customer_id}")
    
    # Find subscription by customer ID
    paddle_subscription = db.query(PaddleSubscription).filter(
        PaddleSubscription.paddle_customer_id == customer_id
    ).first()
    
    if paddle_subscription:
        # Ensure subscription is active after successful payment
        if paddle_subscription.status == SubscriptionStatus.SUSPENDED:
            paddle_subscription.status = SubscriptionStatus.ACTIVE
            db.commit()
            logger.info(f"Subscription reactivated after payment for user {paddle_subscription.user_id}")

async def handle_payment_failed(event_data: Dict[str, Any], db: Session):
    """Handle transaction.payment_failed webhook event"""
    
    transaction_data = event_data["data"]
    subscription_id = transaction_data.get("subscription_id")
    
    logger.warning(f"Processing payment failure for subscription {subscription_id}")
    
    if subscription_id:
        # Find subscription
        paddle_subscription = db.query(PaddleSubscription).filter(
            PaddleSubscription.paddle_subscription_id == subscription_id
        ).first()
        
        if paddle_subscription:
            # Suspend subscription due to payment failure
            paddle_subscription.status = SubscriptionStatus.SUSPENDED
            db.commit()
            logger.warning(f"Subscription suspended due to payment failure for user {paddle_subscription.user_id}")

async def handle_trial_ended(event_data: Dict[str, Any], db: Session):
    """Handle subscription.trial_ended webhook event"""
    
    subscription_data = event_data["data"]
    paddle_subscription_id = subscription_data["id"]
    
    logger.info(f"Processing trial end for subscription {paddle_subscription_id}")
    
    # Find subscription
    paddle_subscription = db.query(PaddleSubscription).filter(
        PaddleSubscription.paddle_subscription_id == paddle_subscription_id
    ).first()
    
    if paddle_subscription:
        # Clear trial status
        paddle_subscription.is_trial = False
        paddle_subscription.trial_end_date = None
        db.commit()
        logger.info(f"Trial ended for user {paddle_subscription.user_id}")

# ============================================================================
# CUSTOMER EVENT HANDLERS
# ============================================================================

async def handle_customer_updated(event_data: Dict[str, Any], db: Session):
    """Handle customer.updated webhook event"""
    
    customer_data = event_data["data"]
    customer_id = customer_data["id"]
    
    logger.info(f"Processing customer update for {customer_id}")
    
    # Find subscription by customer ID
    paddle_subscription = db.query(PaddleSubscription).filter(
        PaddleSubscription.paddle_customer_id == customer_id
    ).first()
    
    if paddle_subscription:
        # Update customer portal URL if provided
        management_urls = customer_data.get("management_urls", {})
        if management_urls.get("customer_portal"):
            paddle_subscription.customer_portal_url = management_urls["customer_portal"]
            db.commit()
            logger.info(f"Customer portal URL updated for user {paddle_subscription.user_id}")

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

async def store_billing_event(
    event_data: Dict[str, Any], 
    processing_status: str,
    processing_error: str = None,
    db: Session = None
):
    """Store billing event for audit purposes"""
    
    try:
        # Extract event metadata
        event_id = event_data.get("event_id", "unknown")
        event_type = event_data.get("event_type", "unknown")
        occurred_at = event_data.get("occurred_at")
        
        # Find related subscription and user
        user_id = None
        subscription_id = None
        paddle_customer_id = None
        paddle_subscription_id = None
        paddle_transaction_id = None
        
        # Extract IDs from event data
        data_section = event_data.get("data", {})
        if data_section:
            paddle_customer_id = data_section.get("customer_id")
            paddle_subscription_id = data_section.get("id") or data_section.get("subscription_id")
            paddle_transaction_id = data_section.get("transaction_id")
        
        # Find associated subscription
        if paddle_customer_id or paddle_subscription_id:
            query = db.query(PaddleSubscription)
            if paddle_customer_id:
                paddle_subscription = query.filter(
                    PaddleSubscription.paddle_customer_id == paddle_customer_id
                ).first()
            elif paddle_subscription_id:
                paddle_subscription = query.filter(
                    PaddleSubscription.paddle_subscription_id == paddle_subscription_id
                ).first()
            
            if paddle_subscription:
                user_id = paddle_subscription.user_id
                subscription_id = paddle_subscription.id
        
        # Create billing event record
        billing_event = BillingEvent(
            user_id=user_id,
            subscription_id=subscription_id,
            paddle_event_id=event_id,
            event_type=event_type,
            paddle_subscription_id=paddle_subscription_id,
            paddle_transaction_id=paddle_transaction_id,
            paddle_customer_id=paddle_customer_id,
            status=processing_status,
            raw_event_data=json.dumps(event_data),
            paddle_event_time=datetime.fromisoformat(occurred_at.replace("Z", "+00:00")) if occurred_at else datetime.utcnow(),
            processing_status=processing_status,
            processing_error=processing_error
        )
        
        db.add(billing_event)
        db.commit()
        
        logger.debug(f"Stored billing event {event_id} with status {processing_status}")
        
    except Exception as e:
        logger.error(f"Failed to store billing event: {e}")
        # Don't raise here - event storage failure shouldn't break webhook processing

# ============================================================================
# WEBHOOK STATUS AND DEBUGGING
# ============================================================================

@router.get("/paddle/status")
async def webhook_status():
    """Get webhook service status"""
    return {
        "status": "operational",
        "webhook_endpoint": "/api/webhooks/paddle",
        "paddle_configured": paddle_service.is_configured(),
        "supported_events": [
            "subscription.created",
            "subscription.updated", 
            "subscription.canceled",
            "subscription.resumed",
            "subscription.paused",
            "transaction.completed",
            "transaction.payment_failed",
            "customer.updated",
            "subscription.trial_ended"
        ],
        "timestamp": datetime.utcnow().isoformat()
    }
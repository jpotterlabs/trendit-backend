"""
Paddle Billing API Integration Service for Trendit

This service handles all interactions with Paddle's Billing API including:
- Customer management
- Subscription lifecycle management  
- Checkout session creation
- Webhook verification
- Usage tracking integration

Supports Paddle's 2025 enhanced API with modern security features.
"""

import httpx
import hmac
import hashlib
import json
import os
import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session

from models.models import (
    User, PaddleSubscription, SubscriptionTier, SubscriptionStatus,
    UsageRecord, BillingEvent
)

logger = logging.getLogger(__name__)

class PaddleService:
    """Paddle Billing API integration for Trendit SaaS platform"""
    
    def __init__(self, sandbox: bool = True):
        """Initialize Paddle service with API credentials
        
        Args:
            sandbox: If True, use Paddle sandbox environment
        """
        self.api_key = os.getenv("PADDLE_API_KEY")
        self.webhook_secret = os.getenv("PADDLE_WEBHOOK_SECRET")
        
        if not self.api_key:
            logger.warning("PADDLE_API_KEY not found in environment variables")
        
        self.base_url = (
            "https://sandbox-api.paddle.com" if sandbox 
            else "https://api.paddle.com"
        )
        
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        # Trendit subscription tier configuration - Feature-based access model
        self.tier_config = {
            SubscriptionTier.FREE: {
                "price": 0,
                "paddle_price_id": None,
                "name": "Discover",
                "description": "Explore Reddit trends with pre-built scenarios",
                "features": {
                    "scenarios_api": True,
                    "query_api": False,
                    "collect_api": False,
                    "data_api": False,
                    "export_api": False,
                    "analytics_dashboard": False,
                    "sentiment_analysis": False
                },
                "limits": {
                    "scenario_queries_per_month": 100,
                    "data_retention_days": 30
                }
            },
            SubscriptionTier.PRO: {
                "price": 29,
                "paddle_price_id": os.getenv("PADDLE_PRO_PRICE_ID"),
                "name": "Research",
                "description": "Ad-hoc research with live Reddit searches",
                "features": {
                    "scenarios_api": True,
                    "query_api": True,
                    "collect_api": False,
                    "data_api": False,
                    "export_api": False,
                    "analytics_dashboard": True,  # Basic analytics only
                    "sentiment_analysis": False
                },
                "limits": {
                    "scenario_queries_per_month": -1,  # Unlimited
                    "query_requests_per_month": 1000,
                    "data_retention_days": 90
                }
            },
            SubscriptionTier.PREMIUM: {
                "price": 79,
                "paddle_price_id": os.getenv("PADDLE_PREMIUM_PRICE_ID"),
                "name": "Intelligence",
                "description": "Persistent data collection with powerful analytics",
                "features": {
                    "scenarios_api": True,
                    "query_api": True,
                    "collect_api": True,
                    "data_api": True,
                    "export_api": True,
                    "analytics_dashboard": True,  # Advanced analytics
                    "sentiment_analysis": False  # Removed entirely
                },
                "limits": {
                    "scenario_queries_per_month": -1,  # Unlimited
                    "query_requests_per_month": -1,    # Unlimited
                    "collection_jobs_per_month": 100,
                    "data_exports_per_month": 50,
                    "data_retention_days": 365
                }
            }
        }
    
    # ========================================================================
    # CUSTOMER MANAGEMENT
    # ========================================================================
    
    async def create_customer(self, user: User) -> Dict:
        """Create Paddle customer for Trendit user
        
        Args:
            user: Trendit user to create Paddle customer for
            
        Returns:
            Paddle customer data
            
        Raises:
            httpx.HTTPStatusError: If Paddle API request fails
        """
        try:
            payload = {
                "email": user.email,
                "name": user.username if user.username else user.email.split("@")[0],
                "locale": "en",
                "custom_data": {
                    "trendit_user_id": str(user.id),
                    "signup_date": datetime.utcnow().isoformat(),
                    "platform": "trendit",
                    "user_email": user.email
                }
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/customers",
                    json=payload,
                    headers=self.headers
                )
                response.raise_for_status()
                
                customer_data = response.json()
                logger.info(f"Created Paddle customer for user {user.id}: {customer_data['data']['id']}")
                return customer_data
                
        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to create Paddle customer for user {user.id}: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error creating Paddle customer: {e}")
            raise
    
    async def get_customer(self, customer_id: str) -> Dict:
        """Retrieve Paddle customer information
        
        Args:
            customer_id: Paddle customer ID
            
        Returns:
            Paddle customer data
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/customers/{customer_id}",
                    headers=self.headers
                )
                response.raise_for_status()
                return response.json()
                
        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to get Paddle customer {customer_id}: {e}")
            raise
    
    # ========================================================================
    # SUBSCRIPTION MANAGEMENT
    # ========================================================================
    
    async def create_subscription(
        self, 
        customer_id: str, 
        tier: SubscriptionTier,
        trial_days: Optional[int] = None
    ) -> Dict:
        """Create Paddle subscription for specific tier
        
        Args:
            customer_id: Paddle customer ID
            tier: Subscription tier (PRO or PREMIUM)
            trial_days: Optional trial period in days
            
        Returns:
            Paddle subscription data
        """
        if tier == SubscriptionTier.FREE:
            raise ValueError("Cannot create Paddle subscription for FREE tier")
        
        price_id = self.tier_config[tier]["paddle_price_id"]
        if not price_id:
            raise ValueError(f"Paddle price ID not configured for {tier.value} tier")
        
        try:
            payload = {
                "customer_id": customer_id,
                "items": [{
                    "price_id": price_id,
                    "quantity": 1
                }],
                "collection_mode": "automatic",
                "billing_cycle": {
                    "interval": "month",
                    "frequency": 1
                },
                "custom_data": {
                    "trendit_tier": tier.value,
                    "created_via": "trendit_api",
                    "plan_name": f"Trendit {tier.value.title()}"
                }
            }
            
            # Add trial period if specified
            if trial_days and trial_days > 0:
                trial_end = datetime.utcnow() + timedelta(days=trial_days)
                payload["scheduled_change"] = {
                    "action": "resume",
                    "effective_at": trial_end.isoformat(),
                    "resume_immediately": False
                }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/subscriptions",
                    json=payload,
                    headers=self.headers
                )
                response.raise_for_status()
                
                subscription_data = response.json()
                logger.info(f"Created Paddle subscription for customer {customer_id}: {subscription_data['data']['id']}")
                return subscription_data
                
        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to create Paddle subscription: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error creating subscription: {e}")
            raise
    
    async def update_subscription(
        self, 
        subscription_id: str, 
        new_tier: SubscriptionTier
    ) -> Dict:
        """Upgrade or downgrade subscription to new tier
        
        Args:
            subscription_id: Paddle subscription ID
            new_tier: Target subscription tier
            
        Returns:
            Updated subscription data
        """
        if new_tier == SubscriptionTier.FREE:
            return await self.cancel_subscription(subscription_id)
        
        new_price_id = self.tier_config[new_tier]["paddle_price_id"]
        if not new_price_id:
            raise ValueError(f"Paddle price ID not configured for {new_tier.value} tier")
        
        try:
            payload = {
                "items": [{
                    "price_id": new_price_id,
                    "quantity": 1
                }],
                "proration_billing_mode": "prorated_immediately",
                "custom_data": {
                    "trendit_tier": new_tier.value,
                    "updated_via": "trendit_api",
                    "plan_name": f"Trendit {new_tier.value.title()}"
                }
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.patch(
                    f"{self.base_url}/subscriptions/{subscription_id}",
                    json=payload,
                    headers=self.headers
                )
                response.raise_for_status()
                
                subscription_data = response.json()
                logger.info(f"Updated Paddle subscription {subscription_id} to {new_tier.value}")
                return subscription_data
                
        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to update Paddle subscription {subscription_id}: {e}")
            raise
    
    async def cancel_subscription(self, subscription_id: str) -> Dict:
        """Cancel subscription at end of current billing period
        
        Args:
            subscription_id: Paddle subscription ID
            
        Returns:
            Subscription cancellation data
        """
        try:
            payload = {
                "scheduled_change": {
                    "action": "cancel",
                    "effective_at": "next_billing_period"
                }
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.patch(
                    f"{self.base_url}/subscriptions/{subscription_id}",
                    json=payload,
                    headers=self.headers
                )
                response.raise_for_status()
                
                subscription_data = response.json()
                logger.info(f"Cancelled Paddle subscription {subscription_id}")
                return subscription_data
                
        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to cancel Paddle subscription {subscription_id}: {e}")
            raise
    
    async def get_subscription(self, subscription_id: str) -> Dict:
        """Get subscription details from Paddle
        
        Args:
            subscription_id: Paddle subscription ID
            
        Returns:
            Subscription data
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/subscriptions/{subscription_id}",
                    headers=self.headers
                )
                response.raise_for_status()
                return response.json()
                
        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to get Paddle subscription {subscription_id}: {e}")
            raise
    
    # ========================================================================
    # CHECKOUT & PAYMENTS
    # ========================================================================
    
    async def create_checkout_url(
        self, 
        user: User, 
        tier: SubscriptionTier,
        success_url: str,
        cancel_url: str,
        trial_days: Optional[int] = None
    ) -> str:
        """Create Paddle checkout URL for subscription
        
        Args:
            user: User purchasing subscription
            tier: Subscription tier to purchase
            success_url: URL to redirect after successful payment
            cancel_url: URL to redirect if payment is cancelled
            trial_days: Optional trial period
            
        Returns:
            Paddle checkout URL
        """
        if tier == SubscriptionTier.FREE:
            raise ValueError("Cannot create checkout for FREE tier")
        
        price_id = self.tier_config[tier]["paddle_price_id"]
        if not price_id:
            raise ValueError(f"Paddle price ID not configured for {tier.value} tier")
        
        try:
            payload = {
                "items": [{
                    "price_id": price_id,
                    "quantity": 1
                }],
                "customer_email": user.email,
                "customer_ip_address": None,  # Will be set by frontend
                "currency_code": "USD",
                "custom_data": {
                    "trendit_user_id": str(user.id),
                    "tier": tier.value,
                    "trial_days": trial_days or 0
                },
                "return_url": success_url,
                "discount_id": None,  # Could add promo codes here
                "locale": "en"
            }
            
            # Add trial if specified
            if trial_days and trial_days > 0:
                payload["checkout_settings"] = {
                    "allow_logout": False,
                    "theme": "light",
                    "locale": "en",
                    "display_mode": "overlay"
                }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/transactions",
                    json=payload,
                    headers=self.headers
                )
                response.raise_for_status()
                
                transaction_data = response.json()
                checkout_url = transaction_data["data"]["checkout"]["url"]
                
                logger.info(f"Created checkout URL for user {user.id}, tier {tier.value}")
                return checkout_url
                
        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to create checkout URL: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error creating checkout: {e}")
            raise
    
    # ========================================================================
    # WEBHOOK VERIFICATION
    # ========================================================================
    
    def verify_webhook(self, payload: bytes, signature: str, timestamp: str) -> bool:
        """Verify Paddle webhook signature using 2025 enhanced security
        
        Args:
            payload: Raw webhook payload
            signature: Paddle-Signature header value
            timestamp: Paddle-Timestamp header value
            
        Returns:
            True if signature is valid, False otherwise
        """
        if not self.webhook_secret:
            logger.error("Paddle webhook secret not configured")
            return False
        
        try:
            # Extract signature from header (format: "ts=timestamp,h1=signature")
            signature_parts = {}
            for part in signature.split(","):
                if "=" in part:
                    key, value = part.split("=", 1)
                    signature_parts[key] = value
            
            webhook_signature = signature_parts.get("h1")
            if not webhook_signature:
                logger.error("No h1 signature found in Paddle-Signature header")
                return False
            
            # Construct signed payload for verification
            signed_payload = f"{timestamp}.{payload.decode()}"
            
            # Calculate expected signature
            expected_signature = hmac.new(
                self.webhook_secret.encode(),
                signed_payload.encode(),
                hashlib.sha256
            ).hexdigest()
            
            # Verify signature
            is_valid = hmac.compare_digest(webhook_signature, expected_signature)
            
            if not is_valid:
                logger.warning("Invalid Paddle webhook signature")
            
            return is_valid
            
        except Exception as e:
            logger.error(f"Error verifying Paddle webhook signature: {e}")
            return False
    
    # ========================================================================
    # USAGE TRACKING INTEGRATION
    # ========================================================================
    
    def get_tier_limits(self, tier: SubscriptionTier) -> Dict[str, int]:
        """Get usage limits for subscription tier

        Args:
            tier: Subscription tier

        Returns:
            Dictionary of usage limits
        """
        return self.tier_config[tier]["limits"]

    def get_tier_features(self, tier: SubscriptionTier) -> Dict[str, bool]:
        """Get feature access for subscription tier

        Args:
            tier: Subscription tier

        Returns:
            Dictionary of feature access permissions
        """
        return self.tier_config[tier]["features"]

    def has_feature_access(self, tier: SubscriptionTier, feature: str) -> bool:
        """Check if tier has access to specific feature

        Args:
            tier: Subscription tier
            feature: Feature name (e.g., 'query_api', 'collect_api')

        Returns:
            True if tier has access to feature
        """
        features = self.get_tier_features(tier)
        return features.get(feature, False)

    def get_tier_info(self, tier: SubscriptionTier) -> Dict:
        """Get complete tier information including name, description, features, and limits

        Args:
            tier: Subscription tier

        Returns:
            Complete tier configuration dictionary
        """
        return self.tier_config[tier]
    
    def calculate_billing_period(self, subscription: PaddleSubscription) -> Tuple[datetime, datetime]:
        """Calculate current billing period for subscription
        
        Args:
            subscription: PaddleSubscription record
            
        Returns:
            Tuple of (period_start, period_end)
        """
        if subscription.current_period_start and subscription.current_period_end:
            return subscription.current_period_start, subscription.current_period_end
        else:
            # Fallback to calendar month for free users
            now = datetime.now(timezone.utc)
            month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            
            # Get next month
            if now.month == 12:
                next_month = month_start.replace(year=now.year + 1, month=1)
            else:
                next_month = month_start.replace(month=now.month + 1)
            
            return month_start, next_month
    
    # ========================================================================
    # UTILITY METHODS
    # ========================================================================
    
    def get_tier_from_price_id(self, price_id: str) -> Optional[SubscriptionTier]:
        """Get subscription tier from Paddle price ID
        
        Args:
            price_id: Paddle price ID
            
        Returns:
            Matching SubscriptionTier or None
        """
        for tier, config in self.tier_config.items():
            if config["paddle_price_id"] == price_id:
                return tier
        return None
    
    def is_configured(self) -> bool:
        """Check if Paddle service is properly configured
        
        Returns:
            True if API key and price IDs are configured
        """
        if not self.api_key:
            return False
        
        # Check that price IDs are configured for paid tiers
        pro_price_id = self.tier_config[SubscriptionTier.PRO]["paddle_price_id"]
        premium_price_id = self.tier_config[SubscriptionTier.PREMIUM]["paddle_price_id"]
        
        return bool(pro_price_id and premium_price_id)


# Global instance for dependency injection
paddle_service = PaddleService(sandbox=True)  # Change to False in production
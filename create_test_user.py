#!/usr/bin/env python3
"""Create a test user with Enterprise subscription for development testing"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy.orm import Session
from models.database import get_db
from models.models import User, PaddleSubscription, SubscriptionStatus, SubscriptionTier
from passlib.context import CryptContext
from datetime import datetime, timezone, timedelta
import uuid

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def create_test_user():
    db = next(get_db())
    
    # Test user credentials
    email = "test@trendit.dev"
    password = "testpass123"
    username = "testuser_enterprise"
    
    try:
        # Check if user already exists by email or username
        existing = db.query(User).filter(
            (User.email == email) | (User.username == username)
        ).first()
        
        if existing:
            print(f"Test user {email} already exists!")
            
            # Update subscription status
            existing.subscription_status = SubscriptionStatus.ACTIVE
            
            # Check if they have enterprise subscription
            enterprise_sub = db.query(PaddleSubscription).filter(
                PaddleSubscription.user_id == existing.id,
                PaddleSubscription.tier == SubscriptionTier.ENTERPRISE,
                PaddleSubscription.status == SubscriptionStatus.ACTIVE
            ).first()
            
            if not enterprise_sub:
                # Deactivate any existing subscriptions
                db.query(PaddleSubscription).filter(
                    PaddleSubscription.user_id == existing.id
                ).update({"status": SubscriptionStatus.CANCELLED})
                
                # Add enterprise subscription
                subscription = PaddleSubscription(
                    user_id=existing.id,
                    paddle_subscription_id=f"test_sub_{uuid.uuid4().hex[:8]}",
                    tier=SubscriptionTier.ENTERPRISE,
                    status=SubscriptionStatus.ACTIVE,
                    current_period_start=datetime.now(timezone.utc),
                    current_period_end=datetime.now(timezone.utc) + timedelta(days=365)
                )
                db.add(subscription)
                db.commit()
                print("✅ Added Enterprise subscription to existing test user")
            else:
                print("✅ Test user already has Enterprise subscription")
                
            db.commit()
            print(f"Login: {email} / {password}")
            return
        
        # Create new user
        hashed_password = pwd_context.hash(password)
        user = User(
            email=email,
            username=username,
            password_hash=hashed_password,
            is_active=True,
            subscription_status=SubscriptionStatus.ACTIVE
        )
        
        db.add(user)
        db.commit()
        db.refresh(user)
        
        # Add Enterprise subscription
        subscription = PaddleSubscription(
            user_id=user.id,
            paddle_subscription_id=f"test_sub_{uuid.uuid4().hex[:8]}",
            tier=SubscriptionTier.ENTERPRISE,
            status=SubscriptionStatus.ACTIVE,
            current_period_start=datetime.now(timezone.utc),
            current_period_end=datetime.now(timezone.utc) + timedelta(days=365)
        )
        
        db.add(subscription)
        db.commit()
        
        print("✅ Created test user with Enterprise subscription (unlimited usage)")
        print(f"Email: {email}")
        print(f"Password: {password}")
        print(f"Tier: {SubscriptionTier.ENTERPRISE.value}")
        print(f"Status: {SubscriptionStatus.ACTIVE.value}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    create_test_user()
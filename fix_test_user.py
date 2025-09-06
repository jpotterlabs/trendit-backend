#!/usr/bin/env python3
"""Fix test user password and verify login credentials"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy.orm import Session
from models.database import get_db
from models.models import User, PaddleSubscription, SubscriptionStatus, SubscriptionTier
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def fix_test_user():
    db = next(get_db())
    
    email = "test@trendit.dev"
    new_password = "testpass123"
    
    try:
        # Find the test user
        user = db.query(User).filter(User.email == email).first()
        if not user:
            print(f"❌ User {email} not found!")
            return
            
        print(f"Found user: {user.email} (ID: {user.id})")
        print(f"Username: {user.username}")
        print(f"Active: {user.is_active}")
        print(f"Subscription Status: {user.subscription_status}")
        
        # Update password
        new_hash = pwd_context.hash(new_password)
        user.password_hash = new_hash
        user.is_active = True
        user.subscription_status = SubscriptionStatus.ACTIVE
        
        # Check subscription
        subscription = db.query(PaddleSubscription).filter(
            PaddleSubscription.user_id == user.id
        ).first()
        
        if subscription:
            print(f"Subscription Tier: {subscription.tier}")
            print(f"Subscription Status: {subscription.status}")
        else:
            print("❌ No subscription found!")
            
        db.commit()
        print("✅ Updated test user password and status")
        
        # Test the password
        test_verify = pwd_context.verify(new_password, user.password_hash)
        print(f"Password verification test: {'✅ PASS' if test_verify else '❌ FAIL'}")
        
        print(f"\n🔑 Login credentials:")
        print(f"Email: {email}")
        print(f"Password: {new_password}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    fix_test_user()
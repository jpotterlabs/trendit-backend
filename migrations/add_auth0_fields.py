#!/usr/bin/env python3
"""
Database migration: Add Auth0 integration fields to User table

Adds:
- auth0_user_id: String, nullable, unique, indexed
- auth0_provider: String, nullable  
- Makes password_hash nullable for OAuth users
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from models.database import get_db, engine
import logging

logger = logging.getLogger(__name__)

def migrate_user_table():
    """Add Auth0 fields to users table"""
    
    migrations = [
        # Make password_hash nullable for OAuth users
        "ALTER TABLE users ALTER COLUMN password_hash DROP NOT NULL;",
        
        # Add Auth0 user ID field (unique, indexed)
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS auth0_user_id VARCHAR NULL;",
        
        # Add Auth0 provider field
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS auth0_provider VARCHAR NULL;",
        
        # Create unique index on auth0_user_id
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_users_auth0_user_id ON users(auth0_user_id);",
        
        # Create index on auth0_provider for queries
        "CREATE INDEX IF NOT EXISTS idx_users_auth0_provider ON users(auth0_provider);",
    ]
    
    try:
        with engine.connect() as connection:
            for migration in migrations:
                logger.info(f"Executing: {migration}")
                connection.execute(text(migration))
                connection.commit()
        
        print("✅ Auth0 migration completed successfully!")
        print("Added fields:")
        print("  - auth0_user_id (unique, indexed)")
        print("  - auth0_provider") 
        print("  - password_hash now nullable")
        
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        print(f"❌ Migration failed: {e}")
        return False
    
    return True

def verify_migration():
    """Verify the migration was successful"""
    try:
        with engine.connect() as connection:
            # Check if columns exist
            result = connection.execute(text("""
                SELECT column_name, is_nullable, data_type 
                FROM information_schema.columns 
                WHERE table_name = 'users' 
                AND column_name IN ('auth0_user_id', 'auth0_provider', 'password_hash')
                ORDER BY column_name;
            """))
            
            columns = result.fetchall()
            print("\n📋 User table columns:")
            for col in columns:
                nullable = "NULL" if col[1] == "YES" else "NOT NULL"
                print(f"  - {col[0]}: {col[2]} {nullable}")
            
            # Check indexes
            result = connection.execute(text("""
                SELECT indexname, indexdef 
                FROM pg_indexes 
                WHERE tablename = 'users' 
                AND indexname LIKE '%auth0%';
            """))
            
            indexes = result.fetchall()
            print("\n🔍 Auth0 indexes:")
            for idx in indexes:
                print(f"  - {idx[0]}")
                
    except Exception as e:
        print(f"❌ Verification failed: {e}")

if __name__ == "__main__":
    print("🔄 Running Auth0 migration...")
    
    if migrate_user_table():
        print("\n🔍 Verifying migration...")
        verify_migration()
    else:
        sys.exit(1)
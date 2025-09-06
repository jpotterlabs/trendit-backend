#!/usr/bin/env python3
"""
Database initialization script for Trendit
Creates all tables and optionally seeds with sample data
"""

import os
import sys
import logging
from sqlalchemy import create_engine
from dotenv import load_dotenv

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from models.database import Base, engine
from models.models import User, CollectionJob, RedditPost, RedditComment, RedditUser, Analytics

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def init_database():
    """Initialize the database with all tables"""
    try:
        logger.info("Creating database tables...")
        
        # Create all tables
        Base.metadata.create_all(bind=engine)
        
        logger.info("Database tables created successfully!")
        logger.info("Tables created:")
        for table_name in Base.metadata.tables.keys():
            logger.info(f"  - {table_name}")
            
        return True
        
    except Exception as e:
        logger.error(f"Error creating database tables: {e}")
        return False

def check_database_connection():
    """Check if database connection is working"""
    try:
        # Test database connection
        from sqlalchemy import text
        with engine.connect() as connection:
            result = connection.execute(text("SELECT 1"))
            logger.info("Database connection successful!")
            return True
            
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        logger.error("Please check your DATABASE_URL environment variable")
        return False

def main():
    """Main initialization function"""
    logger.info("Starting Trendit database initialization...")
    
    # Check database connection first
    if not check_database_connection():
        logger.error("Cannot connect to database. Exiting.")
        sys.exit(1)
    
    # Initialize database
    if init_database():
        logger.info("Database initialization completed successfully!")
        logger.info("You can now start the Trendit API server.")
    else:
        logger.error("Database initialization failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()
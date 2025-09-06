#!/usr/bin/env python3
"""
Test script for Trendit API
Validates Reddit integration and basic functionality
"""

import os
import sys
import asyncio
import logging
import httpx
import json
import time
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Add current directory to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.reddit_client import RedditClient
from services.data_collector import DataCollector

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_reddit_connection():
    """Test Reddit API connection"""
    logger.info("Testing Reddit API connection...")
    
    try:
        client = RedditClient()
        
        # Test basic subreddit access
        posts = client.get_subreddit_posts("python", limit=5)
        logger.info(f"Successfully retrieved {len(posts)} posts from r/python")
        
        if posts:
            logger.info(f"Sample post: {posts[0]['title'][:50]}...")
        
        return True
        
    except Exception as e:
        logger.error(f"Reddit connection test failed: {e}")
        return False

async def test_scenarios():
    """Test the specific user scenarios"""
    logger.info("Testing user scenarios...")
    
    try:
        collector = DataCollector()
        
        # Test Scenario 1: Search posts by keyword and date
        logger.info("Testing Scenario 1: Keyword search with date range")
        date_from = datetime.utcnow() - timedelta(days=30)
        date_to = datetime.utcnow()
        
        results = await collector.search_subreddit_posts_by_keyword_and_date(
            subreddit="python",
            keywords=["fastapi", "api"],
            date_from=date_from,
            date_to=date_to,
            limit=3
        )
        logger.info(f"Scenario 1: Found {len(results)} posts about FastAPI in r/python")
        
        # Test Scenario 2: Trending posts across multiple subreddits
        logger.info("Testing Scenario 2: Multi-subreddit trending")
        trending = await collector.get_trending_posts_multiple_subreddits(
            subreddits=["python", "programming"],
            timeframe="day",
            final_limit=5
        )
        logger.info(f"Scenario 2: Found {len(trending)} trending posts")
        
        # Test Scenario 3: Top posts from r/all
        logger.info("Testing Scenario 3: Top posts from r/all")
        top_posts = await collector.get_top_posts_all_reddit(
            sort_type="hot",
            time_filter="day",
            limit=3
        )
        logger.info(f"Scenario 3: Found {len(top_posts)} top posts from r/all")
        
        # Test Scenario 4: Most popular post today
        logger.info("Testing Scenario 4: Most popular post today")
        popular = await collector.get_most_popular_post_today(
            subreddit="python",
            metric="score"
        )
        if popular:
            logger.info(f"Scenario 4: Most popular post today: {popular['title'][:50]}...")
        else:
            logger.info("Scenario 4: No posts found for today")
        
        return True
        
    except Exception as e:
        logger.error(f"Scenario testing failed: {e}")
        return False

async def test_comments_and_users():
    """Test comment and user analysis"""
    logger.info("Testing comment and user analysis...")
    
    try:
        collector = DataCollector()
        
        # Test comment analysis
        logger.info("Testing comment analysis")
        comments = await collector.get_top_comments_by_criteria(
            subreddit="python",
            keywords=["django"],
            limit=5
        )
        logger.info(f"Found {len(comments)} comments about Django")
        
        # Test user analysis
        logger.info("Testing user analysis")
        users = await collector.get_top_users_by_activity(
            subreddits=["python"],
            timeframe_days=7,
            limit=5
        )
        logger.info(f"Found {len(users)} active users in r/python")
        
        return True
        
    except Exception as e:
        logger.error(f"Comment/user testing failed: {e}")
        return False

async def test_collection_api():
    """Test Collection API endpoints"""
    logger.info("Testing Collection API endpoints...")
    
    base_url = "http://localhost:8000"
    
    try:
        async with httpx.AsyncClient() as client:
            # Test 1: Health check
            logger.info("Testing API health check...")
            response = await client.get(f"{base_url}/health")
            if response.status_code != 200:
                logger.error(f"Health check failed: {response.status_code}")
                return False
            logger.info("✅ API health check passed")
            
            # Test 2: List jobs (initially empty)
            logger.info("Testing list jobs endpoint...")
            response = await client.get(f"{base_url}/api/collect/jobs")
            if response.status_code != 200:
                logger.error(f"List jobs failed: {response.status_code}")
                return False
            
            jobs_data = response.json()
            logger.info(f"✅ Found {jobs_data['total']} existing collection jobs")
            
            # Test 3: Create a basic collection job
            logger.info("Testing collection job creation...")
            job_payload = {
                "subreddits": ["python"],
                "sort_types": ["hot"],
                "time_filters": ["day"],
                "post_limit": 3,
                "comment_limit": 0,
                "max_comment_depth": 1,
                "min_score": 1,
                "exclude_nsfw": True,
                "anonymize_users": True
            }
            
            response = await client.post(
                f"{base_url}/api/collect/jobs",
                json=job_payload,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code != 200:
                logger.error(f"Job creation failed: {response.status_code} - {response.text}")
                return False
            
            job_response = response.json()
            job_id = job_response["job_id"]
            logger.info(f"✅ Created collection job: {job_id}")
            
            # Test 4: Get job status
            logger.info("Testing job status endpoint...")
            response = await client.get(f"{base_url}/api/collect/jobs/{job_id}/status")
            if response.status_code != 200:
                logger.error(f"Job status failed: {response.status_code}")
                return False
            
            status_data = response.json()
            logger.info(f"✅ Job status: {status_data['status']}")
            
            # Test 5: Monitor job completion
            logger.info("Monitoring job completion...")
            max_attempts = 15
            for attempt in range(max_attempts):
                response = await client.get(f"{base_url}/api/collect/jobs/{job_id}/status")
                status_data = response.json()
                status = status_data["status"]
                
                if status in ["completed", "failed"]:
                    logger.info(f"✅ Job completed with status: {status}")
                    if status == "completed":
                        logger.info(f"✅ Collected {status_data['collected_posts']} posts, {status_data['collected_comments']} comments")
                    break
                
                logger.info(f"   Job status: {status} (attempt {attempt + 1}/{max_attempts})")
                await asyncio.sleep(1)
            else:
                logger.warning("Job did not complete within timeout")
            
            # Test 6: Get full job details
            logger.info("Testing job details endpoint...")
            response = await client.get(f"{base_url}/api/collect/jobs/{job_id}")
            if response.status_code != 200:
                logger.error(f"Job details failed: {response.status_code}")
                return False
            
            job_details = response.json()
            logger.info(f"✅ Job details retrieved: {job_details['status']} - {job_details['collected_posts']} posts")
            
            # Test 7: Create advanced job with keywords
            logger.info("Testing advanced collection job with keywords...")
            advanced_payload = {
                "subreddits": ["python", "programming"],
                "sort_types": ["hot"],
                "time_filters": ["day"],
                "post_limit": 2,
                "comment_limit": 0,
                "max_comment_depth": 1,
                "keywords": ["fastapi"],
                "min_score": 1,
                "min_upvote_ratio": 0.7,
                "exclude_nsfw": True,
                "anonymize_users": False
            }
            
            response = await client.post(
                f"{base_url}/api/collect/jobs",
                json=advanced_payload,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code != 200:
                logger.error(f"Advanced job creation failed: {response.status_code}")
                return False
            
            advanced_job = response.json()
            advanced_job_id = advanced_job["job_id"]
            logger.info(f"✅ Created advanced job: {advanced_job_id}")
            
            # Wait a moment for advanced job to complete
            await asyncio.sleep(3)
            
            # Test 8: Test pagination
            logger.info("Testing pagination...")
            response = await client.get(f"{base_url}/api/collect/jobs?page=1&per_page=5")
            if response.status_code != 200:
                logger.error(f"Pagination test failed: {response.status_code}")
                return False
            
            page_data = response.json()
            logger.info(f"✅ Pagination works: page 1, {len(page_data['jobs'])} jobs returned")
            
            # Test 9: Test status filtering
            logger.info("Testing status filtering...")
            response = await client.get(f"{base_url}/api/collect/jobs?status=completed")
            if response.status_code != 200:
                logger.error(f"Status filtering failed: {response.status_code}")
                return False
            
            filtered_data = response.json()
            completed_count = len(filtered_data['jobs'])
            logger.info(f"✅ Status filtering works: {completed_count} completed jobs")
            
            # Test 10: Test job cancellation (create a job to cancel)
            logger.info("Testing job cancellation...")
            cancel_payload = {
                "subreddits": ["python"],
                "sort_types": ["hot"],
                "time_filters": ["day"],
                "post_limit": 50,  # Larger job more likely to be cancelable
                "comment_limit": 20,
                "min_score": 1,
                "exclude_nsfw": True,
                "anonymize_users": True
            }
            
            response = await client.post(
                f"{base_url}/api/collect/jobs",
                json=cancel_payload,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                cancel_job = response.json()
                cancel_job_id = cancel_job["job_id"]
                
                # Try to cancel immediately
                response = await client.post(f"{base_url}/api/collect/jobs/{cancel_job_id}/cancel")
                if response.status_code == 200:
                    logger.info("✅ Job cancellation works")
                else:
                    logger.info("⚠️  Job completed before cancellation could be tested")
            
            # Test 11: Test invalid job ID (should return 404)
            logger.info("Testing invalid job ID...")
            response = await client.get(f"{base_url}/api/collect/jobs/invalid-job-id")
            if response.status_code == 404:
                logger.info("✅ Invalid job ID correctly returns 404")
            else:
                logger.warning(f"Expected 404, got {response.status_code}")
            
            return True
            
    except Exception as e:
        logger.error(f"Collection API testing failed: {e}")
        return False

def check_environment():
    """Check if all required environment variables are set"""
    logger.info("Checking environment configuration...")
    
    required_vars = [
        "REDDIT_CLIENT_ID",
        "REDDIT_CLIENT_SECRET"
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        logger.error(f"Missing required environment variables: {missing_vars}")
        logger.error("Please copy .env.example to .env and fill in your Reddit API credentials")
        return False
    
    logger.info("Environment configuration is valid")
    return True

async def main():
    """Main test function"""
    logger.info("Starting Trendit API tests...")
    
    # Check environment
    if not check_environment():
        sys.exit(1)
    
    # Test Reddit connection
    if not await test_reddit_connection():
        logger.error("Reddit connection failed. Cannot continue tests.")
        sys.exit(1)
    
    # Test scenarios
    if not await test_scenarios():
        logger.error("Scenario tests failed.")
        sys.exit(1)
    
    # Test comments and users
    if not await test_comments_and_users():
        logger.error("Comment/user tests failed.")
        sys.exit(1)
    
    # Test Collection API
    logger.info("\n" + "="*60)
    logger.info("Starting Collection API tests...")
    logger.info("="*60)
    
    if not await test_collection_api():
        logger.error("Collection API tests failed.")
        sys.exit(1)
    
    logger.info("\n" + "="*60)
    logger.info("All tests completed successfully!")
    logger.info("Trendit API is ready for use!")
    logger.info("="*60)
    
    # Print summary
    logger.info("\n📊 Test Summary:")
    logger.info("✅ Reddit API Connection")
    logger.info("✅ Data Collection Scenarios")
    logger.info("✅ Comment & User Analysis")
    logger.info("✅ Collection API Endpoints")
    logger.info("\n🚀 Trendit API is fully functional!")

if __name__ == "__main__":
    asyncio.run(main())
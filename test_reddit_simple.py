#!/usr/bin/env python3
"""
Simple Reddit API test to verify credentials
"""

import praw
import os
from dotenv import load_dotenv

load_dotenv()

def test_reddit_basic():
    """Test basic Reddit connection"""
    print("Testing Reddit API connection...")
    
    client_id = os.getenv("REDDIT_CLIENT_ID")
    client_secret = os.getenv("REDDIT_CLIENT_SECRET")
    user_agent = os.getenv("REDDIT_USER_AGENT")
    
    print(f"Client ID: {client_id}")
    print(f"User Agent: {user_agent}")
    print(f"Client Secret: {'*' * len(client_secret) if client_secret else 'None'}")
    
    try:
        reddit = praw.Reddit(
            client_id=client_id,
            client_secret=client_secret,
            user_agent=user_agent
        )
        
        print(f"Read-only mode: {reddit.read_only}")
        
        # Try to access a simple subreddit
        subreddit = reddit.subreddit("python")
        print(f"Subreddit: {subreddit.display_name}")
        print(f"Subscribers: {subreddit.subscribers}")
        
        # Try to get one post
        for submission in subreddit.hot(limit=1):
            print(f"Test post: {submission.title[:50]}...")
            break
            
        print("✅ Reddit API connection successful!")
        return True
        
    except Exception as e:
        print(f"❌ Reddit API connection failed: {e}")
        return False

if __name__ == "__main__":
    test_reddit_basic()
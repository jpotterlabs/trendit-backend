"""
Date Range Filtering Fix for Trendit Reddit Collection

This module provides improved date filtering logic to fix the issue where
collection jobs find hundreds of posts but filter them all out due to
overly restrictive date ranges and conflicting time filters.

Key improvements:
1. Proper timezone handling (UTC)
2. Lenient date filtering with buffers
3. Optimal Reddit time_filter selection
4. Diagnostic tools for debugging
"""

from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Tuple, List
import logging

logger = logging.getLogger(__name__)

class ImprovedDateFiltering:
    """Improved date filtering logic for Reddit data collection."""
    
    @staticmethod
    def create_date_range_with_buffer(days: int = 7, buffer_hours: int = 4) -> Tuple[datetime, datetime]:
        """
        Create a date range with buffer to account for Reddit's time filtering.
        
        Args:
            days: Number of days to look back
            buffer_hours: Additional hours to add as buffer for Reddit's filtering
        
        Returns:
            Tuple of (date_from, date_to) in UTC
        """
        now_utc = datetime.now(timezone.utc)
        date_to = now_utc
        # Add buffer to ensure we don't miss posts due to Reddit's internal filtering
        date_from = now_utc - timedelta(days=days, hours=buffer_hours)
        
        logger.info(f"Created date range: {date_from} to {date_to} (with {buffer_hours}h buffer)")
        return date_from, date_to
    
    @staticmethod
    def select_optimal_time_filter(days: int) -> str:
        """
        Select the most appropriate Reddit time_filter based on desired day range.
        
        Reddit's time_filter options and their approximate ranges:
        - hour: ~1 hour
        - day: ~24 hours  
        - week: ~7 days
        - month: ~30 days
        - year: ~365 days
        - all: all time
        """
        if days <= 1:
            return "day"  # Use "day" instead of "hour" for better coverage
        elif days <= 7:
            return "week"
        elif days <= 30:
            return "month"
        elif days <= 365:
            return "year"
        else:
            return "all"
    
    @staticmethod
    def should_include_post(post_data: Dict[str, Any], date_from: datetime, date_to: datetime) -> bool:
        """
        Determine if a post should be included based on lenient date filtering.
        
        Args:
            post_data: Reddit post data dictionary
            date_from: Start date (UTC)
            date_to: End date (UTC)
        
        Returns:
            Boolean indicating whether post should be included
        """
        try:
            # Handle both datetime objects and timestamps
            created_utc = post_data.get('created_utc')
            if created_utc is None:
                logger.warning(f"Post missing created_utc: {post_data.get('reddit_id', 'unknown')}")
                return False
            
            if isinstance(created_utc, datetime):
                post_datetime = created_utc
                # Ensure timezone awareness
                if post_datetime.tzinfo is None:
                    post_datetime = post_datetime.replace(tzinfo=timezone.utc)
            else:
                # Assume it's a timestamp
                post_datetime = datetime.fromtimestamp(created_utc, tz=timezone.utc)
            
            # Use lenient filtering - allow posts slightly outside the range
            # This accounts for Reddit's internal time filtering behavior
            buffer = timedelta(hours=2)
            is_within_range = (date_from - buffer) <= post_datetime <= (date_to + buffer)
            
            if not is_within_range:
                logger.debug(f"Post {post_data.get('reddit_id')} outside range: {post_datetime}")
            
            return is_within_range
                
        except (AttributeError, ValueError, OSError, TypeError) as e:
            logger.error(f"Error processing post date for {post_data.get('reddit_id')}: {e}")
            return False
    
    @staticmethod
    def diagnose_date_filtering(posts_data: List[Dict[str, Any]], date_from: datetime, date_to: datetime):
        """
        Analyze posts to understand date filtering behavior.
        """
        if not posts_data:
            logger.info("No posts to analyze for date filtering diagnosis")
            return
        
        post_dates = []
        for post in posts_data:
            try:
                created_utc = post.get('created_utc')
                if created_utc:
                    if isinstance(created_utc, datetime):
                        post_date = created_utc
                        if post_date.tzinfo is None:
                            post_date = post_date.replace(tzinfo=timezone.utc)
                    else:
                        post_date = datetime.fromtimestamp(created_utc, tz=timezone.utc)
                    post_dates.append(post_date)
            except:
                continue
        
        if post_dates:
            earliest = min(post_dates)
            latest = max(post_dates)
            
            logger.info("=== Date Filtering Diagnosis ===")
            logger.info(f"Filter range: {date_from} to {date_to}")
            logger.info(f"Posts date range: {earliest} to {latest}")
            logger.info(f"Posts before filter start: {sum(1 for d in post_dates if d < date_from)}")
            logger.info(f"Posts after filter end: {sum(1 for d in post_dates if d > date_to)}")
            logger.info(f"Posts within range: {sum(1 for d in post_dates if date_from <= d <= date_to)}")
            logger.info(f"Total posts analyzed: {len(post_dates)}")
            
            # Show time distribution
            within_buffer = sum(1 for d in post_dates 
                              if (date_from - timedelta(hours=2)) <= d <= (date_to + timedelta(hours=2)))
            logger.info(f"Posts within range (with 2h buffer): {within_buffer}")


def apply_improved_date_filtering(posts_data: List[Dict[str, Any]], 
                                days: int = 7,
                                debug: bool = False) -> List[Dict[str, Any]]:
    """
    Apply improved date filtering to a list of posts.
    
    Args:
        posts_data: List of post dictionaries
        days: Number of days for the filter range
        debug: Enable debug logging
    
    Returns:
        Filtered list of posts
    """
    if not posts_data:
        return []
    
    # Create optimal date range
    date_from, date_to = ImprovedDateFiltering.create_date_range_with_buffer(days)
    
    if debug:
        ImprovedDateFiltering.diagnose_date_filtering(posts_data, date_from, date_to)
    
    # Apply lenient filtering
    filtered_posts = []
    for post in posts_data:
        if ImprovedDateFiltering.should_include_post(post, date_from, date_to):
            filtered_posts.append(post)
    
    logger.info(f"Date filtering: {len(posts_data)} -> {len(filtered_posts)} posts")
    
    if debug and len(filtered_posts) == 0 and len(posts_data) > 0:
        logger.warning("All posts were filtered out! This might indicate a date filtering issue.")
        ImprovedDateFiltering.diagnose_date_filtering(posts_data, date_from, date_to)
    
    return filtered_posts
import praw
import os
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import time
import logging
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

class RedditClient:                             
    """
    Comprehensive Reddit API client using PRAW
    """
    
    def __init__(self):
        self.client_id = os.getenv("REDDIT_CLIENT_ID")
        self.client_secret = os.getenv("REDDIT_CLIENT_SECRET") 
        self.user_agent = os.getenv("REDDIT_USER_AGENT", "Trendit/1.0")
        
        if not all([self.client_id, self.client_secret]):
            raise ValueError("Reddit API credentials not found in environment variables")
        
        self._reddit = None
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize the PRAW Reddit client"""
        try:
            self._reddit = praw.Reddit(
                client_id=self.client_id,
                client_secret=self.client_secret,
                user_agent=self.user_agent
            )
            
            # Test the connection
            logger.info(f"Reddit client initialized. Read-only: {self._reddit.read_only}")
            
        except Exception as e:
            logger.error(f"Failed to initialize Reddit client: {e}")
            raise
    
    @property
    def reddit(self) -> praw.Reddit:
        """Get the PRAW Reddit instance"""
        if self._reddit is None:
            self._initialize_client()
        return self._reddit
    
    def get_subreddit_posts(
        self,
        subreddit_name: str,
        sort_type: str = "hot",
        time_filter: str = "all",
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get posts from a subreddit
        
        Args:
            subreddit_name: Name of the subreddit
            sort_type: hot, new, top, rising, controversial
            time_filter: hour, day, week, month, year, all (for top/controversial)
            limit: Maximum number of posts to retrieve
        
        Returns:
            List of post dictionaries
        """
        try:
            subreddit = self.reddit.subreddit(subreddit_name)
            posts = []
            
            # Get posts based on sort type
            if sort_type == "hot":
                submission_generator = subreddit.hot(limit=limit)
            elif sort_type == "new":
                submission_generator = subreddit.new(limit=limit)
            elif sort_type == "top":
                submission_generator = subreddit.top(time_filter=time_filter, limit=limit)
            elif sort_type == "rising":
                submission_generator = subreddit.rising(limit=limit)
            elif sort_type == "controversial":
                submission_generator = subreddit.controversial(time_filter=time_filter, limit=limit)
            else:
                raise ValueError(f"Invalid sort type: {sort_type}")
            
            for submission in submission_generator:
                post_data = self._extract_post_data(submission)
                posts.append(post_data)
                
                # Rate limiting
                time.sleep(0.1)
            
            logger.info(f"Retrieved {len(posts)} posts from r/{subreddit_name}")
            return posts
            
        except Exception as e:
            logger.error(f"Error retrieving posts from r/{subreddit_name}: {e}")
            raise
    
    def get_post_comments(
        self,
        submission_id: str,
        max_comments: int = 50,
        max_depth: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Get comments for a specific post
        
        Args:
            submission_id: Reddit submission ID
            max_comments: Maximum number of comments to retrieve
            max_depth: Maximum comment thread depth
        
        Returns:
            List of comment dictionaries
        """
        try:
            submission = self.reddit.submission(id=submission_id)
            submission.comments.replace_more(limit=0)  # Remove MoreComments objects
            
            comments = []
            comment_count = 0
            
            def process_comment(comment, depth=0):
                nonlocal comment_count
                if comment_count >= max_comments or depth > max_depth:
                    return
                
                if hasattr(comment, 'body'):  # Ensure it's a real comment
                    comment_data = self._extract_comment_data(comment, depth)
                    comments.append(comment_data)
                    comment_count += 1
                    
                    # Process replies
                    for reply in comment.replies:
                        process_comment(reply, depth + 1)
            
            # Process all top-level comments
            for comment in submission.comments:
                process_comment(comment)
            
            logger.info(f"Retrieved {len(comments)} comments for post {submission_id}")
            return comments
            
        except Exception as e:
            logger.error(f"Error retrieving comments for post {submission_id}: {e}")
            raise
    
    def search_posts(
        self,
        query: str,
        subreddit_name: Optional[str] = None,
        sort: str = "relevance",
        time_filter: str = "all",
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Search for posts across Reddit or within a subreddit
        
        Args:
            query: Search query
            subreddit_name: Subreddit to search in (None for all of Reddit)
            sort: relevance, hot, top, new, comments
            time_filter: hour, day, week, month, year, all
            limit: Maximum results
        
        Returns:
            List of matching post dictionaries
        """
        try:
            if subreddit_name:
                subreddit = self.reddit.subreddit(subreddit_name)
                search_results = subreddit.search(
                    query=query,
                    sort=sort,
                    time_filter=time_filter,
                    limit=limit
                )
            else:
                search_results = self.reddit.subreddit("all").search(
                    query=query,
                    sort=sort,
                    time_filter=time_filter,
                    limit=limit
                )
            
            posts = []
            for submission in search_results:
                post_data = self._extract_post_data(submission)
                posts.append(post_data)
                time.sleep(0.1)  # Rate limiting
            
            logger.info(f"Found {len(posts)} posts matching query: {query}")
            return posts
            
        except Exception as e:
            logger.error(f"Error searching posts: {e}")
            raise
    
    def get_user_posts(
        self,
        username: str,
        sort: str = "new",
        time_filter: str = "all",
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get posts by a specific user
        
        Args:
            username: Reddit username
            sort: new, hot, top
            time_filter: hour, day, week, month, year, all
            limit: Maximum posts
        
        Returns:
            List of user's post dictionaries
        """
        try:
            redditor = self.reddit.redditor(username)
            
            if sort == "new":
                submissions = redditor.submissions.new(limit=limit)
            elif sort == "hot":
                submissions = redditor.submissions.hot(limit=limit)
            elif sort == "top":
                submissions = redditor.submissions.top(time_filter=time_filter, limit=limit)
            else:
                raise ValueError(f"Invalid sort type: {sort}")
            
            posts = []
            for submission in submissions:
                post_data = self._extract_post_data(submission)
                posts.append(post_data)
                time.sleep(0.1)
            
            logger.info(f"Retrieved {len(posts)} posts from user u/{username}")
            return posts
            
        except Exception as e:
            logger.error(f"Error retrieving posts from user u/{username}: {e}")
            raise
    
    def get_user_info(self, username: str) -> Dict[str, Any]:
        """
        Get information about a Reddit user
        
        Args:
            username: Reddit username
        
        Returns:
            User information dictionary
        """
        try:
            redditor = self.reddit.redditor(username)
            
            user_data = {
                "username": redditor.name,
                "user_id": redditor.id if hasattr(redditor, 'id') else None,
                "comment_karma": getattr(redditor, 'comment_karma', 0),
                "link_karma": getattr(redditor, 'link_karma', 0),
                "total_karma": getattr(redditor, 'total_karma', 0),
                "account_created": datetime.fromtimestamp(redditor.created_utc) if hasattr(redditor, 'created_utc') else None,
                "is_employee": getattr(redditor, 'is_employee', False),
                "is_mod": getattr(redditor, 'is_mod', False),
                "is_gold": getattr(redditor, 'is_gold', False),
                "has_verified_email": getattr(redditor, 'has_verified_email', False),
                "collected_at": datetime.utcnow()
            }
            
            logger.info(f"Retrieved user info for u/{username}")
            return user_data
            
        except Exception as e:
            logger.error(f"Error retrieving user info for u/{username}: {e}")
            raise
    
    def get_subreddit_info(self, subreddit_name: str) -> Dict[str, Any]:
        """
        Get information about a subreddit
        
        Args:
            subreddit_name: Name of the subreddit
        
        Returns:
            Subreddit information dictionary
        """
        try:
            subreddit = self.reddit.subreddit(subreddit_name)
            
            subreddit_data = {
                "name": subreddit.display_name,
                "title": subreddit.title,
                "description": subreddit.description,
                "subscribers": subreddit.subscribers,
                "created_utc": datetime.fromtimestamp(subreddit.created_utc),
                "is_nsfw": subreddit.over18,
                "public_description": subreddit.public_description,
                "language": getattr(subreddit, 'lang', None),
                "collected_at": datetime.utcnow()
            }
            
            logger.info(f"Retrieved subreddit info for r/{subreddit_name}")
            return subreddit_data
            
        except Exception as e:
            logger.error(f"Error retrieving subreddit info for r/{subreddit_name}: {e}")
            raise
    
    def _extract_post_data(self, submission) -> Dict[str, Any]:
        """Extract relevant data from a PRAW submission object"""
        return {
            "reddit_id": submission.id,
            "title": submission.title,
            "selftext": submission.selftext,
            "url": submission.url,
            "permalink": submission.permalink,
            "subreddit": submission.subreddit.display_name,
            "author": submission.author.name if submission.author else None,
            "author_id": submission.author.name if submission.author else None,
            "score": submission.score,
            "upvote_ratio": submission.upvote_ratio,
            "num_comments": submission.num_comments,
            "awards_received": submission.total_awards_received,
            "is_nsfw": submission.over_18,
            "is_spoiler": submission.spoiler,
            "is_stickied": submission.stickied,
            "post_hint": getattr(submission, 'post_hint', None),
            "created_utc": datetime.fromtimestamp(submission.created_utc),
            "collected_at": datetime.utcnow()
        }
    
    def _extract_comment_data(self, comment, depth: int = 0) -> Dict[str, Any]:
        """Extract relevant data from a PRAW comment object"""
        return {
            "reddit_id": comment.id,
            "body": comment.body,
            "parent_id": comment.parent_id,
            "author": comment.author.name if comment.author else None,
            "author_id": comment.author.name if comment.author else None,
            "depth": depth,
            "score": comment.score,
            "awards_received": comment.total_awards_received,
            "is_submitter": comment.is_submitter,
            "is_stickied": comment.stickied,
            "created_utc": datetime.fromtimestamp(comment.created_utc),
            "collected_at": datetime.utcnow()
        }
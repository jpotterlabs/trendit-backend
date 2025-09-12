from fastapi import APIRouter, HTTPException, Query as FastAPIQuery, Depends
from typing import List, Optional, Dict, Any
from datetime import datetime, date, timezone, timedelta
from pydantic import BaseModel, Field
import time
import logging

from services.data_collector import DataCollector
from services.date_filter_fix import ImprovedDateFiltering
from models.models import User
from api.auth import require_api_call_limit

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/query", tags=["query"])
collector = DataCollector()

# Request Models
class PostQueryRequest(BaseModel):
    """Advanced post query parameters"""
    subreddits: List[str] = Field(..., description="List of subreddit names")
    keywords: Optional[List[str]] = Field(None, description="Keywords to search for")
    exclude_keywords: Optional[List[str]] = Field(None, description="Keywords to exclude")
    
    # Date filtering
    date_from: Optional[datetime] = Field(None, description="Start date (ISO format)")
    date_to: Optional[datetime] = Field(None, description="End date (ISO format)")
    
    # Score filtering
    min_score: Optional[int] = Field(None, description="Minimum post score")
    max_score: Optional[int] = Field(None, description="Maximum post score")
    min_upvote_ratio: Optional[float] = Field(None, description="Minimum upvote ratio (0.0-1.0)")
    max_upvote_ratio: Optional[float] = Field(None, description="Maximum upvote ratio (0.0-1.0)")
    
    # Comment filtering
    min_comments: Optional[int] = Field(None, description="Minimum number of comments")
    max_comments: Optional[int] = Field(None, description="Maximum number of comments")
    
    # Author filtering
    include_authors: Optional[List[str]] = Field(None, description="Include only these authors")
    exclude_authors: Optional[List[str]] = Field(None, description="Exclude these authors")
    exclude_deleted: bool = Field(True, description="Exclude deleted posts")
    exclude_removed: bool = Field(True, description="Exclude removed posts")
    
    # Content filtering
    content_types: Optional[List[str]] = Field(None, description="Content types: text, link, image, video")
    exclude_nsfw: bool = Field(True, description="Exclude NSFW content")
    exclude_spoilers: bool = Field(True, description="Exclude spoiler content")
    exclude_stickied: bool = Field(True, description="Exclude stickied posts")
    
    # Reddit API parameters
    sort_type: str = Field("hot", description="Sort type: hot, new, top, rising, controversial")
    time_filter: str = Field("all", description="Time filter: hour, day, week, month, year, all")
    limit: int = Field(100, description="Maximum results (1-1000)")
    
    # Advanced options
    include_self_text: bool = Field(True, description="Include post self text")
    include_awards: bool = Field(False, description="Include award information")
    
class CommentQueryRequest(BaseModel):
    """Advanced comment query parameters"""
    subreddits: Optional[List[str]] = Field(None, description="List of subreddit names")
    post_ids: Optional[List[str]] = Field(None, description="Specific post IDs to get comments from")
    keywords: Optional[List[str]] = Field(None, description="Keywords to search for in comments")
    exclude_keywords: Optional[List[str]] = Field(None, description="Keywords to exclude")
    
    # Score filtering
    min_score: Optional[int] = Field(None, description="Minimum comment score")
    max_score: Optional[int] = Field(None, description="Maximum comment score")
    
    # Author filtering
    include_authors: Optional[List[str]] = Field(None, description="Include only these authors")
    exclude_authors: Optional[List[str]] = Field(None, description="Exclude these authors")
    exclude_deleted: bool = Field(True, description="Exclude deleted comments")
    exclude_removed: bool = Field(True, description="Exclude removed comments")
    
    # Comment structure
    max_depth: Optional[int] = Field(None, description="Maximum comment depth")
    min_depth: Optional[int] = Field(None, description="Minimum comment depth")
    include_op_replies: Optional[bool] = Field(None, description="Include/exclude OP replies")
    
    # Reddit API parameters
    sort_type: str = Field("top", description="Sort type: top, new, best, controversial")
    limit: int = Field(100, description="Maximum results (1-1000)")
    
class UserQueryRequest(BaseModel):
    """Advanced user query parameters"""
    usernames: Optional[List[str]] = Field(None, description="Specific usernames to analyze")
    subreddits: Optional[List[str]] = Field(None, description="Find active users in these subreddits")
    
    # Karma filtering
    min_comment_karma: Optional[int] = Field(None, description="Minimum comment karma")
    min_link_karma: Optional[int] = Field(None, description="Minimum link karma")
    min_total_karma: Optional[int] = Field(None, description="Minimum total karma")
    
    # Account age
    min_account_age_days: Optional[int] = Field(None, description="Minimum account age in days")
    max_account_age_days: Optional[int] = Field(None, description="Maximum account age in days")
    
    # Activity filtering
    min_post_count: Optional[int] = Field(None, description="Minimum post count in timeframe")
    min_comment_count: Optional[int] = Field(None, description="Minimum comment count in timeframe")
    timeframe_days: int = Field(30, description="Days to look back for activity")
    
    # User attributes
    include_verified_only: Optional[bool] = Field(None, description="Only verified email users")
    include_premium_only: Optional[bool] = Field(None, description="Only Reddit premium users")
    exclude_suspended: bool = Field(True, description="Exclude suspended accounts")
    
    limit: int = Field(50, description="Maximum results (1-500)")

# Response Models
class QueryResponse(BaseModel):
    """Standard query response format"""
    query_type: str
    parameters: Dict[str, Any]
    results: List[Dict[str, Any]]
    count: int
    execution_time_ms: float
    reddit_api_calls: int
    filters_applied: List[str]

# POST Endpoints for complex queries
@router.post("/posts", response_model=QueryResponse)
async def query_posts(
    request: PostQueryRequest,
    current_user: User = Depends(require_api_call_limit)
):
    """
    Advanced post query with comprehensive filtering options.
    
    Supports complex queries like:
    - Posts from multiple subreddits with keyword filtering
    - Score and engagement thresholds  
    - Author inclusion/exclusion
    - Content type filtering
    - Date range filtering
    """
    try:
        start_time = time.time()
        
        # Convert request to parameters
        filters_applied = []
        reddit_calls = 0
        all_results = []
        
        # Use user-provided sort and time_filter parameters directly
        effective_sort_type = request.sort_type
        effective_time_filter = request.time_filter
        
        for subreddit in request.subreddits:
            reddit_calls += 1
            
            # Build search query if keywords provided
            if request.keywords:
                search_query = " OR ".join(request.keywords)
                async with collector.reddit_client as reddit:
                    posts = await reddit.search_posts(
                        query=search_query,
                        subreddit_name=subreddit,
                        sort=effective_sort_type,
                        time_filter=effective_time_filter,
                        limit=min(request.limit * 2, 1000)  # Get extra for filtering
                    )
                filters_applied.append("keyword_search")
            else:
                # Get posts by sort type
                async with collector.reddit_client as reddit:
                    posts = await reddit.get_subreddit_posts(
                        subreddit_name=subreddit,
                        sort_type=effective_sort_type,
                        time_filter=effective_time_filter,
                        limit=min(request.limit * 2, 1000)
                    )
            
            all_results.extend(posts)
        
        # Apply filters
        filtered_results = []
        
        for post in all_results:
            # Date filtering - use improved logic with buffers
            if request.date_from or request.date_to:
                # Create date range for filtering (using timezone-aware datetimes)
                if request.date_from and request.date_to:
                    # Use the improved date filtering logic
                    if not ImprovedDateFiltering.should_include_post(post, request.date_from, request.date_to):
                        continue
                elif request.date_from:
                    # Only start date provided - use raw date, let ImprovedDateFiltering handle buffering
                    if not ImprovedDateFiltering.should_include_post(post, request.date_from, datetime.now(timezone.utc)):
                        continue
                elif request.date_to:
                    # Only end date provided - use raw date, let ImprovedDateFiltering handle buffering
                    # Use a very early date as the start to allow all posts before end date
                    very_early_date = datetime(2005, 1, 1, tzinfo=timezone.utc)  # Before Reddit existed
                    if not ImprovedDateFiltering.should_include_post(post, very_early_date, request.date_to):
                        continue
            
            # Score filtering
            if request.min_score and post.get('score', 0) < request.min_score:
                continue
            if request.max_score and post.get('score', 0) > request.max_score:
                continue
                
            # Upvote ratio filtering
            if request.min_upvote_ratio and post.get('upvote_ratio', 0) < request.min_upvote_ratio:
                continue
            if request.max_upvote_ratio and post.get('upvote_ratio', 1) > request.max_upvote_ratio:
                continue
                
            # Comment count filtering
            if request.min_comments and post.get('num_comments', 0) < request.min_comments:
                continue
            if request.max_comments and post.get('num_comments', 0) > request.max_comments:
                continue
                
            # Author filtering
            author = post.get('author')
            if request.include_authors and author not in request.include_authors:
                continue
            if request.exclude_authors and author in request.exclude_authors:
                continue
            if request.exclude_deleted and not author:
                continue
                
            # Content filtering
            if request.exclude_nsfw and post.get('is_nsfw', False):
                continue
            if request.exclude_spoilers and post.get('is_spoiler', False):
                continue
            if request.exclude_stickied and post.get('is_stickied', False):
                continue
                
            # Keyword exclusion
            if request.exclude_keywords:
                title_text = (post.get('title', '') + ' ' + post.get('selftext', '')).lower()
                if any(keyword.lower() in title_text for keyword in request.exclude_keywords):
                    continue
                    
            filtered_results.append(post)
            
            if len(filtered_results) >= request.limit:
                break
        
        # Track applied filters
        if request.date_from or request.date_to:
            filters_applied.append("date_range")
        if request.min_score or request.max_score:
            filters_applied.append("score_range")
        if request.exclude_keywords:
            filters_applied.append("keyword_exclusion")
        if request.include_authors or request.exclude_authors:
            filters_applied.append("author_filtering")
        if not request.include_self_text:
            # Remove selftext if not requested
            for post in filtered_results:
                post.pop('selftext', None)
        
        execution_time = (time.time() - start_time) * 1000
        
        return QueryResponse(
            query_type="posts",
            parameters=request.dict(),
            results=filtered_results,
            count=len(filtered_results),
            execution_time_ms=execution_time,
            reddit_api_calls=reddit_calls,
            filters_applied=filters_applied
        )
        
    except Exception as e:
        logger.error(f"Post query failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/comments", response_model=QueryResponse)
async def query_comments(
    request: CommentQueryRequest,
    current_user: User = Depends(require_api_call_limit)
):
    """
    Advanced comment query with comprehensive filtering options.
    
    Supports queries like:
    - Comments from specific posts or subreddits
    - Score and depth filtering
    - Author filtering
    - Content filtering
    """
    try:
        start_time = time.time()
        filters_applied = []
        reddit_calls = 0
        all_results = []
        
        if request.post_ids:
            # Get comments from specific posts
            async with collector.reddit_client as reddit:
                for post_id in request.post_ids:
                    reddit_calls += 1
                    comments = await reddit.get_post_comments(
                        submission_id=post_id,
                        max_comments=request.limit
                    )
                    all_results.extend(comments)
                
        elif request.subreddits:
            # Search comments in subreddits (via recent posts)
            async with collector.reddit_client as reddit:
                for subreddit in request.subreddits:
                    reddit_calls += 1
                    # Get recent posts to find comments
                    posts = await reddit.get_subreddit_posts(
                        subreddit_name=subreddit,
                        sort_type="new",
                        limit=20  # Get recent posts to search their comments
                    )
                    
                    for post in posts:
                        reddit_calls += 1
                        comments = await reddit.get_post_comments(
                            submission_id=post['reddit_id'],
                            max_comments=50
                        )
                        all_results.extend(comments)
        
        # Apply filters
        filtered_results = []
        
        for comment in all_results:
            # Score filtering
            if request.min_score and comment.get('score', 0) < request.min_score:
                continue
            if request.max_score and comment.get('score', 0) > request.max_score:
                continue
                
            # Depth filtering
            if request.min_depth and comment.get('depth', 0) < request.min_depth:
                continue
            if request.max_depth and comment.get('depth', 0) > request.max_depth:
                continue
                
            # Author filtering
            author = comment.get('author')
            if request.include_authors and author not in request.include_authors:
                continue
            if request.exclude_authors and author in request.exclude_authors:
                continue
            if request.exclude_deleted and not author:
                continue
                
            # Keyword filtering
            if request.keywords:
                comment_text = comment.get('body', '').lower()
                if not any(keyword.lower() in comment_text for keyword in request.keywords):
                    continue
                    
            if request.exclude_keywords:
                comment_text = comment.get('body', '').lower()
                if any(keyword.lower() in comment_text for keyword in request.exclude_keywords):
                    continue
                    
            filtered_results.append(comment)
            
            if len(filtered_results) >= request.limit:
                break
        
        execution_time = (time.time() - start_time) * 1000
        
        return QueryResponse(
            query_type="comments",
            parameters=request.dict(),
            results=filtered_results,
            count=len(filtered_results),
            execution_time_ms=execution_time,
            reddit_api_calls=reddit_calls,
            filters_applied=filters_applied
        )
        
    except Exception as e:
        logger.error(f"Comment query failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/users", response_model=QueryResponse)
async def query_users(
    request: UserQueryRequest,
    current_user: User = Depends(require_api_call_limit)
):
    """
    Advanced user analysis and filtering.
    
    Supports queries like:
    - User profiles by username
    - Active users in subreddits
    - Users by karma thresholds
    - Account age filtering
    """
    try:
        start_time = time.time()
        filters_applied = []
        reddit_calls = 0
        all_results = []
        
        if request.usernames:
            # Get specific user profiles
            async with collector.reddit_client as reddit:
                for username in request.usernames:
                    reddit_calls += 1
                    try:
                        user_data = await reddit.get_user_info(username)
                        if user_data:
                            all_results.append(user_data)
                    except:
                        continue  # Skip invalid/suspended users
                    
        elif request.subreddits:
            # Find active users in subreddits
            seen_users = set()
            async with collector.reddit_client as reddit:
                for subreddit in request.subreddits:
                    reddit_calls += 1
                    posts = await reddit.get_subreddit_posts(
                        subreddit_name=subreddit,
                        sort_type="hot",
                        limit=100
                    )
                    
                    for post in posts:
                        author = post.get('author')
                        if author and author not in seen_users:
                            seen_users.add(author)
                            reddit_calls += 1
                            try:
                                user_data = await reddit.get_user_info(author)
                                if user_data:
                                    all_results.append(user_data)
                            except:
                                continue
        
        # Apply filters
        filtered_results = []
        
        for user in all_results:
            # Karma filtering
            if request.min_comment_karma and user.get('comment_karma', 0) < request.min_comment_karma:
                continue
            if request.min_link_karma and user.get('link_karma', 0) < request.min_link_karma:
                continue
            if request.min_total_karma and user.get('total_karma', 0) < request.min_total_karma:
                continue
                
            # Account age filtering
            if request.min_account_age_days or request.max_account_age_days:
                created = user.get('account_created')
                if created:
                    age_days = (datetime.utcnow() - created).days
                    if request.min_account_age_days and age_days < request.min_account_age_days:
                        continue
                    if request.max_account_age_days and age_days > request.max_account_age_days:
                        continue
            
            filtered_results.append(user)
            
            if len(filtered_results) >= request.limit:
                break
        
        execution_time = (time.time() - start_time) * 1000
        
        return QueryResponse(
            query_type="users",
            parameters=request.dict(),
            results=filtered_results,
            count=len(filtered_results),
            execution_time_ms=execution_time,
            reddit_api_calls=reddit_calls,
            filters_applied=filters_applied
        )
        
    except Exception as e:
        logger.error(f"User query failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# GET endpoints for simple queries
@router.get("/posts/simple", response_model=QueryResponse)
async def simple_post_query(
    subreddits: str = FastAPIQuery(..., description="Comma-separated subreddit names"),
    keywords: Optional[str] = FastAPIQuery(None, description="Comma-separated keywords"),
    min_score: Optional[int] = FastAPIQuery(None, description="Minimum score"),
    limit: int = FastAPIQuery(50, description="Maximum results"),
    current_user: User = Depends(require_api_call_limit)
):
    """Simple post query via GET parameters"""
    request = PostQueryRequest(
        subreddits=subreddits.split(','),
        keywords=keywords.split(',') if keywords else None,
        min_score=min_score,
        limit=limit
    )
    return await query_posts(request)

@router.get("/examples")
async def query_examples(
    current_user: User = Depends(require_api_call_limit)
):
    """Get example queries for the Query API"""
    return {
        "description": "Trendit Query API - Flexible one-off Reddit queries",
        "examples": {
            "complex_post_query": {
                "method": "POST",
                "endpoint": "/api/query/posts",
                "description": "Find high-scoring posts about Python in programming subreddits",
                "body": {
                    "subreddits": ["python", "programming", "learnpython"],
                    "keywords": ["async", "fastapi", "performance"],
                    "min_score": 100,
                    "min_upvote_ratio": 0.8,
                    "exclude_keywords": ["beginner", "help"],
                    "sort_type": "top",
                    "time_filter": "week",
                    "limit": 20
                }
            },
            "comment_analysis": {
                "method": "POST", 
                "endpoint": "/api/query/comments",
                "description": "Analyze high-quality comments in specific posts",
                "body": {
                    "post_ids": ["abc123", "def456"],
                    "min_score": 10,
                    "max_depth": 2,
                    "exclude_deleted": True,
                    "limit": 50
                }
            },
            "user_research": {
                "method": "POST",
                "endpoint": "/api/query/users", 
                "description": "Find experienced users in technical subreddits",
                "body": {
                    "subreddits": ["python", "MachineLearning"],
                    "min_total_karma": 1000,
                    "min_account_age_days": 365,
                    "limit": 25
                }
            },
            "simple_get_query": {
                "method": "GET",
                "endpoint": "/api/query/posts/simple?subreddits=python,programming&keywords=fastapi&min_score=50&limit=10",
                "description": "Simple GET-based post query"
            }
        }
    }
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, asc, func
from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field
import logging

from models.database import get_db
from models.models import CollectionJob, RedditPost, RedditComment, RedditUser, Analytics, JobStatus, User
from services.analytics import AnalyticsService
from api.auth import require_api_call_limit, require_dashboard_api_limit, require_feature

router = APIRouter(prefix="/api/data", tags=["data"])
logger = logging.getLogger(__name__)

# Request/Response Models
class PostQueryRequest(BaseModel):
    """Request model for querying stored posts"""
    
    # Job filtering
    job_ids: Optional[List[str]] = Field(
        default=None,
        example=["job_abc123", "job_def456"],
        description="Specific collection job IDs to query data from"
    )
    job_status: Optional[JobStatus] = Field(
        default=None,
        example=JobStatus.COMPLETED,
        description="Filter by job status (PENDING, RUNNING, COMPLETED, FAILED)"
    )

    # Content filtering
    subreddits: Optional[List[str]] = Field(
        default=None,
        example=["python", "MachineLearning", "datascience"],
        description="Filter posts from specific subreddits"
    )
    keywords: Optional[List[str]] = Field(
        default=None,
        example=["machine learning", "tensorflow", "neural networks"],
        description="Search for posts containing these keywords in title and content"
    )
    exclude_keywords: Optional[List[str]] = Field(
        default=None,
        example=["spam", "advertisement"],
        description="Exclude posts containing these keywords"
    )
    
    # Score and engagement filters
    min_score: Optional[int] = Field(
        default=None,
        example=50,
        description="Minimum post upvote score"
    )
    max_score: Optional[int] = Field(
        default=None,
        example=1000,
        description="Maximum post upvote score"
    )
    min_upvote_ratio: Optional[float] = Field(
        default=None,
        example=0.8,
        description="Minimum upvote ratio (0.0-1.0)"
    )
    min_comments: Optional[int] = Field(
        default=None,
        example=10,
        description="Minimum number of comments on the post"
    )
    max_comments: Optional[int] = Field(
        default=None,
        example=500,
        description="Maximum number of comments on the post"
    )
    
    # Content type filters
    exclude_nsfw: Optional[bool] = Field(default=None, description="Exclude NSFW content")
    exclude_stickied: Optional[bool] = Field(default=None, description="Exclude stickied posts")
    post_types: Optional[List[str]] = Field(default=None, description="Filter by post types (image, video, link, text)")
    
    # Date filters
    created_after: Optional[datetime] = Field(default=None, description="Posts created after this date")
    created_before: Optional[datetime] = Field(default=None, description="Posts created before this date")
    collected_after: Optional[datetime] = Field(default=None, description="Posts collected after this date")
    collected_before: Optional[datetime] = Field(default=None, description="Posts collected before this date")
    
    # Author filters
    authors: Optional[List[str]] = Field(default=None, description="Filter by specific authors")
    exclude_authors: Optional[List[str]] = Field(default=None, description="Exclude specific authors")
    exclude_deleted: Optional[bool] = Field(default=True, description="Exclude deleted/removed posts")
    
    # Sorting and pagination
    sort_by: str = Field(default="created_utc", description="Sort field")
    sort_order: str = Field(default="desc", description="Sort order (asc/desc)")
    limit: int = Field(default=20, ge=1, le=1000, description="Number of results")
    offset: int = Field(default=0, ge=0, description="Results offset")

class CommentQueryRequest(BaseModel):
    """Request model for querying stored comments"""
    
    # Job and post filtering
    job_ids: Optional[List[str]] = Field(default=None, description="Specific collection job IDs")
    post_ids: Optional[List[int]] = Field(default=None, description="Specific post IDs")
    
    # Content filtering
    subreddits: Optional[List[str]] = Field(default=None, description="Filter by subreddits")
    keywords: Optional[List[str]] = Field(default=None, description="Search in comment body")
    exclude_keywords: Optional[List[str]] = Field(default=None, description="Exclude comments with these keywords")
    
    # Comment-specific filters
    min_score: Optional[int] = Field(default=None, description="Minimum comment score")
    max_score: Optional[int] = Field(default=None, description="Maximum comment score")
    min_depth: Optional[int] = Field(default=None, description="Minimum thread depth")
    max_depth: Optional[int] = Field(default=None, description="Maximum thread depth")
    top_level_only: Optional[bool] = Field(default=False, description="Only top-level comments")
    
    # Author filters
    authors: Optional[List[str]] = Field(default=None, description="Filter by specific authors")
    exclude_authors: Optional[List[str]] = Field(default=None, description="Exclude specific authors")
    exclude_deleted: Optional[bool] = Field(default=True, description="Exclude deleted comments")
    is_submitter: Optional[bool] = Field(default=None, description="Filter by post author comments")
    
    # Date filters
    created_after: Optional[datetime] = Field(default=None, description="Comments created after this date")
    created_before: Optional[datetime] = Field(default=None, description="Comments created before this date")
    
    # Sorting and pagination
    sort_by: str = Field(default="created_utc", description="Sort field")
    sort_order: str = Field(default="desc", description="Sort order (asc/desc)")
    limit: int = Field(default=50, ge=1, le=1000, description="Number of results")
    offset: int = Field(default=0, ge=0, description="Results offset")

class DataQueryResponse(BaseModel):
    """Response model for data queries"""
    
    query_type: str
    description: str
    results: List[Dict[str, Any]]
    total_count: int
    returned_count: int
    execution_time_ms: float

class PostAnalyticsResponse(BaseModel):
    """Response model for post analytics"""
    
    total_posts: int
    unique_subreddits: int
    unique_authors: int
    date_range: Dict[str, Optional[str]]
    score_stats: Dict[str, float]
    engagement_stats: Dict[str, float]
    content_distribution: Dict[str, int]
    top_posts: List[Dict[str, Any]]
    subreddit_breakdown: Dict[str, int]

# Data Query Endpoints

@router.post("/posts", response_model=DataQueryResponse)
async def query_posts(
    query: PostQueryRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_api_call_limit)
):
    """
    Query stored Reddit posts with advanced filtering
    
    Search and filter posts collected by previous collection jobs
    with comprehensive filtering options for content, engagement,
    dates, authors, and more.
    """
    import time
    start_time = time.time()
    
    try:
        # Build base query
        query_obj = db.query(RedditPost)
        
        # Join with CollectionJob for job-based filtering
        if query.job_ids or query.job_status:
            query_obj = query_obj.join(CollectionJob)
            
            if query.job_ids:
                query_obj = query_obj.filter(CollectionJob.job_id.in_(query.job_ids))
            
            if query.job_status:
                query_obj = query_obj.filter(CollectionJob.status == query.job_status)
        
        # Subreddit filtering
        if query.subreddits:
            query_obj = query_obj.filter(RedditPost.subreddit.in_(query.subreddits))
        
        # Keyword filtering
        if query.keywords:
            keyword_conditions = []
            for keyword in query.keywords:
                keyword_conditions.append(
                    or_(
                        RedditPost.title.ilike(f"%{keyword}%"),
                        RedditPost.selftext.ilike(f"%{keyword}%")
                    )
                )
            query_obj = query_obj.filter(or_(*keyword_conditions))
        
        if query.exclude_keywords:
            for keyword in query.exclude_keywords:
                query_obj = query_obj.filter(
                    and_(
                        ~RedditPost.title.ilike(f"%{keyword}%"),
                        ~RedditPost.selftext.ilike(f"%{keyword}%")
                    )
                )
        
        # Score filtering
        if query.min_score is not None:
            query_obj = query_obj.filter(RedditPost.score >= query.min_score)
        if query.max_score is not None:
            query_obj = query_obj.filter(RedditPost.score <= query.max_score)
        
        # Engagement filtering
        if query.min_upvote_ratio is not None:
            query_obj = query_obj.filter(RedditPost.upvote_ratio >= query.min_upvote_ratio)
        if query.min_comments is not None:
            query_obj = query_obj.filter(RedditPost.num_comments >= query.min_comments)
        if query.max_comments is not None:
            query_obj = query_obj.filter(RedditPost.num_comments <= query.max_comments)
        
        # Content type filtering
        if query.exclude_nsfw:
            query_obj = query_obj.filter(RedditPost.is_nsfw == False)
        if query.exclude_stickied:
            query_obj = query_obj.filter(RedditPost.is_stickied == False)
        if query.post_types:
            query_obj = query_obj.filter(RedditPost.post_hint.in_(query.post_types))
        
        # Date filtering
        if query.created_after:
            query_obj = query_obj.filter(RedditPost.created_utc >= query.created_after)
        if query.created_before:
            query_obj = query_obj.filter(RedditPost.created_utc <= query.created_before)
        if query.collected_after:
            query_obj = query_obj.filter(RedditPost.collected_at >= query.collected_after)
        if query.collected_before:
            query_obj = query_obj.filter(RedditPost.collected_at <= query.collected_before)
        
        # Author filtering
        if query.authors:
            query_obj = query_obj.filter(RedditPost.author.in_(query.authors))
        if query.exclude_authors:
            query_obj = query_obj.filter(~RedditPost.author.in_(query.exclude_authors))
        if query.exclude_deleted:
            query_obj = query_obj.filter(RedditPost.author.isnot(None))
        
        # Get total count before pagination
        total_count = query_obj.count()
        
        # Sorting
        sort_field = getattr(RedditPost, query.sort_by, RedditPost.created_utc)
        if query.sort_order.lower() == "asc":
            query_obj = query_obj.order_by(asc(sort_field))
        else:
            query_obj = query_obj.order_by(desc(sort_field))
        
        # Pagination
        posts = query_obj.offset(query.offset).limit(query.limit).all()
        
        # Convert to response format
        results = []
        for post in posts:
            post_data = {
                "id": post.id,
                "reddit_id": post.reddit_id,
                "title": post.title,
                "selftext": post.selftext,
                "url": post.url,
                "permalink": post.permalink,
                "subreddit": post.subreddit,
                "author": post.author,
                "score": post.score,
                "upvote_ratio": post.upvote_ratio,
                "num_comments": post.num_comments,
                "awards_received": post.awards_received,
                "is_nsfw": post.is_nsfw,
                "is_spoiler": post.is_spoiler,
                "is_stickied": post.is_stickied,
                "post_hint": post.post_hint,
                "created_utc": post.created_utc.isoformat() if post.created_utc else None,
                "collected_at": post.collected_at.isoformat() if post.collected_at else None,
                "sentiment_score": post.sentiment_score,
                "readability_score": post.readability_score,
                "collection_job_id": post.collection_job_id
            }
            results.append(post_data)
        
        execution_time = (time.time() - start_time) * 1000
        
        return DataQueryResponse(
            query_type="posts",
            description=f"Query returned {len(results)} posts from {total_count} total matches",
            results=results,
            total_count=total_count,
            returned_count=len(results),
            execution_time_ms=round(execution_time, 2)
        )
        
    except Exception as e:
        logger.error(f"Post query failed: {e}")
        raise HTTPException(status_code=500, detail=f"Post query failed: {str(e)}")

@router.post("/comments", response_model=DataQueryResponse)
async def query_comments(
    query: CommentQueryRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_api_call_limit)
):
    """
    Query stored Reddit comments with advanced filtering
    
    Search and filter comments collected by previous collection jobs
    with options for thread depth, scores, authors, and content filtering.
    """
    import time
    start_time = time.time()
    
    try:
        # Build base query
        query_obj = db.query(RedditComment)
        
        # Join with posts and jobs for filtering
        query_obj = query_obj.join(RedditPost)
        
        if query.job_ids:
            query_obj = query_obj.join(CollectionJob)
            query_obj = query_obj.filter(CollectionJob.job_id.in_(query.job_ids))
        
        # Post filtering
        if query.post_ids:
            query_obj = query_obj.filter(RedditComment.post_id.in_(query.post_ids))
        
        if query.subreddits:
            query_obj = query_obj.filter(RedditPost.subreddit.in_(query.subreddits))
        
        # Content filtering
        if query.keywords:
            keyword_conditions = []
            for keyword in query.keywords:
                keyword_conditions.append(RedditComment.body.ilike(f"%{keyword}%"))
            query_obj = query_obj.filter(or_(*keyword_conditions))
        
        if query.exclude_keywords:
            for keyword in query.exclude_keywords:
                query_obj = query_obj.filter(~RedditComment.body.ilike(f"%{keyword}%"))
        
        # Score filtering
        if query.min_score is not None:
            query_obj = query_obj.filter(RedditComment.score >= query.min_score)
        if query.max_score is not None:
            query_obj = query_obj.filter(RedditComment.score <= query.max_score)
        
        # Depth filtering
        if query.min_depth is not None:
            query_obj = query_obj.filter(RedditComment.depth >= query.min_depth)
        if query.max_depth is not None:
            query_obj = query_obj.filter(RedditComment.depth <= query.max_depth)
        if query.top_level_only:
            query_obj = query_obj.filter(RedditComment.depth == 0)
        
        # Author filtering
        if query.authors:
            query_obj = query_obj.filter(RedditComment.author.in_(query.authors))
        if query.exclude_authors:
            query_obj = query_obj.filter(~RedditComment.author.in_(query.exclude_authors))
        if query.exclude_deleted:
            query_obj = query_obj.filter(RedditComment.author.isnot(None))
        if query.is_submitter is not None:
            query_obj = query_obj.filter(RedditComment.is_submitter == query.is_submitter)
        
        # Date filtering
        if query.created_after:
            query_obj = query_obj.filter(RedditComment.created_utc >= query.created_after)
        if query.created_before:
            query_obj = query_obj.filter(RedditComment.created_utc <= query.created_before)
        
        # Get total count
        total_count = query_obj.count()
        
        # Sorting
        sort_field = getattr(RedditComment, query.sort_by, RedditComment.created_utc)
        if query.sort_order.lower() == "asc":
            query_obj = query_obj.order_by(asc(sort_field))
        else:
            query_obj = query_obj.order_by(desc(sort_field))
        
        # Pagination
        comments = query_obj.offset(query.offset).limit(query.limit).all()
        
        # Convert to response format
        results = []
        for comment in comments:
            comment_data = {
                "id": comment.id,
                "reddit_id": comment.reddit_id,
                "body": comment.body,
                "parent_id": comment.parent_id,
                "post_id": comment.post_id,
                "author": comment.author,
                "author_id": comment.author_id,
                "depth": comment.depth,
                "score": comment.score,
                "awards_received": comment.awards_received,
                "is_submitter": comment.is_submitter,
                "is_stickied": comment.is_stickied,
                "created_utc": comment.created_utc.isoformat() if comment.created_utc else None,
                "collected_at": comment.collected_at.isoformat() if comment.collected_at else None,
                "sentiment_score": comment.sentiment_score,
                # Include post context
                "post_title": comment.post.title,
                "post_subreddit": comment.post.subreddit
            }
            results.append(comment_data)
        
        execution_time = (time.time() - start_time) * 1000
        
        return DataQueryResponse(
            query_type="comments",
            description=f"Query returned {len(results)} comments from {total_count} total matches",
            results=results,
            total_count=total_count,
            returned_count=len(results),
            execution_time_ms=round(execution_time, 2)
        )
        
    except Exception as e:
        logger.error(f"Comment query failed: {e}")
        raise HTTPException(status_code=500, detail=f"Comment query failed: {str(e)}")

@router.get("/analytics/{job_id}", response_model=PostAnalyticsResponse)
async def get_job_analytics(
    job_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_api_call_limit)
):
    """
    Get analytics for a specific collection job
    
    Provides comprehensive analytics including engagement metrics,
    content distribution, top posts, and subreddit breakdowns.
    """
    try:
        # Verify job exists
        job = db.query(CollectionJob).filter(CollectionJob.job_id == job_id).first()
        if not job:
            raise HTTPException(status_code=404, detail="Collection job not found")
        
        # Get all posts for this job
        posts = db.query(RedditPost).filter(RedditPost.collection_job_id == job.id).all()
        
        if not posts:
            return PostAnalyticsResponse(
                total_posts=0,
                unique_subreddits=0,
                unique_authors=0,
                date_range={"earliest": None, "latest": None},
                score_stats={},
                engagement_stats={},
                content_distribution={},
                top_posts=[],
                subreddit_breakdown={}
            )
        
        # Calculate analytics
        total_posts = len(posts)
        unique_subreddits = len(set(post.subreddit for post in posts if post.subreddit))
        unique_authors = len(set(post.author for post in posts if post.author))
        
        # Date range
        dates = [post.created_utc for post in posts if post.created_utc]
        date_range = {
            "earliest": min(dates).isoformat() if dates else None,
            "latest": max(dates).isoformat() if dates else None
        }
        
        # Score statistics
        scores = [post.score for post in posts if post.score is not None]
        score_stats = {
            "mean": sum(scores) / len(scores) if scores else 0,
            "median": sorted(scores)[len(scores)//2] if scores else 0,
            "min": min(scores) if scores else 0,
            "max": max(scores) if scores else 0
        }
        
        # Engagement statistics
        ratios = [post.upvote_ratio for post in posts if post.upvote_ratio is not None]
        comments = [post.num_comments for post in posts if post.num_comments is not None]
        engagement_stats = {
            "avg_upvote_ratio": sum(ratios) / len(ratios) if ratios else 0,
            "avg_comments": sum(comments) / len(comments) if comments else 0,
            "total_comments": sum(comments) if comments else 0
        }
        
        # Content distribution
        content_types = {}
        nsfw_count = sum(1 for post in posts if post.is_nsfw)
        stickied_count = sum(1 for post in posts if post.is_stickied)
        
        content_distribution = {
            "total": total_posts,
            "nsfw": nsfw_count,
            "stickied": stickied_count,
            "regular": total_posts - nsfw_count - stickied_count
        }
        
        # Top posts by score
        top_posts = sorted(posts, key=lambda p: p.score or 0, reverse=True)[:5]
        top_posts_data = []
        for post in top_posts:
            top_posts_data.append({
                "title": post.title,
                "score": post.score,
                "subreddit": post.subreddit,
                "author": post.author,
                "num_comments": post.num_comments,
                "permalink": post.permalink
            })
        
        # Subreddit breakdown
        subreddit_counts = {}
        for post in posts:
            if post.subreddit:
                subreddit_counts[post.subreddit] = subreddit_counts.get(post.subreddit, 0) + 1
        
        return PostAnalyticsResponse(
            total_posts=total_posts,
            unique_subreddits=unique_subreddits,
            unique_authors=unique_authors,
            date_range=date_range,
            score_stats=score_stats,
            engagement_stats=engagement_stats,
            content_distribution=content_distribution,
            top_posts=top_posts_data,
            subreddit_breakdown=subreddit_counts
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Analytics query failed: {e}")
        raise HTTPException(status_code=500, detail=f"Analytics query failed: {str(e)}")

@router.get("/summary", response_model=Dict[str, Any])
async def get_data_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_dashboard_api_limit)
):
    """
    Get overall summary of stored data
    
    Provides high-level statistics about all collected data
    including job counts, data volumes, and date ranges.
    """
    try:
        # Job statistics
        total_jobs = db.query(CollectionJob).count()
        completed_jobs = db.query(CollectionJob).filter(CollectionJob.status == JobStatus.COMPLETED).count()
        
        # Data volume statistics
        total_posts = db.query(RedditPost).count()
        total_comments = db.query(RedditComment).count()
        
        # Date ranges
        earliest_post = db.query(func.min(RedditPost.created_utc)).scalar()
        latest_post = db.query(func.max(RedditPost.created_utc)).scalar()
        
        # Subreddit and author counts
        unique_subreddits = db.query(RedditPost.subreddit).distinct().count()
        unique_authors = db.query(RedditPost.author).filter(RedditPost.author.isnot(None)).distinct().count()
        
        # Top subreddits by post count
        top_subreddits = db.query(
            RedditPost.subreddit,
            func.count(RedditPost.id).label('count')
        ).group_by(RedditPost.subreddit).order_by(desc('count')).limit(10).all()
        
        return {
            "data_summary": {
                "total_collection_jobs": total_jobs,
                "completed_jobs": completed_jobs,
                "total_posts": total_posts,
                "total_comments": total_comments,
                "unique_subreddits": unique_subreddits,
                "unique_authors": unique_authors
            },
            "date_range": {
                "earliest_post": earliest_post.isoformat() if earliest_post else None,
                "latest_post": latest_post.isoformat() if latest_post else None
            },
            "top_subreddits": [
                {"subreddit": sub, "post_count": count} 
                for sub, count in top_subreddits
            ]
        }
        
    except Exception as e:
        logger.error(f"Summary query failed: {e}")
        raise HTTPException(status_code=500, detail=f"Summary query failed: {str(e)}")

# Simple GET endpoints for basic queries
@router.get("/posts/recent")
async def get_recent_posts(
    limit: int = Query(20, ge=1, le=100),
    subreddit: Optional[str] = Query(None),
    min_score: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_api_call_limit)
):
    """Get recently collected posts with optional filtering"""
    
    query_obj = db.query(RedditPost)
    
    if subreddit:
        query_obj = query_obj.filter(RedditPost.subreddit == subreddit)
    if min_score is not None:
        query_obj = query_obj.filter(RedditPost.score >= min_score)
    
    posts = query_obj.order_by(desc(RedditPost.collected_at)).limit(limit).all()
    
    return {
        "posts": [
            {
                "title": post.title,
                "subreddit": post.subreddit,
                "score": post.score,
                "author": post.author,
                "created_utc": post.created_utc.isoformat() if post.created_utc else None,
                "permalink": post.permalink
            }
            for post in posts
        ],
        "count": len(posts)
    }

@router.get("/posts/top")
async def get_top_posts(
    limit: int = Query(20, ge=1, le=100),
    subreddit: Optional[str] = Query(None),
    timeframe_hours: Optional[int] = Query(None, description="Last N hours"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_api_call_limit)
):
    """Get top scoring posts with optional filtering"""
    
    query_obj = db.query(RedditPost)
    
    if subreddit:
        query_obj = query_obj.filter(RedditPost.subreddit == subreddit)
    
    if timeframe_hours:
        from datetime import datetime, timedelta
        cutoff_time = datetime.utcnow() - timedelta(hours=timeframe_hours)
        query_obj = query_obj.filter(RedditPost.collected_at >= cutoff_time)
    
    posts = query_obj.order_by(desc(RedditPost.score)).limit(limit).all()
    
    return {
        "posts": [
            {
                "title": post.title,
                "subreddit": post.subreddit,
                "score": post.score,
                "author": post.author,
                "num_comments": post.num_comments,
                "upvote_ratio": post.upvote_ratio,
                "permalink": post.permalink
            }
            for post in posts
        ],
        "count": len(posts)
    }
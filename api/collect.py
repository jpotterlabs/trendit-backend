from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from pydantic import BaseModel, Field
import uuid
import logging

from models.database import get_db
from models.models import CollectionJob, JobStatus, SortType, TimeFilter, RedditPost, RedditComment, User
from services.data_collector import DataCollector
from services.sentiment_analyzer import sentiment_analyzer
from api.auth import require_api_call_limit, require_jobs_api_limit, require_feature
from services.date_filter_fix import ImprovedDateFiltering

router = APIRouter(prefix="/api/collect", tags=["collection"])
logger = logging.getLogger(__name__)

# Request/Response Models
class CollectionJobRequest(BaseModel):
    """Request model for creating a new collection job"""

    # Collection targets
    subreddits: List[str] = Field(
        ...,
        example=["python", "MachineLearning", "datascience"],
        description="List of subreddit names (without r/ prefix)"
    )
    sort_types: List[SortType] = Field(
        default=[SortType.HOT],
        example=[SortType.HOT, SortType.TOP],
        description="Sort types to use for collecting posts"
    )
    time_filters: List[TimeFilter] = Field(
        default=[TimeFilter.WEEK],
        example=[TimeFilter.WEEK, TimeFilter.MONTH],
        description="Time filters to apply for post collection"
    )

    # Limits
    post_limit: int = Field(
        default=100,
        ge=1,
        le=10000,
        example=250,
        description="Maximum posts to collect per subreddit"
    )
    comment_limit: int = Field(
        default=50,
        ge=0,
        le=1000,
        example=25,
        description="Maximum comments per post to collect"
    )
    max_comment_depth: int = Field(
        default=3,
        ge=0,
        le=10,
        example=2,
        description="Maximum depth of comment threads to traverse"
    )

    # Filters
    keywords: Optional[List[str]] = Field(
        default=None,
        example=["artificial intelligence", "neural networks", "tensorflow"],
        description="Keywords to filter posts by (searches title and content)"
    )
    min_score: int = Field(
        default=0,
        example=10,
        description="Minimum upvote score for posts"
    )
    min_upvote_ratio: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        example=0.8,
        description="Minimum upvote ratio (0.0-1.0) for posts"
    )
    date_from: Optional[datetime] = Field(
        default=None,
        example="2024-01-01T00:00:00Z",
        description="Start date filter (ISO format)"
    )
    date_to: Optional[datetime] = Field(
        default=None,
        example="2024-12-31T23:59:59Z",
        description="End date filter (ISO format)"
    )
    exclude_nsfw: bool = Field(
        default=True,
        example=True,
        description="Whether to exclude NSFW (Not Safe For Work) content"
    )
    anonymize_users: bool = Field(
        default=True,
        example=True,
        description="Whether to anonymize usernames in collected data"
    )

class CollectionJobResponse(BaseModel):
    """Response model for collection job information"""
    
    id: int
    job_id: str
    status: JobStatus
    progress: int
    total_expected: int
    collected_posts: int
    collected_comments: int
    error_message: Optional[str]
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    
    # Collection parameters (subset for response)
    subreddits: List[str]
    post_limit: int
    
    class Config:
        from_attributes = True

class CollectionJobStatusResponse(BaseModel):
    """Simplified response for job status checks"""
    
    job_id: str
    status: JobStatus
    progress: int
    collected_posts: int
    collected_comments: int
    error_message: Optional[str]
    
    class Config:
        from_attributes = True

class CollectionJobListResponse(BaseModel):
    """Response for listing collection jobs"""
    
    jobs: List[CollectionJobResponse]
    total: int
    page: int
    per_page: int

# Collection Job Management Endpoints

@router.post("/jobs", response_model=CollectionJobResponse)
@require_feature('collect_api')
async def create_collection_job(
    job_request: CollectionJobRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_api_call_limit)
):
    """
    Create a new persistent collection job
    
    This endpoint creates a collection job that will run in the background
    and store all collected data in the database for later analysis.
    """
    try:
        # Generate unique job ID
        job_id = str(uuid.uuid4())
        
        # Create collection job record
        collection_job = CollectionJob(
            job_id=job_id,
            user_id=current_user.id,
            subreddits=job_request.subreddits,
            sort_types=[st.value for st in job_request.sort_types],
            time_filters=[tf.value for tf in job_request.time_filters],
            post_limit=job_request.post_limit,
            comment_limit=job_request.comment_limit,
            max_comment_depth=job_request.max_comment_depth,
            keywords=job_request.keywords,
            min_score=job_request.min_score,
            min_upvote_ratio=job_request.min_upvote_ratio,
            date_from=job_request.date_from,
            date_to=job_request.date_to,
            exclude_nsfw=job_request.exclude_nsfw,
            anonymize_users=job_request.anonymize_users,
            status=JobStatus.PENDING
        )
        
        db.add(collection_job)
        db.commit()
        db.refresh(collection_job)
        
        # Start background collection
        background_tasks.add_task(
            run_collection_job,
            collection_job.id,
            job_request.dict()
        )
        
        logger.info(f"Created collection job {job_id} with {len(job_request.subreddits)} subreddits")
        
        return CollectionJobResponse.from_orm(collection_job)
        
    except Exception as e:
        logger.error(f"Failed to create collection job: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create collection job: {str(e)}")

@router.get("/jobs/{job_id}", response_model=CollectionJobResponse)
@require_feature('collect_api')
async def get_collection_job(
    job_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_api_call_limit)
):
    """
    Get detailed information about a specific collection job
    """
    job = db.query(CollectionJob).filter(CollectionJob.job_id == job_id).first()
    
    if not job:
        raise HTTPException(status_code=404, detail="Collection job not found")
    
    return CollectionJobResponse.from_orm(job)

@router.get("/jobs/{job_id}/status", response_model=CollectionJobStatusResponse)
@require_feature('collect_api')
async def get_collection_job_status(
    job_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_api_call_limit)
):
    """
    Get quick status update for a collection job
    """
    job = db.query(CollectionJob).filter(CollectionJob.job_id == job_id).first()
    
    if not job:
        raise HTTPException(status_code=404, detail="Collection job not found")
    
    return CollectionJobStatusResponse(
        job_id=job.job_id,
        status=job.status,
        progress=job.progress,
        collected_posts=job.collected_posts,
        collected_comments=job.collected_comments,
        error_message=job.error_message
    )

@router.get("/jobs", response_model=CollectionJobListResponse)
@require_feature('collect_api')
async def list_collection_jobs(
    status: Optional[JobStatus] = None,
    page: int = 1,
    per_page: int = 20,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_jobs_api_limit)
):
    """
    List collection jobs with optional filtering
    """
    query = db.query(CollectionJob)
    
    if status:
        query = query.filter(CollectionJob.status == status)
    
    # Get total count
    total = query.count()
    
    # Apply pagination
    offset = (page - 1) * per_page
    jobs = query.order_by(CollectionJob.created_at.desc()).offset(offset).limit(per_page).all()
    
    return CollectionJobListResponse(
        jobs=[CollectionJobResponse.from_orm(job) for job in jobs],
        total=total,
        page=page,
        per_page=per_page
    )

@router.post("/jobs/{job_id}/cancel")
@require_feature('collect_api')
async def cancel_collection_job(
    job_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_api_call_limit)
):
    """
    Cancel a running collection job
    """
    job = db.query(CollectionJob).filter(CollectionJob.job_id == job_id).first()
    
    if not job:
        raise HTTPException(status_code=404, detail="Collection job not found")
    
    if job.status not in [JobStatus.PENDING, JobStatus.RUNNING]:
        raise HTTPException(
            status_code=400, 
            detail=f"Cannot cancel job with status: {job.status.value}"
        )
    
    job.status = JobStatus.CANCELLED
    job.completed_at = datetime.utcnow()
    db.commit()
    
    logger.info(f"Cancelled collection job {job_id}")
    
    return {"message": f"Collection job {job_id} cancelled successfully"}

@router.delete("/jobs/{job_id}")
@require_feature('collect_api')
async def delete_collection_job(
    job_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_api_call_limit)
):
    """
    Delete a collection job and all associated data
    
    WARNING: This will permanently delete all collected posts, comments, and analytics
    """
    job = db.query(CollectionJob).filter(CollectionJob.job_id == job_id).first()
    
    if not job:
        raise HTTPException(status_code=404, detail="Collection job not found")
    
    if job.status == JobStatus.RUNNING:
        raise HTTPException(
            status_code=400, 
            detail="Cannot delete a running job. Cancel it first."
        )
    
    # Delete the job (cascade will handle related data)
    db.delete(job)
    db.commit()
    
    logger.info(f"Deleted collection job {job_id}")
    
    return {"message": f"Collection job {job_id} deleted successfully"}

# Background Collection Function

async def run_collection_job(job_id: int, job_params: Dict[str, Any]):
    """
    Background task to run a collection job with real data collection
    """
    from models.database import SessionLocal
    
    db = SessionLocal()
    collector = DataCollector()
    
    try:
        # Get the job record
        job = db.query(CollectionJob).filter(CollectionJob.id == job_id).first()
        if not job:
            logger.error(f"Collection job {job_id} not found")
            return
        
        # Update status to running
        job.status = JobStatus.RUNNING
        job.started_at = datetime.utcnow()
        db.commit()
        
        logger.info(f"Starting collection job {job.job_id} for subreddits: {job.subreddits}")
        
        # Estimate total expected items
        estimated_posts = min(job.post_limit, len(job.subreddits) * 25)
        job.total_expected = estimated_posts
        db.commit()
        
        # Run collection for each subreddit and sort type combination
        total_collected_posts = 0
        total_collected_comments = 0
        all_collected_data = []
        
        for subreddit in job.subreddits:
            for sort_type in job.sort_types:
                for time_filter in job.time_filters:
                    if job.status == JobStatus.CANCELLED:
                        logger.info(f"Collection job {job.job_id} was cancelled")
                        return
                    
                    try:
                        logger.info(f"Collecting from r/{subreddit} with {sort_type} sort and {time_filter} filter")
                        
                        # Use DataCollector to get posts based on job parameters
                        if job.keywords:
                            # If keywords are specified, use search
                            # Use improved date range logic
                            if job.date_from and job.date_to:
                                # Use job-specified dates
                                date_from = job.date_from
                                date_to = job.date_to
                            else:
                                # Use improved date range with buffer for better collection
                                date_from, date_to = ImprovedDateFiltering.create_date_range_with_buffer(
                                    days=7, buffer_hours=4
                                )
                            
                            logger.info(f"Collection date range: {date_from} to {date_to}")
                            
                            posts_data = await collector.search_subreddit_posts_by_keyword_and_date(
                                subreddit=subreddit,
                                keywords=job.keywords,
                                date_from=date_from,
                                date_to=date_to,
                                limit=min(job.post_limit // len(job.subreddits), 100),
                                sort_by="score"
                            )
                        else:
                            # Use trending/popular posts collection
                            posts_data = await collector.get_trending_posts_multiple_subreddits(
                                subreddits=[subreddit],
                                timeframe=time_filter,
                                limit_per_subreddit=min(job.post_limit // len(job.subreddits), 25),
                                final_limit=min(job.post_limit, 100)
                            )
                        
                        # Add debugging code for monitoring collection results
                        if posts_data:
                            logger.info(f"Collection debug - posts found: {len(posts_data)}")
                            # Show date range of collected posts for debugging
                            try:
                                post_dates = []
                                for post in posts_data:
                                    created_utc = post.get('created_utc')
                                    if created_utc and isinstance(created_utc, datetime):
                                        post_dates.append(created_utc)
                                
                                if post_dates:
                                    earliest_post = min(post_dates)
                                    latest_post = max(post_dates)
                                    logger.info(f"Collected posts date range: {earliest_post} to {latest_post}")
                            except Exception as e:
                                logger.warning(f"Error analyzing post dates: {e}")
                        else:
                            logger.warning("No posts collected - this might indicate a date filtering issue")
                        
                        # Store collected data with sentiment analysis
                        posts_for_sentiment = []
                        reddit_posts = []
                        
                        # Prepare posts and sentiment analysis
                        for post_data in posts_data:
                            try:
                                # Create RedditPost record
                                created_utc = post_data.get('created_utc')
                                if isinstance(created_utc, (int, float)):
                                    created_utc = datetime.fromtimestamp(created_utc)
                                elif not isinstance(created_utc, datetime):
                                    created_utc = datetime.utcnow()
                                
                                reddit_post = RedditPost(
                                    collection_job_id=job.id,
                                    reddit_id=post_data.get('reddit_id'),
                                    title=post_data.get('title'),
                                    selftext=post_data.get('selftext'),
                                    url=post_data.get('url'),
                                    permalink=post_data.get('permalink'),
                                    subreddit=post_data.get('subreddit'),
                                    author=post_data.get('author') if not job.anonymize_users else None,
                                    score=post_data.get('score', 0),
                                    upvote_ratio=post_data.get('upvote_ratio', 0.0),
                                    num_comments=post_data.get('num_comments', 0),
                                    is_nsfw=post_data.get('over_18', False),
                                    created_utc=created_utc
                                )
                                
                                reddit_posts.append(reddit_post)
                                
                                # Prepare text for sentiment analysis
                                title = post_data.get('title', '')
                                selftext = post_data.get('selftext', '')
                                combined_text = f"{title}. {selftext}".strip()
                                posts_for_sentiment.append(combined_text)
                                
                            except Exception as e:
                                logger.error(f"Error preparing post {post_data.get('id')}: {e}")
                                continue
                        
                        # Run sentiment analysis for all posts in batch
                        sentiment_scores = []
                        if sentiment_analyzer.is_available() and posts_for_sentiment:
                            try:
                                async with sentiment_analyzer:
                                    logger.info(f"Analyzing sentiment for {len(posts_for_sentiment)} posts")
                                    sentiment_scores = await sentiment_analyzer.analyze_batch(posts_for_sentiment)
                                    logger.info(f"Completed sentiment analysis: {len([s for s in sentiment_scores if s is not None])} successful")
                            except Exception as e:
                                logger.warning(f"Sentiment analysis failed: {e}")
                                sentiment_scores = [None] * len(posts_for_sentiment)
                        else:
                            sentiment_scores = [None] * len(posts_for_sentiment)
                        
                        # Store posts with sentiment scores
                        for reddit_post, sentiment_score in zip(reddit_posts, sentiment_scores):
                            try:
                                # Check if post already exists
                                existing_post = db.query(RedditPost).filter(
                                    RedditPost.reddit_id == reddit_post.reddit_id
                                ).first()
                                
                                if existing_post:
                                    logger.info(f"Skipping duplicate post: {reddit_post.reddit_id}")
                                    continue
                                
                                reddit_post.sentiment_score = sentiment_score
                                db.add(reddit_post)
                                db.flush()  # Get the ID without committing
                                
                                total_collected_posts += 1
                                
                                # Collect comments if requested
                                if job.comment_limit > 0:
                                    try:
                                        comments_data = await collector.get_top_comments_by_criteria(
                                            post_id=reddit_post.reddit_id,
                                            limit=min(job.comment_limit, 50)
                                        )
                                        
                                        for comment_data in comments_data:
                                            try:
                                                # Check if comment already exists
                                                existing_comment = db.query(RedditComment).filter(
                                                    RedditComment.reddit_id == comment_data['reddit_id']
                                                ).first()
                                                
                                                if existing_comment:
                                                    continue
                                                
                                                reddit_comment = RedditComment(
                                                    reddit_id=comment_data['reddit_id'],
                                                    post_id=reddit_post.id,
                                                    parent_id=comment_data.get('parent_id'),
                                                    author=comment_data.get('author'),
                                                    body=comment_data['body'],
                                                    score=comment_data['score'],
                                                    depth=comment_data.get('depth', 0),
                                                    created_utc=comment_data['created_utc'],
                                                    collected_at=datetime.utcnow()
                                                )
                                                db.add(reddit_comment)
                                                total_collected_comments += 1
                                            except Exception as e:
                                                logger.error(f"Error storing comment: {e}")
                                                continue
                                    except Exception as e:
                                        logger.warning(f"Error collecting comments for post {reddit_post.reddit_id}: {e}")
                                        continue
                                
                            except Exception as e:
                                logger.error(f"Error storing post {reddit_post.reddit_id}: {e}")
                                db.rollback()  # Rollback the transaction on error
                                continue
                        
                        # Update progress
                        progress = min(100, int((total_collected_posts / max(estimated_posts, 1)) * 100))
                        job.progress = progress
                        job.collected_posts = total_collected_posts
                        job.collected_comments = total_collected_comments
                        db.commit()
                        
                        logger.info(f"Collected {len(posts_data)} posts from r/{subreddit}")
                        
                    except Exception as e:
                        logger.error(f"Error collecting from r/{subreddit} ({sort_type}, {time_filter}): {e}")
                        continue
        
        # Mark job as completed
        job.status = JobStatus.COMPLETED
        job.completed_at = datetime.utcnow()
        job.progress = 100
        db.commit()
        
        logger.info(f"Completed collection job {job.job_id}: {total_collected_posts} posts, {total_collected_comments} comments")
        
    except Exception as e:
        logger.error(f"Collection job {job_id} failed: {e}")
        
        # Mark job as failed
        job = db.query(CollectionJob).filter(CollectionJob.id == job_id).first()
        if job:
            job.status = JobStatus.FAILED
            job.error_message = str(e)
            job.completed_at = datetime.utcnow()
            db.commit()
    
    finally:
        db.close()
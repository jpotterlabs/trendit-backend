from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Response
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field
import logging
import json
import csv
import io
import pandas as pd
import uuid

from models.database import get_db
from models.models import CollectionJob, RedditPost, RedditComment, JobStatus, User
from api.data import PostQueryRequest, CommentQueryRequest
from api.auth import require_export_limit

router = APIRouter(prefix="/api/export", tags=["export"])
logger = logging.getLogger(__name__)

# Request/Response Models
class ExportRequest(BaseModel):
    """Request model for data export"""

    # Export target
    export_type: str = Field(
        ...,
        example="posts",
        description="What to export (posts, comments, job_data)"
    )
    format: str = Field(
        ...,
        example="csv",
        description="Export format (csv, json, jsonl, parquet)"
    )

    # Optional query filters (reuse Data API filters)
    job_ids: Optional[List[str]] = Field(
        default=None,
        example=["job_abc123", "job_def456"],
        description="Specific collection job IDs to export data from"
    )
    subreddits: Optional[List[str]] = Field(
        default=None,
        example=["python", "MachineLearning"],
        description="Filter exported data by specific subreddits"
    )
    keywords: Optional[List[str]] = Field(
        default=None,
        example=["machine learning", "AI", "tensorflow"],
        description="Search keywords to filter exported posts/comments"
    )
    min_score: Optional[int] = Field(
        default=None,
        example=50,
        description="Minimum upvote score for exported posts"
    )
    created_after: Optional[datetime] = Field(
        default=None,
        example="2024-01-01T00:00:00Z",
        description="Export only data created after this date"
    )
    created_before: Optional[datetime] = Field(
        default=None,
        example="2024-12-31T23:59:59Z",
        description="Export only data created before this date"
    )

    # Export options
    include_metadata: bool = Field(
        default=True,
        example=True,
        description="Include collection job metadata in export"
    )
    anonymize_authors: bool = Field(
        default=False,
        example=False,
        description="Remove author usernames from exported data for privacy"
    )
    limit: Optional[int] = Field(
        default=None,
        example=1000,
        description="Maximum number of records to export (null = no limit)"
    )

class ExportResponse(BaseModel):
    """Response model for export operations"""
    
    export_id: str
    status: str
    export_type: str
    format: str
    record_count: int
    file_size_bytes: Optional[int] = None
    download_url: Optional[str] = None
    created_at: datetime
    expires_at: Optional[datetime] = None

# Export Endpoints

@router.post("/posts/{format}")
async def export_posts(
    format: str,
    export_request: PostQueryRequest,
    response: Response,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_export_limit)
):
    """
    Export posts in specified format (csv, json, jsonl, parquet)
    
    Uses the same filtering options as the Data API posts query
    but returns the data in the requested export format.
    """
    try:
        if format.lower() not in ["csv", "json", "jsonl", "parquet"]:
            raise HTTPException(status_code=400, detail="Supported formats: csv, json, jsonl, parquet")
        
        # Use the same query logic as Data API
        from api.data import query_posts
        
        # Create a mock response object to get the data
        class MockResponse:
            pass
        
        # Execute the query
        query_obj = db.query(RedditPost)
        
        # Apply basic filters (simplified version)
        if export_request.job_ids:
            query_obj = query_obj.join(CollectionJob)
            query_obj = query_obj.filter(CollectionJob.job_id.in_(export_request.job_ids))
        
        if export_request.subreddits:
            query_obj = query_obj.filter(RedditPost.subreddit.in_(export_request.subreddits))
        
        if export_request.min_score is not None:
            query_obj = query_obj.filter(RedditPost.score >= export_request.min_score)
        
        if export_request.created_after:
            query_obj = query_obj.filter(RedditPost.created_utc >= export_request.created_after)
        
        if export_request.created_before:
            query_obj = query_obj.filter(RedditPost.created_utc <= export_request.created_before)
        
        # Apply limit
        if export_request.limit:
            query_obj = query_obj.limit(export_request.limit)
        
        posts = query_obj.all()
        
        if not posts:
            raise HTTPException(status_code=404, detail="No posts found matching criteria")
        
        # Convert to export format
        posts_data = []
        for post in posts:
            post_dict = {
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
            posts_data.append(post_dict)
        
        # Generate export based on format
        if format.lower() == "json":
            content = json.dumps(posts_data, indent=2)
            media_type = "application/json"
            filename = f"posts_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            
        elif format.lower() == "jsonl":
            content = "\n".join(json.dumps(post) for post in posts_data)
            media_type = "application/json"
            filename = f"posts_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jsonl"
            
        elif format.lower() == "csv":
            output = io.StringIO()
            if posts_data:
                writer = csv.DictWriter(output, fieldnames=posts_data[0].keys())
                writer.writeheader()
                writer.writerows(posts_data)
            content = output.getvalue()
            media_type = "text/csv"
            filename = f"posts_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            
        elif format.lower() == "parquet":
            # Convert to pandas DataFrame and export as Parquet
            df = pd.DataFrame(posts_data)
            buffer = io.BytesIO()
            df.to_parquet(buffer, index=False)
            content = buffer.getvalue()
            media_type = "application/octet-stream"
            filename = f"posts_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.parquet"
        
        # Set response headers
        response.headers["Content-Disposition"] = f"attachment; filename={filename}"
        response.headers["Content-Length"] = str(len(content))
        
        logger.info(f"Exported {len(posts_data)} posts in {format} format")
        
        return Response(
            content=content,
            media_type=media_type,
            headers={
                "Content-Disposition": f"attachment; filename={filename}",
                "X-Export-Count": str(len(posts_data)),
                "X-Export-Format": format.upper()
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Export failed: {e}")
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")

@router.post("/comments/{format}")
async def export_comments(
    format: str,
    export_request: CommentQueryRequest,
    response: Response,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_export_limit)
):
    """
    Export comments in specified format (csv, json, jsonl, parquet)
    
    Uses the same filtering options as the Data API comments query
    but returns the data in the requested export format.
    """
    try:
        if format.lower() not in ["csv", "json", "jsonl", "parquet"]:
            raise HTTPException(status_code=400, detail="Supported formats: csv, json, jsonl, parquet")
        
        # Build query (simplified version of Data API logic)
        query_obj = db.query(RedditComment).join(RedditPost)
        
        if export_request.job_ids:
            query_obj = query_obj.join(CollectionJob)
            query_obj = query_obj.filter(CollectionJob.job_id.in_(export_request.job_ids))
        
        if export_request.subreddits:
            query_obj = query_obj.filter(RedditPost.subreddit.in_(export_request.subreddits))
        
        if export_request.min_score is not None:
            query_obj = query_obj.filter(RedditComment.score >= export_request.min_score)
        
        if export_request.limit:
            query_obj = query_obj.limit(export_request.limit)
        
        comments = query_obj.all()
        
        if not comments:
            raise HTTPException(status_code=404, detail="No comments found matching criteria")
        
        # Convert to export format
        comments_data = []
        for comment in comments:
            comment_dict = {
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
                # Post context
                "post_title": comment.post.title,
                "post_subreddit": comment.post.subreddit,
                "post_score": comment.post.score
            }
            comments_data.append(comment_dict)
        
        # Generate export based on format
        if format.lower() == "json":
            content = json.dumps(comments_data, indent=2)
            media_type = "application/json"
            filename = f"comments_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            
        elif format.lower() == "jsonl":
            content = "\n".join(json.dumps(comment) for comment in comments_data)
            media_type = "application/json"
            filename = f"comments_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jsonl"
            
        elif format.lower() == "csv":
            output = io.StringIO()
            if comments_data:
                writer = csv.DictWriter(output, fieldnames=comments_data[0].keys())
                writer.writeheader()
                writer.writerows(comments_data)
            content = output.getvalue()
            media_type = "text/csv"
            filename = f"comments_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            
        elif format.lower() == "parquet":
            df = pd.DataFrame(comments_data)
            buffer = io.BytesIO()
            df.to_parquet(buffer, index=False)
            content = buffer.getvalue()
            media_type = "application/octet-stream"
            filename = f"comments_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.parquet"
        
        logger.info(f"Exported {len(comments_data)} comments in {format} format")
        
        return Response(
            content=content,
            media_type=media_type,
            headers={
                "Content-Disposition": f"attachment; filename={filename}",
                "X-Export-Count": str(len(comments_data)),
                "X-Export-Format": format.upper()
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Comment export failed: {e}")
        raise HTTPException(status_code=500, detail=f"Comment export failed: {str(e)}")

@router.get("/job/{job_id}/{format}")
async def export_job_data(
    job_id: str,
    format: str,
    include_comments: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_export_limit)
):
    """
    Export all data from a specific collection job
    
    Exports posts and optionally comments from a completed collection job
    in the specified format.
    """
    try:
        if format.lower() not in ["csv", "json", "jsonl", "parquet"]:
            raise HTTPException(status_code=400, detail="Supported formats: csv, json, jsonl, parquet")
        
        # Verify job exists
        job = db.query(CollectionJob).filter(CollectionJob.job_id == job_id).first()
        if not job:
            raise HTTPException(status_code=404, detail="Collection job not found")
        
        # Get job posts
        posts = db.query(RedditPost).filter(RedditPost.collection_job_id == job.id).all()
        
        if not posts:
            raise HTTPException(status_code=404, detail="No data found for this job")
        
        # Build export data
        export_data = {
            "job_metadata": {
                "job_id": job.job_id,
                "subreddits": job.subreddits,
                "status": job.status.value,
                "created_at": job.created_at.isoformat() if job.created_at else None,
                "completed_at": job.completed_at.isoformat() if job.completed_at else None,
                "total_posts": len(posts),
                "collected_posts": job.collected_posts,
                "collected_comments": job.collected_comments
            },
            "posts": []
        }
        
        # Add posts data
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
                "created_utc": post.created_utc.isoformat() if post.created_utc else None,
                "collected_at": post.collected_at.isoformat() if post.collected_at else None
            }
            
            # Include comments if requested
            if include_comments:
                comments = db.query(RedditComment).filter(RedditComment.post_id == post.id).all()
                post_data["comments"] = [
                    {
                        "reddit_id": comment.reddit_id,
                        "body": comment.body,
                        "author": comment.author,
                        "score": comment.score,
                        "depth": comment.depth,
                        "created_utc": comment.created_utc.isoformat() if comment.created_utc else None
                    }
                    for comment in comments
                ]
            
            export_data["posts"].append(post_data)
        
        # Generate export
        if format.lower() == "json":
            content = json.dumps(export_data, indent=2)
            media_type = "application/json"
            filename = f"job_{job_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            
        elif format.lower() == "jsonl":
            # For JSONL, flatten the structure
            lines = []
            lines.append(json.dumps(export_data["job_metadata"]))
            for post in export_data["posts"]:
                lines.append(json.dumps(post))
            content = "\n".join(lines)
            media_type = "application/json"
            filename = f"job_{job_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jsonl"
            
        elif format.lower() == "csv":
            # For CSV, export just the posts data
            output = io.StringIO()
            if export_data["posts"]:
                # Flatten nested data for CSV
                flattened_posts = []
                for post in export_data["posts"]:
                    flat_post = post.copy()
                    if "comments" in flat_post:
                        flat_post["comment_count"] = len(flat_post["comments"])
                        del flat_post["comments"]  # Remove nested data
                    flattened_posts.append(flat_post)
                
                writer = csv.DictWriter(output, fieldnames=flattened_posts[0].keys())
                writer.writeheader()
                writer.writerows(flattened_posts)
            content = output.getvalue()
            media_type = "text/csv"
            filename = f"job_{job_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            
        elif format.lower() == "parquet":
            # For Parquet, export just the posts as DataFrame
            df = pd.DataFrame(export_data["posts"])
            if "comments" in df.columns:
                df["comment_count"] = df["comments"].apply(len)
                df = df.drop("comments", axis=1)
            
            buffer = io.BytesIO()
            df.to_parquet(buffer, index=False)
            content = buffer.getvalue()
            media_type = "application/octet-stream"
            filename = f"job_{job_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.parquet"
        
        logger.info(f"Exported job {job_id} data ({len(posts)} posts) in {format} format")
        
        return Response(
            content=content,
            media_type=media_type,
            headers={
                "Content-Disposition": f"attachment; filename={filename}",
                "X-Export-Job-ID": job_id,
                "X-Export-Post-Count": str(len(posts)),
                "X-Export-Format": format.upper()
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Job export failed: {e}")
        raise HTTPException(status_code=500, detail=f"Job export failed: {str(e)}")

@router.get("/formats")
async def get_supported_formats(
    current_user: User = Depends(require_export_limit)
):
    """
    Get list of supported export formats and their descriptions
    """
    return {
        "supported_formats": {
            "csv": {
                "description": "Comma-separated values format",
                "media_type": "text/csv",
                "use_case": "Spreadsheet applications, data analysis",
                "supports_nested": False
            },
            "json": {
                "description": "JavaScript Object Notation",
                "media_type": "application/json",
                "use_case": "API consumption, web applications",
                "supports_nested": True
            },
            "jsonl": {
                "description": "JSON Lines format (one JSON object per line)",
                "media_type": "application/json",
                "use_case": "Streaming data processing, log analysis",
                "supports_nested": True
            },
            "parquet": {
                "description": "Apache Parquet columnar storage format",
                "media_type": "application/octet-stream",
                "use_case": "Big data analytics, data warehousing",
                "supports_nested": False
            }
        },
        "export_types": [
            "posts",
            "comments", 
            "job_data"
        ],
        "usage_examples": {
            "posts_csv": "/api/export/posts/csv",
            "comments_json": "/api/export/comments/json", 
            "job_data_parquet": "/api/export/job/{job_id}/parquet"
        }
    }
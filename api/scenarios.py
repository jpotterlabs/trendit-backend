from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, date, timedelta
from pydantic import BaseModel

from models.database import get_db
from models.models import User
from services.data_collector import DataCollector
from api.auth import require_api_call_limit

router = APIRouter(prefix="/api/scenarios", tags=["scenarios"])
collector = DataCollector()

# Request/Response Models
class ScenarioResponse(BaseModel):
    scenario: str
    description: str
    results: List[dict]
    count: int
    execution_time_ms: float

# SCENARIO 1: Search posts by keyword and date range
@router.get("/1/subreddit-keyword-search", response_model=ScenarioResponse)
async def scenario_1_subreddit_keyword_search(
    subreddit: str = Query(..., description="Subreddit name (e.g., 'python')"),
    keywords: str = Query(..., description="Comma-separated keywords (e.g., 'poetry,package')"),
    date_from: date = Query(..., description="Start date (YYYY-MM-DD)"),
    date_to: date = Query(..., description="End date (YYYY-MM-DD)"),
    limit: int = Query(10, description="Number of results to return"),
    sort_by: str = Query("score", description="Sort by: score, comments, date"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_api_call_limit)
):
    """
    SCENARIO 1: Get the 10 most popular posts in r/python about 'poetry' from date X to Y
    
    Example: GET /api/scenarios/1/subreddit-keyword-search?subreddit=python&keywords=poetry,package&date_from=2024-01-01&date_to=2024-12-31&limit=10&sort_by=score
    """
    try:
        import time
        start_time = time.time()
        
        keyword_list = [k.strip() for k in keywords.split(',')]
        date_from_dt = datetime.combine(date_from, datetime.min.time())
        date_to_dt = datetime.combine(date_to, datetime.max.time())
        
        results = await collector.search_subreddit_posts_by_keyword_and_date(
            subreddit=subreddit,
            keywords=keyword_list,
            date_from=date_from_dt,
            date_to=date_to_dt,
            limit=limit,
            sort_by=sort_by
        )
        
        execution_time = (time.time() - start_time) * 1000
        
        return ScenarioResponse(
            scenario="1",
            description=f"Most popular posts in r/{subreddit} about {keyword_list} from {date_from} to {date_to}",
            results=results,
            count=len(results),
            execution_time_ms=round(execution_time, 2)
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# SCENARIO 2: Trending posts across multiple subreddits
@router.get("/2/trending-multi-subreddits", response_model=ScenarioResponse)
async def scenario_2_trending_multi_subreddits(
    subreddits: str = Query(..., description="Comma-separated subreddit names (e.g., 'claudecode,vibecoding,aiagent')"),
    timeframe: str = Query("day", description="Timeframe: hour, day, week"),
    limit: int = Query(10, description="Number of trending posts to return"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_api_call_limit)
):
    """
    SCENARIO 2: Trending posts in r/claudecode, r/vibecoding, and r/aiagent for today
    
    Example: GET /api/scenarios/2/trending-multi-subreddits?subreddits=claudecode,vibecoding,aiagent&timeframe=day&limit=10
    """
    try:
        import time
        start_time = time.time()
        
        subreddit_list = [s.strip() for s in subreddits.split(',')]
        
        results = await collector.get_trending_posts_multiple_subreddits(
            subreddits=subreddit_list,
            timeframe=timeframe,
            limit_per_subreddit=20,
            final_limit=limit
        )
        
        execution_time = (time.time() - start_time) * 1000
        
        return ScenarioResponse(
            scenario="2",
            description=f"Trending posts across {subreddit_list} for {timeframe}",
            results=results,
            count=len(results),
            execution_time_ms=round(execution_time, 2)
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# SCENARIO 3: Top posts in r/all
@router.get("/3/top-posts-all", response_model=ScenarioResponse)
async def scenario_3_top_posts_all(
    sort_type: str = Query("hot", description="Sort type: hot, top, new, rising, controversial"),
    time_filter: str = Query("week", description="Time filter: hour, day, week, month, year, all"),
    limit: int = Query(10, description="Number of posts to return"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_api_call_limit)
):
    """
    SCENARIO 3: Top 10 hot posts in r/all for this week
    
    Example: GET /api/scenarios/3/top-posts-all?sort_type=hot&time_filter=week&limit=10
    """
    try:
        import time
        start_time = time.time()
        
        results = await collector.get_top_posts_all_reddit(
            sort_type=sort_type,
            time_filter=time_filter,
            limit=limit
        )
        
        execution_time = (time.time() - start_time) * 1000
        
        return ScenarioResponse(
            scenario="3",
            description=f"Top {limit} {sort_type} posts in r/all for {time_filter}",
            results=results,
            count=len(results),
            execution_time_ms=round(execution_time, 2)
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# SCENARIO 4: Most popular post in subreddit today
@router.get("/4/most-popular-today", response_model=ScenarioResponse)
async def scenario_4_most_popular_today(
    subreddit: str = Query(..., description="Subreddit name (e.g., 'openai')"),
    metric: str = Query("score", description="Popularity metric: score, comments, upvote_ratio"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_api_call_limit)
):
    """
    SCENARIO 4: Most popular post in r/openai today
    
    Example: GET /api/scenarios/4/most-popular-today?subreddit=openai&metric=score
    """
    try:
        import time
        start_time = time.time()
        
        result = await collector.get_most_popular_post_today(
            subreddit=subreddit,
            metric=metric
        )
        
        execution_time = (time.time() - start_time) * 1000
        
        results = [result] if result else []
        
        return ScenarioResponse(
            scenario="4",
            description=f"Most popular post in r/{subreddit} today by {metric}",
            results=results,
            count=len(results),
            execution_time_ms=round(execution_time, 2)
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# COMMENT SCENARIOS
@router.get("/comments/top-by-criteria", response_model=ScenarioResponse)
async def get_top_comments_by_criteria(
    subreddit: Optional[str] = Query(None, description="Specific subreddit to search"),
    post_id: Optional[str] = Query(None, description="Specific post ID to get comments from"),
    keywords: Optional[str] = Query(None, description="Comma-separated keywords to search for"),
    days_back: int = Query(7, description="Days to look back"),
    limit: int = Query(10, description="Number of comments to return"),
    sort_by: str = Query("score", description="Sort by: score, date, length"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_api_call_limit)
):
    """
    Get top comments based on various criteria
    
    Examples:
    - Top comments in r/python about 'django': GET /comments/top-by-criteria?subreddit=python&keywords=django&limit=10
    - Top comments on specific post: GET /comments/top-by-criteria?post_id=abc123&limit=10
    """
    try:
        import time
        start_time = time.time()
        
        # Calculate date range
        date_to = datetime.utcnow()
        date_from = date_to - timedelta(days=days_back)
        
        keyword_list = [k.strip() for k in keywords.split(',')] if keywords else None
        
        results = await collector.get_top_comments_by_criteria(
            subreddit=subreddit,
            post_id=post_id,
            date_from=date_from,
            date_to=date_to,
            keywords=keyword_list,
            limit=limit,
            sort_by=sort_by
        )
        
        execution_time = (time.time() - start_time) * 1000
        
        description_parts = []
        if subreddit:
            description_parts.append(f"in r/{subreddit}")
        if post_id:
            description_parts.append(f"on post {post_id}")
        if keyword_list:
            description_parts.append(f"about {keyword_list}")
        
        description = f"Top comments {' '.join(description_parts)} sorted by {sort_by}"
        
        return ScenarioResponse(
            scenario="comments",
            description=description,
            results=results,
            count=len(results),
            execution_time_ms=round(execution_time, 2)
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# USER SCENARIOS  
@router.get("/users/top-by-activity", response_model=ScenarioResponse)
async def get_top_users_by_activity(
    subreddits: Optional[str] = Query(None, description="Comma-separated subreddit names to analyze"),
    days_back: int = Query(7, description="Days to analyze"),
    limit: int = Query(10, description="Number of users to return"),
    metric: str = Query("total_score", description="Ranking metric: total_score, post_count, comment_count"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_api_call_limit)
):
    """
    Get most active/popular users based on various metrics
    
    Examples:
    - Most active users in r/python: GET /users/top-by-activity?subreddits=python&metric=post_count&limit=10
    - Highest scoring users across multiple subs: GET /users/top-by-activity?subreddits=python,javascript,golang&metric=total_score
    """
    try:
        import time
        start_time = time.time()
        
        subreddit_list = [s.strip() for s in subreddits.split(',')] if subreddits else None
        
        results = await collector.get_top_users_by_activity(
            subreddits=subreddit_list,
            timeframe_days=days_back,
            limit=limit,
            metric=metric
        )
        
        execution_time = (time.time() - start_time) * 1000
        
        subreddit_desc = f"in {subreddit_list}" if subreddit_list else "across Reddit"
        
        return ScenarioResponse(
            scenario="users",
            description=f"Top {limit} users by {metric} {subreddit_desc} over last {days_back} days",
            results=results,
            count=len(results),
            execution_time_ms=round(execution_time, 2)
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# COMBINED SCENARIOS ENDPOINT
@router.get("/examples", response_model=dict)
async def get_scenario_examples(
    current_user: User = Depends(require_api_call_limit)
):
    """
    Get example API calls for all scenarios
    """
    examples = {
        "scenario_1": {
            "description": "10 most popular posts in r/python about 'poetry' from date X to Y",
            "endpoint": "/api/scenarios/1/subreddit-keyword-search",
            "example_url": "/api/scenarios/1/subreddit-keyword-search?subreddit=python&keywords=poetry,package&date_from=2024-01-01&date_to=2024-12-31&limit=10&sort_by=score"
        },
        "scenario_2": {
            "description": "Trending posts in r/claudecode, r/vibecoding, r/aiagent for today",
            "endpoint": "/api/scenarios/2/trending-multi-subreddits", 
            "example_url": "/api/scenarios/2/trending-multi-subreddits?subreddits=claudecode,vibecoding,aiagent&timeframe=day&limit=10"
        },
        "scenario_3": {
            "description": "Top 10 hot posts in r/all for this week",
            "endpoint": "/api/scenarios/3/top-posts-all",
            "example_url": "/api/scenarios/3/top-posts-all?sort_type=hot&time_filter=week&limit=10"
        },
        "scenario_4": {
            "description": "Most popular post in r/openai today",
            "endpoint": "/api/scenarios/4/most-popular-today",
            "example_url": "/api/scenarios/4/most-popular-today?subreddit=openai&metric=score"
        },
        "comments": {
            "description": "Top comments with various filters",
            "endpoint": "/api/scenarios/comments/top-by-criteria",
            "examples": [
                "/api/scenarios/comments/top-by-criteria?subreddit=python&keywords=django&limit=10",
                "/api/scenarios/comments/top-by-criteria?post_id=abc123&limit=10"
            ]
        },
        "users": {
            "description": "Most active users by various metrics",
            "endpoint": "/api/scenarios/users/top-by-activity",
            "examples": [
                "/api/scenarios/users/top-by-activity?subreddits=python&metric=post_count&limit=10",
                "/api/scenarios/users/top-by-activity?subreddits=python,javascript,golang&metric=total_score"
            ]
        }
    }
    
    return {
        "description": "Trendit API Scenarios - Comprehensive Reddit Data Collection Examples",
        "scenarios": examples,
        "base_url": "http://localhost:8000"
    }
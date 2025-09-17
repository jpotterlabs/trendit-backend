from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
import logging

from services.sentiment_analyzer import sentiment_analyzer
from models.models import User
from api.auth import require_sentiment_limit

router = APIRouter(prefix="/api/sentiment", tags=["sentiment"])
logger = logging.getLogger(__name__)

class SentimentAnalysisRequest(BaseModel):
    text: str = Field(
        ...,
        example="I absolutely love this new machine learning framework! It's so intuitive and well-documented.",
        description="Text content to analyze for sentiment (posts, comments, reviews, etc.)"
    )

class BatchSentimentAnalysisRequest(BaseModel):
    texts: List[str] = Field(
        ...,
        example=[
            "This API is amazing! Works perfectly for my research project.",
            "The documentation could be better, but overall it's okay.",
            "Terrible experience, nothing worked as expected."
        ],
        description="List of text strings to analyze sentiment for in batch"
    )

class SentimentAnalysisResponse(BaseModel):
    text: str
    sentiment_score: Optional[float]
    sentiment_label: str
    analysis_time_ms: float

class BatchSentimentAnalysisResponse(BaseModel):
    results: List[SentimentAnalysisResponse]
    stats: Dict[str, Any]
    total_time_ms: float

@router.get("/status")
async def get_sentiment_analysis_status(
    current_user: User = Depends(require_sentiment_limit)
):
    """
    Get sentiment analysis service status
    """
    return {
        "available": sentiment_analyzer.is_available(),
        "api_configured": sentiment_analyzer.api_key is not None,
        "model": sentiment_analyzer.model,
        "description": "OpenRouter-powered sentiment analysis for Reddit content"
    }

@router.post("/analyze", response_model=SentimentAnalysisResponse)
async def analyze_text_sentiment(
    request: SentimentAnalysisRequest,
    current_user: User = Depends(require_sentiment_limit)
):
    """
    Analyze sentiment of a single text
    """
    if not sentiment_analyzer.is_available():
        raise HTTPException(
            status_code=503, 
            detail="Sentiment analysis is not available. Please configure OPENROUTER_API_KEY."
        )
    
    import time
    start_time = time.time()
    
    async with sentiment_analyzer:
        sentiment_score = await sentiment_analyzer.analyze_text(request.text)
    
    analysis_time = (time.time() - start_time) * 1000
    
    return SentimentAnalysisResponse(
        text=request.text[:100] + "..." if len(request.text) > 100 else request.text,
        sentiment_score=sentiment_score,
        sentiment_label=sentiment_analyzer.get_sentiment_label(sentiment_score),
        analysis_time_ms=analysis_time
    )

@router.post("/analyze-batch", response_model=BatchSentimentAnalysisResponse)
async def analyze_batch_sentiment(
    request: BatchSentimentAnalysisRequest,
    current_user: User = Depends(require_sentiment_limit)
):
    """
    Analyze sentiment of multiple texts in batch
    """
    if not sentiment_analyzer.is_available():
        raise HTTPException(
            status_code=503, 
            detail="Sentiment analysis is not available. Please configure OPENROUTER_API_KEY."
        )
    
    if len(request.texts) > 50:
        raise HTTPException(
            status_code=400,
            detail="Maximum 50 texts allowed per batch"
        )
    
    import time
    start_time = time.time()
    
    async with sentiment_analyzer:
        sentiment_scores = await sentiment_analyzer.analyze_batch(request.texts)
    
    total_time = (time.time() - start_time) * 1000
    
    # Create individual results
    results = []
    for text, score in zip(request.texts, sentiment_scores):
        results.append(SentimentAnalysisResponse(
            text=text[:100] + "..." if len(text) > 100 else text,
            sentiment_score=score,
            sentiment_label=sentiment_analyzer.get_sentiment_label(score),
            analysis_time_ms=0  # Individual time not tracked in batch
        ))
    
    # Calculate statistics
    stats = sentiment_analyzer.get_sentiment_stats(sentiment_scores)
    
    return BatchSentimentAnalysisResponse(
        results=results,
        stats=stats,
        total_time_ms=total_time
    )

@router.get("/test")
async def test_sentiment_analysis(
    current_user: User = Depends(require_sentiment_limit)
):
    """
    Test sentiment analysis with sample texts
    """
    if not sentiment_analyzer.is_available():
        return {
            "available": False,
            "message": "Sentiment analysis is not available. Configure OPENROUTER_API_KEY to test."
        }
    
    test_texts = [
        "I absolutely love this new feature! It's amazing and works perfectly.",
        "This is terrible. I hate it so much and it never works properly.",
        "It's okay, nothing special. Just an average implementation.",
        "FastAPI is an excellent framework for building APIs quickly.",
        "The documentation could be better, but overall it's not bad."
    ]
    
    async with sentiment_analyzer:
        scores = await sentiment_analyzer.analyze_batch(test_texts)
    
    results = []
    for text, score in zip(test_texts, scores):
        results.append({
            "text": text,
            "score": score,
            "label": sentiment_analyzer.get_sentiment_label(score)
        })
    
    stats = sentiment_analyzer.get_sentiment_stats(scores)
    
    return {
        "available": True,
        "test_results": results,
        "statistics": stats
    }
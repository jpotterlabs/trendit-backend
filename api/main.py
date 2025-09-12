from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging
import uvicorn
from contextlib import asynccontextmanager

from models.database import engine, Base
from api.scenarios import router as scenarios_router
from api.query import router as query_router
from api.collect import router as collect_router
from api.data import router as data_router
from api.export import router as export_router
from api.sentiment import router as sentiment_router
from api.auth import router as auth_router
from api.auth0_auth import router as auth0_router
from api.billing import router as billing_router
from api.webhooks import router as webhooks_router
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup
    logger.info("Starting Trendit API server...")
    
    # Create database tables
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created/verified")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Trendit API server...")

# Create FastAPI application
app = FastAPI(
    title="Trendit API",
    description="Comprehensive Reddit Data Collection and Analysis Platform",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth_router)
app.include_router(auth0_router)
app.include_router(billing_router)
app.include_router(webhooks_router)
app.include_router(scenarios_router)
app.include_router(query_router)
app.include_router(collect_router)
app.include_router(data_router)
app.include_router(export_router)
app.include_router(sentiment_router)

@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "message": "Welcome to Trendit API",
        "description": "Comprehensive Reddit Data Collection and Analysis Platform",
        "version": "1.0.0",
        "features": [
            "Reddit post collection with advanced filtering",
            "Comment thread analysis",
            "User activity tracking",
            "Multi-subreddit trending analysis",
            "Temporal and engagement analytics",
            "Real-time data streaming",
            "Persistent data pipeline with job management",
            "Advanced data querying and analytics",
            "Export to multiple formats (CSV, JSON, JSONL, Parquet)"
        ],
        "scenarios": {
            "1": "Search posts by keywords and date range in specific subreddits",
            "2": "Get trending posts across multiple subreddits",
            "3": "Retrieve top posts from r/all with filters",
            "4": "Find most popular posts in subreddits by timeframe",
            "comments": "Advanced comment analysis and filtering",
            "users": "User activity and popularity metrics"
        },
        "endpoints": {
            "scenarios": "/api/scenarios/examples",
            "collection": "/api/datastore/jobs",
            "data_query": "/api/databrowser/summary",
            "export": "/api/export/formats",
            "sentiment": "/api/sentiment/status",
            "docs": "/docs",
            "redoc": "/redoc"
        },
        "github": "https://github.com/username/trendit"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Test database connection
        from models.database import SessionLocal
        from sqlalchemy import text
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
        
        # Test Reddit API credentials
        reddit_configured = all([
            os.getenv("REDDIT_CLIENT_ID"),
            os.getenv("REDDIT_CLIENT_SECRET")
        ])
        
        return {
            "status": "healthy",
            "database": "connected",
            "reddit_api": "configured" if reddit_configured else "not_configured",
            "timestamp": "2024-01-01T00:00:00Z"
        }
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail=f"Service unavailable: {str(e)}")

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler"""
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "message": "An unexpected error occurred",
            "type": type(exc).__name__
        }
    )

if __name__ == "__main__":
    # Get configuration from environment
    host = os.getenv("HOST", "localhost")
    port = int(os.getenv("PORT", 8000))
    reload = os.getenv("RELOAD", "true").lower() == "true"
    
    logger.info(f"Starting Trendit API server on {host}:{port}")
    
    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=reload,
        log_level="info"
    )
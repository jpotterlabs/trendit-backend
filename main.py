# Vercel cache bust
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging
import uvicorn
from contextlib import asynccontextmanager
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
from sentry_sdk.integrations.logging import LoggingIntegration

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

# Initialize Sentry for error monitoring
sentry_dsn = os.getenv("SENTRY_DSN")
if sentry_dsn:
    sentry_sdk.init(
        dsn=sentry_dsn,
        integrations=[
            FastApiIntegration(auto_enabling_integrations=True),
            SqlalchemyIntegration(),
            LoggingIntegration(
                level=logging.INFO,        # Capture info and above as breadcrumbs
                event_level=logging.ERROR  # Send errors as events
            ),
        ],
        traces_sample_rate=1.0 if os.getenv("DEBUG", "false").lower() == "true" else 0.1,
        profiles_sample_rate=1.0 if os.getenv("DEBUG", "false").lower() == "true" else 0.1,
        environment=os.getenv("ENVIRONMENT", "development"),
        before_send=lambda event, hint: event if event.get('level') != 'info' else None,
    )

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
    
    try:
        # Log the database URL
        from models.database import DATABASE_URL
        logger.info(f"Connecting to database: {DATABASE_URL}")
        
        # Create database tables
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created/verified")
        
        # Initialize rate limiter
        from services.rate_limiter import rate_limiter
        logger.info("Rate limiter initialized (Redis or in-memory fallback)")
        
    except Exception as e:
        logger.error(f"Error during startup: {e}")
        # You might want to raise the exception to prevent the app from starting
        # raise e
    
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

# Configure CORS for production and development
allowed_origins = [
    "https://trendit.potterlabs.xyz",  # Production frontend
    "https://trendit.potterlabs.xyz/",  # With trailing slash
]

# Read localhost CORS environment flag
allow_localhost_cors = os.getenv("ALLOW_LOCALHOST_CORS", "false").lower() in ("true", "1", "yes", "on")

# Define localhost origins for development
localhost_origins = [
    "http://localhost:3000",  # Development frontend
    "http://localhost:3001",  # Alternative dev port
    "https://localhost:3000",  # HTTPS dev
    "http://127.0.0.1:3000",  # Alternative localhost
    "https://127.0.0.1:3000",  # HTTPS 127.0.0.1
]

# Only allow localhost origins when environment flag is enabled
if allow_localhost_cors:
    allowed_origins.extend(localhost_origins)

# Add environment-specific origins
if os.getenv("ADDITIONAL_CORS_ORIGINS"):
    additional_origins = os.getenv("ADDITIONAL_CORS_ORIGINS").split(",")
    allowed_origins.extend([origin.strip() for origin in additional_origins])

# In development, allow all origins for easier testing
if os.getenv("DEBUG", "false").lower() == "true":
    allowed_origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
    expose_headers=["*"],
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
            "collection": "/api/collect/jobs",
            "data_query": "/api/data/summary",
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

        # Test Sentry configuration
        sentry_configured = bool(os.getenv("SENTRY_DSN"))

        return {
            "status": "healthy",
            "database": "connected",
            "reddit_api": "configured" if reddit_configured else "not_configured",
            "sentry": "configured" if sentry_configured else "not_configured",
            "timestamp": "2024-01-01T00:00:00Z"
        }

    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail=f"Service unavailable: {str(e)}")

@app.get("/debug/test-error")
async def test_error():
    """Test endpoint to verify Sentry error reporting - REMOVE IN PRODUCTION"""
    logger.info("Test error endpoint called - this should appear in Sentry as breadcrumb")
    raise Exception("This is a test error to verify Sentry integration is working correctly")

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
from sqlalchemy import Column, Integer, String, DateTime, Float, Boolean, Text, ForeignKey, Index, JSON, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .database import Base
import enum

class JobStatus(enum.Enum):
    PENDING = "pending"
    RUNNING = "running" 
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class SortType(enum.Enum):
    HOT = "hot"
    NEW = "new"
    TOP = "top"
    RISING = "rising"
    CONTROVERSIAL = "controversial"

class TimeFilter(enum.Enum):
    HOUR = "hour"
    DAY = "day"
    WEEK = "week"
    MONTH = "month"
    YEAR = "year"
    ALL = "all"

class SubscriptionStatus(enum.Enum):
    INACTIVE = "inactive"
    ACTIVE = "active"
    TRIALING = "trialing"
    SUSPENDED = "suspended"
    CANCELLED = "cancelled"

class SubscriptionTier(enum.Enum):
    FREE = "free"
    PRO = "pro"
    PREMIUM = "premium"

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    password_hash = Column(String, nullable=True)  # Nullable for OAuth users
    is_active = Column(Boolean, default=True)
    subscription_status = Column(Enum(SubscriptionStatus), default=SubscriptionStatus.INACTIVE)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Auth0 Integration Fields
    auth0_user_id = Column(String, nullable=True, unique=True, index=True)  # Auth0 sub claim
    auth0_provider = Column(String, nullable=True)  # 'google', 'github', 'auth0'
    
    # Relationships
    collection_jobs = relationship("CollectionJob", back_populates="user")
    api_keys = relationship("APIKey", back_populates="user")
    paddle_subscription = relationship("PaddleSubscription", back_populates="user", uselist=False)

class APIKey(Base):
    __tablename__ = "api_keys"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    key_hash = Column(String, nullable=False, index=True)  # Store hashed version
    name = Column(String, nullable=False)  # User-friendly name for the key
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=True)
    last_used_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="api_keys")

class CollectionJob(Base):
    __tablename__ = "collection_jobs"
    
    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(String, unique=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    # Collection Parameters
    subreddits = Column(JSON)  # List of subreddit names
    sort_types = Column(JSON)  # List of sort types
    time_filters = Column(JSON)  # List of time filters
    post_limit = Column(Integer, default=100)
    comment_limit = Column(Integer, default=50)
    max_comment_depth = Column(Integer, default=3)
    
    # Filters
    keywords = Column(JSON)  # Search keywords
    min_score = Column(Integer, default=0)
    min_upvote_ratio = Column(Float, default=0.0)
    date_from = Column(DateTime(timezone=True), nullable=True)
    date_to = Column(DateTime(timezone=True), nullable=True)
    exclude_nsfw = Column(Boolean, default=True)
    anonymize_users = Column(Boolean, default=True)
    
    # Status and Progress
    status = Column(Enum(JobStatus), default=JobStatus.PENDING)
    progress = Column(Integer, default=0)
    total_expected = Column(Integer, default=0)
    collected_posts = Column(Integer, default=0)
    collected_comments = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="collection_jobs")
    posts = relationship("RedditPost", back_populates="collection_job")
    analytics = relationship("Analytics", back_populates="collection_job")

class RedditPost(Base):
    __tablename__ = "reddit_posts"
    
    id = Column(Integer, primary_key=True, index=True)
    collection_job_id = Column(Integer, ForeignKey("collection_jobs.id"))
    
    # Reddit Data
    reddit_id = Column(String, unique=True, index=True)
    title = Column(Text)
    selftext = Column(Text, nullable=True)
    url = Column(String, nullable=True)
    permalink = Column(String)
    
    # Metadata
    subreddit = Column(String, index=True)
    author = Column(String, nullable=True)  # null if anonymized or deleted
    author_id = Column(String, nullable=True)
    
    # Metrics
    score = Column(Integer, index=True)
    upvote_ratio = Column(Float)
    num_comments = Column(Integer)
    awards_received = Column(Integer, default=0)
    
    # Content Classification
    is_nsfw = Column(Boolean, default=False)
    is_spoiler = Column(Boolean, default=False)
    is_stickied = Column(Boolean, default=False)
    post_hint = Column(String, nullable=True)  # image, video, link, etc.
    
    # Timestamps
    created_utc = Column(DateTime(timezone=True))
    collected_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Analytics
    sentiment_score = Column(Float, nullable=True)
    readability_score = Column(Float, nullable=True)
    
    # Relationships
    collection_job = relationship("CollectionJob", back_populates="posts")
    comments = relationship("RedditComment", back_populates="post")

class RedditComment(Base):
    __tablename__ = "reddit_comments"
    
    id = Column(Integer, primary_key=True, index=True)
    post_id = Column(Integer, ForeignKey("reddit_posts.id"))
    
    # Reddit Data
    reddit_id = Column(String, unique=True, index=True)
    body = Column(Text)
    parent_id = Column(String, nullable=True)  # Parent comment ID
    
    # Metadata
    author = Column(String, nullable=True)  # null if anonymized or deleted
    author_id = Column(String, nullable=True)
    depth = Column(Integer, default=0)  # Comment depth in thread
    
    # Metrics
    score = Column(Integer, index=True)
    awards_received = Column(Integer, default=0)
    
    # Flags
    is_submitter = Column(Boolean, default=False)  # Comment by post author
    is_stickied = Column(Boolean, default=False)
    
    # Timestamps
    created_utc = Column(DateTime(timezone=True))
    collected_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Analytics
    sentiment_score = Column(Float, nullable=True)
    
    # Relationships
    post = relationship("RedditPost", back_populates="comments")

class RedditUser(Base):
    __tablename__ = "reddit_users"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Reddit Data
    username = Column(String, unique=True, index=True)
    user_id = Column(String, unique=True, nullable=True)
    
    # Profile Data
    comment_karma = Column(Integer, default=0)
    link_karma = Column(Integer, default=0)
    total_karma = Column(Integer, default=0)
    account_created = Column(DateTime(timezone=True), nullable=True)
    
    # Flags
    is_employee = Column(Boolean, default=False)
    is_mod = Column(Boolean, default=False)
    is_gold = Column(Boolean, default=False)
    has_verified_email = Column(Boolean, default=False)
    
    # Timestamps
    collected_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class Analytics(Base):
    __tablename__ = "analytics"
    
    id = Column(Integer, primary_key=True, index=True)
    collection_job_id = Column(Integer, ForeignKey("collection_jobs.id"))
    
    # Summary Statistics
    total_posts = Column(Integer)
    total_comments = Column(Integer)
    total_users = Column(Integer)
    avg_score = Column(Float)
    avg_comments_per_post = Column(Float)
    avg_upvote_ratio = Column(Float)
    
    # Engagement Metrics
    top_posts = Column(JSON)  # Top posts by score
    most_commented = Column(JSON)  # Most commented posts
    active_users = Column(JSON)  # Most active users
    
    # Content Analysis
    common_keywords = Column(JSON)  # Most common keywords
    sentiment_distribution = Column(JSON)  # Sentiment analysis results
    post_type_distribution = Column(JSON)  # Distribution by post type
    
    # Temporal Analysis
    posting_patterns = Column(JSON)  # Posting frequency over time
    engagement_trends = Column(JSON)  # Engagement trends
    
    # Timestamps
    generated_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    collection_job = relationship("CollectionJob", back_populates="analytics")

# Database indexes for better performance
Index('idx_reddit_posts_subreddit_score', RedditPost.subreddit, RedditPost.score)
Index('idx_reddit_posts_created_utc', RedditPost.created_utc)
Index('idx_reddit_posts_collection_job', RedditPost.collection_job_id)
Index('idx_reddit_comments_post_id', RedditComment.post_id)
Index('idx_reddit_comments_score', RedditComment.score)
Index('idx_reddit_comments_created_utc', RedditComment.created_utc)
Index('idx_collection_jobs_status_created', CollectionJob.status, CollectionJob.created_at)
Index('idx_collection_jobs_user_id', CollectionJob.user_id)
Index('idx_api_keys_user_id', APIKey.user_id)
Index('idx_api_keys_hash', APIKey.key_hash)
Index('idx_users_email', User.email)
Index('idx_users_subscription_status', User.subscription_status)

# ============================================================================
# PADDLE BILLING INTEGRATION MODELS
# ============================================================================

class PaddleSubscription(Base):
    """Extended subscription model for Paddle Billing integration"""
    __tablename__ = "paddle_subscriptions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True)
    
    # Paddle Integration Fields
    paddle_customer_id = Column(String, nullable=True, unique=True, index=True)
    paddle_subscription_id = Column(String, nullable=True, unique=True, index=True)
    paddle_price_id = Column(String, nullable=True)
    
    # Subscription Details
    tier = Column(Enum(SubscriptionTier), default=SubscriptionTier.FREE, index=True)
    status = Column(Enum(SubscriptionStatus), default=SubscriptionStatus.INACTIVE, index=True)
    
    # Billing Cycle Information
    current_period_start = Column(DateTime(timezone=True), nullable=True)
    current_period_end = Column(DateTime(timezone=True), nullable=True)
    next_billed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Usage Limits (dynamically set based on tier)
    monthly_api_calls_limit = Column(Integer, default=100)
    monthly_exports_limit = Column(Integer, default=5)
    monthly_sentiment_limit = Column(Integer, default=50)
    data_retention_days = Column(Integer, default=30)
    
    # Billing Information
    price_per_month = Column(Float, default=0.0)
    currency = Column(String, default="USD", nullable=False)
    
    # Trial Management
    trial_start_date = Column(DateTime(timezone=True), nullable=True)
    trial_end_date = Column(DateTime(timezone=True), nullable=True)
    is_trial = Column(Boolean, default=False)
    
    # Customer Portal & Management
    customer_portal_url = Column(String, nullable=True)  # Paddle-generated URL
    
    # Metadata & Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="paddle_subscription")
    usage_records = relationship("UsageRecord", back_populates="subscription")
    billing_events = relationship("BillingEvent", back_populates="subscription")

class UsageRecord(Base):
    """Track API usage for billing and rate limiting purposes"""
    __tablename__ = "usage_records"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    subscription_id = Column(Integer, ForeignKey("paddle_subscriptions.id"), nullable=True, index=True)
    
    # Usage Details
    endpoint = Column(String, nullable=False, index=True)  # "/api/export/posts/csv"
    usage_type = Column(String, nullable=False, index=True)  # "api_call", "export", "sentiment_analysis"
    cost_units = Column(Integer, default=1)  # How many "units" this action consumed
    
    # Request Context
    request_id = Column(String, nullable=True)  # For debugging/tracing
    ip_address = Column(String, nullable=True)
    user_agent = Column(Text, nullable=True)
    
    # Billing Period Tracking
    billing_period_start = Column(DateTime(timezone=True), nullable=False, index=True)
    billing_period_end = Column(DateTime(timezone=True), nullable=False)
    
    # Additional Context
    request_metadata = Column(JSON, nullable=True)  # Additional context (file size, etc.)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    
    # Relationships
    user = relationship("User")
    subscription = relationship("PaddleSubscription", back_populates="usage_records")

class BillingEvent(Base):
    """Audit log for all billing events received from Paddle webhooks"""
    __tablename__ = "billing_events"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    subscription_id = Column(Integer, ForeignKey("paddle_subscriptions.id"), nullable=True, index=True)
    
    # Paddle Event Identification
    paddle_event_id = Column(String, nullable=False, unique=True, index=True)
    event_type = Column(String, nullable=False, index=True)  # "subscription.created", "transaction.completed"
    paddle_subscription_id = Column(String, nullable=True, index=True)
    paddle_transaction_id = Column(String, nullable=True, index=True)
    paddle_customer_id = Column(String, nullable=True, index=True)
    
    # Event Details
    amount = Column(Float, nullable=True)
    currency = Column(String, nullable=True)
    status = Column(String, nullable=False, index=True)  # "success", "failed", "pending"
    
    # Raw Event Data (for debugging and audit)
    raw_event_data = Column(Text, nullable=False)  # Full JSON dump of Paddle event
    
    # Timing
    paddle_event_time = Column(DateTime(timezone=True), nullable=False, index=True)
    processed_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Processing Status
    processing_status = Column(String, default="processed", index=True)  # "processed", "failed", "ignored"
    processing_error = Column(Text, nullable=True)
    
    # Relationships
    user = relationship("User")
    subscription = relationship("PaddleSubscription", back_populates="billing_events")

# ============================================================================
# PADDLE BILLING INDEXES FOR PERFORMANCE
# ============================================================================

# PaddleSubscription indexes
Index('idx_paddle_subscriptions_user_id', PaddleSubscription.user_id)
Index('idx_paddle_subscriptions_customer_id', PaddleSubscription.paddle_customer_id)
Index('idx_paddle_subscriptions_subscription_id', PaddleSubscription.paddle_subscription_id)
Index('idx_paddle_subscriptions_tier_status', PaddleSubscription.tier, PaddleSubscription.status)
Index('idx_paddle_subscriptions_billing_period', PaddleSubscription.current_period_start, PaddleSubscription.current_period_end)

# UsageRecord indexes for billing queries
Index('idx_usage_records_user_billing_period', UsageRecord.user_id, UsageRecord.billing_period_start)
Index('idx_usage_records_subscription_billing_period', UsageRecord.subscription_id, UsageRecord.billing_period_start)
Index('idx_usage_records_usage_type_created', UsageRecord.usage_type, UsageRecord.created_at)
Index('idx_usage_records_endpoint_created', UsageRecord.endpoint, UsageRecord.created_at)

# BillingEvent indexes for webhook processing and audit
Index('idx_billing_events_paddle_event_id', BillingEvent.paddle_event_id)
Index('idx_billing_events_user_event_time', BillingEvent.user_id, BillingEvent.paddle_event_time)
Index('idx_billing_events_subscription_event_time', BillingEvent.subscription_id, BillingEvent.paddle_event_time)
Index('idx_billing_events_event_type_time', BillingEvent.event_type, BillingEvent.paddle_event_time)
Index('idx_billing_events_processing_status', BillingEvent.processing_status)
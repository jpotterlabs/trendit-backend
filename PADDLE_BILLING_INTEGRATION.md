# Paddle Billing Integration Documentation

## Overview

This document provides comprehensive documentation for the Paddle billing integration implemented in the Trendit Reddit data intelligence platform. The integration provides a complete SaaS billing solution with usage tracking, rate limiting, and subscription management.

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Database Models](#database-models)
3. [Service Layer](#service-layer)
4. [API Endpoints](#api-endpoints)
5. [Usage Tracking & Rate Limiting](#usage-tracking--rate-limiting)
6. [Webhook System](#webhook-system)
7. [Configuration](#configuration)
8. [Testing](#testing)
9. [Deployment Guide](#deployment-guide)
10. [Troubleshooting](#troubleshooting)

## Architecture Overview

The Paddle billing integration follows a modular architecture with clear separation of concerns:

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Frontend      │    │   Trendit API    │    │   Paddle API    │
│   (Checkout)    │◄──►│   Billing Layer  │◄──►│   (Webhooks)    │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                              │
                              ▼
                    ┌──────────────────┐
                    │   PostgreSQL     │
                    │   Database       │
                    └──────────────────┘
```

### Key Components

- **Paddle Service** (`services/paddle_service.py`): Core integration with Paddle API
- **Billing API** (`api/billing.py`): REST endpoints for subscription management
- **Webhook Handler** (`api/webhooks.py`): Processes Paddle webhook events
- **Usage Tracking** (`api/auth.py`): Rate limiting and usage monitoring
- **Database Models** (`models/models.py`): Data persistence layer

## Database Models

### PaddleSubscription Model

Stores subscription information for each user:

```python
class PaddleSubscription(Base):
    __tablename__ = "paddle_subscriptions"
    
    # Core Fields
    id: int                           # Primary key
    user_id: int                      # Foreign key to users table
    paddle_customer_id: str           # Paddle customer ID
    paddle_subscription_id: str       # Paddle subscription ID
    paddle_price_id: str              # Paddle price ID
    
    # Subscription Details
    tier: SubscriptionTier            # FREE, PRO, ENTERPRISE
    status: SubscriptionStatus        # ACTIVE, INACTIVE, TRIALING, etc.
    
    # Billing Information
    current_period_start: datetime    # Current billing period start
    current_period_end: datetime      # Current billing period end
    next_billed_at: datetime          # Next billing date
    price_per_month: float            # Monthly price
    currency: str                     # Currency code (USD)
    
    # Usage Limits (set based on tier)
    monthly_api_calls_limit: int      # API calls per month
    monthly_exports_limit: int        # Data exports per month
    monthly_sentiment_limit: int      # Sentiment analyses per month
    data_retention_days: int          # Data retention period
    
    # Trial Management
    trial_start_date: datetime        # Trial start date
    trial_end_date: datetime          # Trial end date
    is_trial: bool                    # Is currently in trial
    
    # Management
    customer_portal_url: str          # Paddle customer portal URL
```

### UsageRecord Model

Tracks API usage for billing and rate limiting:

```python
class UsageRecord(Base):
    __tablename__ = "usage_records"
    
    # Core Fields
    id: int                           # Primary key
    user_id: int                      # Foreign key to users
    subscription_id: int              # Foreign key to paddle_subscriptions (nullable)
    
    # Usage Details
    endpoint: str                     # API endpoint called
    usage_type: str                   # "api_calls", "exports", "sentiment_analysis"
    cost_units: int                   # Number of units consumed (default: 1)
    
    # Request Context
    request_id: str                   # For debugging/tracing
    ip_address: str                   # Client IP address
    user_agent: str                   # Client user agent
    
    # Billing Period
    billing_period_start: datetime    # Start of billing period
    billing_period_end: datetime      # End of billing period
    
    # Additional Context
    request_metadata: JSON            # Additional request context
    created_at: datetime              # Timestamp of usage
```

### BillingEvent Model

Audit log for Paddle webhook events:

```python
class BillingEvent(Base):
    __tablename__ = "billing_events"
    
    # Core Fields
    id: int                           # Primary key
    subscription_id: int              # Foreign key to paddle_subscriptions
    paddle_event_id: str              # Paddle event ID (for deduplication)
    
    # Event Details
    event_type: str                   # Paddle event type
    event_data: JSON                  # Complete event payload
    processed_successfully: bool      # Processing status
    error_message: str                # Error details if failed
    retry_count: int                  # Number of retry attempts
    
    # Timestamps
    received_at: datetime             # When webhook was received
    processed_at: datetime            # When processing completed
```

## Service Layer

### PaddleService Class

The `PaddleService` class (`services/paddle_service.py`) provides the core integration with Paddle's API.

#### Key Methods

**Customer Management:**
```python
async def create_customer(user: User) -> Dict
async def get_customer(customer_id: str) -> Dict
```

**Subscription Management:**
```python
async def create_subscription(customer_id: str, tier: SubscriptionTier, trial_days: int = None) -> Dict
async def update_subscription(subscription_id: str, new_tier: SubscriptionTier) -> Dict
async def cancel_subscription(subscription_id: str) -> Dict
async def get_subscription(subscription_id: str) -> Dict
```

**Checkout & Payments:**
```python
async def create_checkout_url(user: User, tier: SubscriptionTier, success_url: str, cancel_url: str, trial_days: int = None) -> str
```

**Webhook Verification:**
```python
def verify_webhook(payload: bytes, signature: str, timestamp: str) -> bool
```

#### Configuration

The service is configured with tier-specific settings:

```python
tier_config = {
    SubscriptionTier.FREE: {
        "price": 0,
        "paddle_price_id": None,
        "limits": {
            "api_calls_per_month": 100,
            "exports_per_month": 5,
            "sentiment_analysis_per_month": 50,
            "data_retention_days": 30
        }
    },
    SubscriptionTier.PRO: {
        "price": 29,
        "paddle_price_id": os.getenv("PADDLE_PRO_PRICE_ID"),
        "limits": {
            "api_calls_per_month": 10000,
            "exports_per_month": 100,
            "sentiment_analysis_per_month": 2000,
            "data_retention_days": 365
        }
    },
    SubscriptionTier.ENTERPRISE: {
        "price": 299,
        "paddle_price_id": os.getenv("PADDLE_ENTERPRISE_PRICE_ID"),
        "limits": {
            "api_calls_per_month": 100000,
            "exports_per_month": 1000,
            "sentiment_analysis_per_month": 20000,
            "data_retention_days": -1  # Unlimited
        }
    }
}
```

## API Endpoints

### Billing Management (`/api/billing/`)

#### Get Subscription Tiers
```http
GET /api/billing/tiers
```

Returns available subscription tiers and their features.

**Response:**
```json
{
  "tiers": {
    "free": {
      "name": "Free",
      "price": 0,
      "currency": "USD",
      "interval": "month",
      "features": [...],
      "limits": {
        "api_calls_per_month": 100,
        "exports_per_month": 5,
        "sentiment_analysis_per_month": 50,
        "data_retention_days": 30
      }
    }
  }
}
```

#### Create Checkout Session
```http
POST /api/billing/checkout
Authorization: Bearer {token}
Content-Type: application/json

{
  "tier": "pro",
  "success_url": "https://yourapp.com/success",
  "cancel_url": "https://yourapp.com/cancel",
  "trial_days": 14
}
```

**Response:**
```json
{
  "checkout_url": "https://pay.paddle.com/...",
  "tier": "pro",
  "trial_days": 14
}
```

#### Get User Subscription Status
```http
GET /api/billing/subscription
Authorization: Bearer {token}
```

**Response:**
```json
{
  "subscription": {
    "tier": "pro",
    "status": "active",
    "current_period_start": "2025-09-01T00:00:00Z",
    "current_period_end": "2025-10-01T00:00:00Z",
    "next_billed_at": "2025-10-01T00:00:00Z",
    "price_per_month": 29.0,
    "currency": "USD",
    "is_trial": false,
    "customer_portal_url": "https://customer-portal.paddle.com/..."
  },
  "usage": {
    "current_period": {
      "api_calls": {"used": 45, "limit": 10000},
      "exports": {"used": 2, "limit": 100},
      "sentiment_analysis": {"used": 12, "limit": 2000}
    }
  }
}
```

#### Upgrade/Downgrade Subscription
```http
PUT /api/billing/subscription
Authorization: Bearer {token}
Content-Type: application/json

{
  "new_tier": "enterprise"
}
```

#### Cancel Subscription
```http
DELETE /api/billing/subscription
Authorization: Bearer {token}
```

### Webhook Handler (`/api/webhooks/`)

#### Paddle Webhook Endpoint
```http
POST /api/webhooks/paddle
Content-Type: application/json
Paddle-Signature: {signature}
Paddle-Timestamp: {timestamp}

{
  "event_type": "subscription.created",
  "data": {...}
}
```

Handles all Paddle webhook events with automatic signature verification and event processing.

## Usage Tracking & Rate Limiting

### Authentication Dependencies

The system provides specialized authentication dependencies for different usage types:

#### Export Limits
```python
@router.get("/api/export/formats")
async def get_export_formats(user: User = Depends(require_export_limit)):
    # Tracks "exports" usage type
    # Free: 5/month, Pro: 100/month, Enterprise: 1000/month
```

#### API Call Limits
```python
@router.get("/api/data/summary")
async def get_data_summary(user: User = Depends(require_api_call_limit)):
    # Tracks "api_calls" usage type
    # Free: 100/month, Pro: 10000/month, Enterprise: 100000/month
```

#### Sentiment Analysis Limits
```python
@router.post("/api/sentiment/analyze")
async def analyze_sentiment(user: User = Depends(require_sentiment_limit)):
    # Tracks "sentiment_analysis" usage type
    # Free: 50/month, Pro: 2000/month, Enterprise: 20000/month
```

### Rate Limiting Response

When limits are exceeded, the API returns:

```http
HTTP/1.1 429 Too Many Requests
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 0
X-RateLimit-Reset: 1693526400
X-User-Tier: free
Content-Type: application/json

{
  "detail": "Usage limit exceeded. 100/100 api_calls used this month. Upgrade your plan for higher limits."
}
```

### Usage Tracking Implementation

The usage tracking system:

1. **Identifies User Tier**: Checks for active Paddle subscription or defaults to FREE
2. **Calculates Billing Period**: Uses Paddle billing cycle or calendar month for free users
3. **Checks Current Usage**: Queries usage records for the current billing period
4. **Enforces Limits**: Compares current usage against tier limits
5. **Records Usage**: Creates usage record for successful requests
6. **Adds Headers**: Includes rate limit information in response headers

## Webhook System

### Supported Events

The webhook system handles the following Paddle events:

#### Subscription Events
- `subscription.created` - New subscription created
- `subscription.updated` - Subscription modified (plan change, etc.)
- `subscription.cancelled` - Subscription cancelled
- `subscription.paused` - Subscription paused
- `subscription.resumed` - Subscription resumed

#### Payment Events
- `transaction.completed` - Payment successful
- `transaction.payment_failed` - Payment failed

#### Customer Events  
- `customer.created` - New customer created
- `customer.updated` - Customer information updated

### Webhook Security

The system implements Paddle's enhanced 2025 security verification:

```python
def verify_webhook(payload: bytes, signature: str, timestamp: str) -> bool:
    # Extract signature from header (format: "ts=timestamp,h1=signature")
    signature_parts = {}
    for part in signature.split(","):
        if "=" in part:
            key, value = part.split("=", 1)
            signature_parts[key] = value
    
    webhook_signature = signature_parts.get("h1")
    if not webhook_signature:
        return False
    
    # Construct signed payload for verification
    signed_payload = f"{timestamp}.{payload.decode()}"
    
    # Calculate expected signature
    expected_signature = hmac.new(
        self.webhook_secret.encode(),
        signed_payload.encode(),
        hashlib.sha256
    ).hexdigest()
    
    # Verify signature using constant-time comparison
    return hmac.compare_digest(webhook_signature, expected_signature)
```

### Event Processing Flow

1. **Receive Webhook**: Paddle sends HTTP POST to `/api/webhooks/paddle`
2. **Verify Signature**: Validate request authenticity using HMAC-SHA256
3. **Check Duplication**: Prevent duplicate processing using `paddle_event_id`
4. **Route Event**: Direct to appropriate handler based on `event_type`
5. **Process Event**: Update database records and trigger side effects
6. **Log Event**: Create audit record in `BillingEvent` table
7. **Return Response**: Send 200 OK to acknowledge processing

### Error Handling

- **Invalid Signature**: Returns 401 Unauthorized
- **Duplicate Event**: Returns 200 OK (already processed)
- **Processing Error**: Returns 500, triggers retry logic
- **Unknown Event**: Logs warning, returns 200 OK

## Configuration

### Environment Variables

Required environment variables:

```bash
# Paddle Configuration
PADDLE_API_KEY=your_paddle_api_key
PADDLE_WEBHOOK_SECRET=your_webhook_secret

# Price IDs (from Paddle Dashboard)
PADDLE_PRO_PRICE_ID=pri_01234567890
PADDLE_ENTERPRISE_PRICE_ID=pri_09876543210

# Database Configuration
DATABASE_URL=postgresql://user:password@localhost:5432/trendit

# Application Configuration
HOST=localhost
PORT=8000
RELOAD=true
```

### Paddle Dashboard Setup

1. **Create Products**: Set up Pro ($29/month) and Enterprise ($299/month) products
2. **Configure Webhooks**: Point to `https://your-domain.com/api/webhooks/paddle`
3. **Generate API Keys**: Create sandbox and production API keys
4. **Set Price IDs**: Copy price IDs to environment variables

## Testing

### Manual Testing

Test the billing system with these curl commands:

```bash
# 1. Register user and get API key
curl -X POST "http://localhost:8000/auth/register" \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "password": "testpass123"}'

curl -X POST "http://localhost:8000/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "password": "testpass123"}'

curl -X POST "http://localhost:8000/auth/api-keys" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "test-key"}'

# 2. Test billing endpoints
curl -X GET "http://localhost:8000/api/billing/tiers"

curl -X GET "http://localhost:8000/api/billing/subscription" \
  -H "Authorization: Bearer YOUR_API_KEY"

# 3. Test usage tracking
curl -X GET "http://localhost:8000/api/export/formats" \
  -H "Authorization: Bearer YOUR_API_KEY"

curl -X GET "http://localhost:8000/api/data/summary" \
  -H "Authorization: Bearer YOUR_API_KEY"

curl -X GET "http://localhost:8000/api/sentiment/status" \
  -H "Authorization: Bearer YOUR_API_KEY"
```

### Usage Verification

Check usage records in the database:

```python
from models.database import SessionLocal
from models.models import UsageRecord, User
from sqlalchemy import func

db = SessionLocal()
user = db.query(User).filter(User.email == 'test@example.com').first()
usage_count = db.query(func.count(UsageRecord.id)).filter(UsageRecord.user_id == user.id).scalar()
print(f'User has {usage_count} usage records')
```

### Automated Testing

Run the comprehensive test suite:

```bash
# Start the server
python main.py

# In another terminal, run tests
python test_api.py
```

## Deployment Guide

### Production Checklist

1. **Environment Configuration**
   - [ ] Set production Paddle API keys
   - [ ] Configure production webhook secret
   - [ ] Update price IDs for production products
   - [ ] Set secure database connection string

2. **Database Migration**
   - [ ] Apply database schema changes
   - [ ] Verify indexes are created
   - [ ] Run data migration scripts if needed

3. **Paddle Configuration**
   - [ ] Create production products in Paddle
   - [ ] Configure production webhook URL
   - [ ] Test webhook delivery
   - [ ] Set up customer portal

4. **Security**
   - [ ] Enable HTTPS for all endpoints
   - [ ] Configure CORS properly for production
   - [ ] Set up rate limiting at infrastructure level
   - [ ] Enable logging and monitoring

5. **Monitoring**
   - [ ] Set up error tracking (Sentry, etc.)
   - [ ] Configure usage metrics collection
   - [ ] Set up billing event monitoring
   - [ ] Create alerting for failed webhooks

### Database Schema Migration

Apply the schema changes for production:

```sql
-- Create new tables
CREATE TABLE paddle_subscriptions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) NOT NULL UNIQUE,
    paddle_customer_id VARCHAR UNIQUE,
    paddle_subscription_id VARCHAR UNIQUE,
    -- ... (see models.py for complete schema)
);

CREATE TABLE usage_records (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) NOT NULL,
    subscription_id INTEGER REFERENCES paddle_subscriptions(id),
    -- ... (see models.py for complete schema)
);

CREATE TABLE billing_events (
    id SERIAL PRIMARY KEY,
    subscription_id INTEGER REFERENCES paddle_subscriptions(id),
    paddle_event_id VARCHAR UNIQUE NOT NULL,
    -- ... (see models.py for complete schema)
);

-- Create indexes for performance
CREATE INDEX idx_paddle_subscriptions_user_id ON paddle_subscriptions(user_id);
CREATE INDEX idx_paddle_subscriptions_status ON paddle_subscriptions(status);
CREATE INDEX idx_usage_records_user_billing_period ON usage_records(user_id, billing_period_start);
CREATE INDEX idx_usage_records_usage_type ON usage_records(usage_type);
CREATE INDEX idx_billing_events_paddle_event ON billing_events(paddle_event_id);
```

## Troubleshooting

### Common Issues

#### 1. Webhook Signature Verification Fails

**Symptoms**: Webhooks return 401 Unauthorized

**Solutions**:
- Verify `PADDLE_WEBHOOK_SECRET` matches Paddle dashboard
- Check timestamp tolerance (Paddle requires processing within 5 minutes)
- Ensure raw request body is used for signature verification

#### 2. Usage Tracking Not Working

**Symptoms**: No usage records created, rate limiting not enforced

**Solutions**:
- Verify API key authentication is working
- Check that endpoints use correct dependency functions
- Ensure database schema includes usage_records table
- Verify subscription_id is nullable in database

#### 3. Rate Limits Not Applied

**Symptoms**: Users exceed limits without getting 429 responses

**Solutions**:
- Check user tier calculation logic
- Verify billing period calculation
- Ensure usage records are being created
- Check tier limit configuration

#### 4. Subscription Status Issues

**Symptoms**: Subscription shows incorrect status

**Solutions**:
- Check webhook processing for subscription events
- Verify Paddle API responses
- Check database subscription records
- Test webhook delivery from Paddle

### Debug Commands

Check system status:

```python
# Check Paddle service configuration
from services.paddle_service import paddle_service
print(f"Paddle configured: {paddle_service.is_configured()}")

# Check user subscription status
from models.database import SessionLocal
from models.models import User, PaddleSubscription

db = SessionLocal()
user = db.query(User).filter(User.email == 'user@example.com').first()
subscription = db.query(PaddleSubscription).filter(PaddleSubscription.user_id == user.id).first()
print(f"User tier: {subscription.tier if subscription else 'FREE'}")
print(f"User status: {subscription.status if subscription else 'No subscription'}")
```

Check recent webhook events:

```python
from models.models import BillingEvent
recent_events = db.query(BillingEvent).order_by(BillingEvent.received_at.desc()).limit(10).all()
for event in recent_events:
    print(f"{event.event_type} - {event.processed_successfully} - {event.received_at}")
```

### Logging

Enable detailed logging for debugging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# In production, use structured logging
import structlog
logger = structlog.get_logger()
```

Key log points:
- Webhook signature verification
- Subscription status changes
- Usage record creation
- Rate limit enforcement
- API errors and exceptions

---

## Support

For additional support with the Paddle billing integration:

1. Check the Paddle documentation: https://developer.paddle.com/
2. Review Trendit API logs for error details
3. Test webhook delivery using Paddle's webhook testing tools
4. Verify environment configuration and API keys

This integration provides a robust foundation for SaaS billing with comprehensive usage tracking and rate limiting capabilities.
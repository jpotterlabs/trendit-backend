# Trendit API Documentation

Complete reference for the Trendit Backend API endpoints.

## Base URL
```text
Production: https://api.potterlabs.xyz
Local: http://localhost:8000
```

## Authentication

All API endpoints require authentication using one of these methods:

### 1. JWT Bearer Token (Frontend)
```http
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

### 2. API Key (Programmatic)
```http
Authorization: Bearer tk_abc123def456...
```

## Rate Limits

| Tier | Monthly Limit | Per Minute |
|------|---------------|------------|
| Free | 100 calls | 10 |
| Pro | 10,000 calls | 100 |
| Enterprise | Unlimited | 1000 |

## Endpoints

### Authentication

#### Create Test User (Admin Only)
```http
POST /auth/create-test-user
```

**Headers:**
```http
Content-Type: application/json
```

**Request Body:**
```json
{
  "admin_key": "your_admin_secret_key"
}
```

**Response:**
```json
{
  "user": {
    "email": "test@trendit.dev",
    "password": "TestPassword123"
  },
  "api_key": "tk_abc123def456...",
  "subscription": {
    "tier": "pro",
    "status": "active",
    "usage_limit": 10000
  }
}
```

#### Get User Profile
```http
GET /auth/profile
```

**Response:**
```json
{
  "sub": "auth0|123456789",
  "email": "user@example.com",
  "name": "User Name",
  "subscription": {
    "tier": "free",
    "status": "active",
    "usage_current": 45,
    "usage_limit": 100
  }
}
```

#### Create API Key
```http
POST /auth/api-key
```

**Response:**
```json
{
  "api_key": "tk_abc123def456...",
  "created_at": "2024-01-01T00:00:00Z",
  "usage_limit": 100
}
```

### Collection Jobs

#### Create Collection Job
```http
POST /api/jobs
```

**Request Body:**
```json
{
  "subreddits": ["python", "javascript", "webdev"],
  "sort_types": ["hot", "top", "new"],
  "time_filters": ["day", "week", "month"],
  "post_limit": 100,
  "comment_limit": 50,
  "max_comment_depth": 3,
  "keywords": ["tutorial", "guide", "beginner"],
  "min_score": 10,
  "min_upvote_ratio": 0.7,
  "exclude_nsfw": true,
  "anonymize_users": true
}
```

**Response:**
```json
{
  "job_id": "job_abc123",
  "status": "pending",
  "created_at": "2024-01-01T00:00:00Z",
  "estimated_duration": "10-15 minutes",
  "parameters": {
    "subreddits": ["python", "javascript"],
    "post_limit": 100,
    "comment_limit": 50
  }
}
```

#### Get Job Status
```http
GET /api/jobs/{job_id}
```

**Response:**
```json
{
  "job_id": "job_abc123",
  "status": "completed",
  "progress": 100,
  "created_at": "2024-01-01T00:00:00Z",
  "completed_at": "2024-01-01T00:15:30Z",
  "stats": {
    "posts_collected": 150,
    "comments_collected": 750,
    "subreddits_processed": 2,
    "processing_time": "12m 30s"
  },
  "errors": []
}
```

#### List User Jobs
```http
GET /api/jobs?limit=10&offset=0&status=completed
```

**Query Parameters:**
- `limit`: Number of jobs to return (default: 10, max: 100)
- `offset`: Pagination offset (default: 0)
- `status`: Filter by status (`pending`, `running`, `completed`, `failed`)

**Response:**
```json
{
  "jobs": [
    {
      "job_id": "job_abc123",
      "status": "completed",
      "created_at": "2024-01-01T00:00:00Z",
      "stats": {
        "posts_collected": 150,
        "comments_collected": 750
      }
    }
  ],
  "total": 25,
  "limit": 10,
  "offset": 0
}
```

### Data Query

#### Subreddit Keyword Search
```http
GET /api/scenarios/1/subreddit-keyword-search
```

**Query Parameters:**
- `subreddit` (required): Subreddit name (without r/)
- `keywords` (required): Comma-separated keywords
- `date_from` (required): Start date (YYYY-MM-DD)
- `date_to` (required): End date (YYYY-MM-DD)
- `limit` (optional): Result limit (default: 100, max: 1000)
- `sort_by` (optional): Sort field (`score`, `created_utc`, `num_comments`)
- `sort_order` (optional): Sort direction (`asc`, `desc`)

**Example:**
```http
GET /api/scenarios/1/subreddit-keyword-search?subreddit=python&keywords=tutorial,guide&date_from=2024-01-01&date_to=2024-12-31&limit=50
```

**Response:**
```json
{
  "posts": [
    {
      "id": "post_123",
      "title": "Complete Python Tutorial for Beginners",
      "author": "user123",
      "score": 1250,
      "num_comments": 89,
      "created_utc": "2024-06-15T10:30:00Z",
      "url": "https://reddit.com/r/python/comments/...",
      "selftext": "This is a comprehensive guide...",
      "subreddit": "python",
      "keywords_matched": ["tutorial", "guide"]
    }
  ],
  "total_found": 245,
  "query_info": {
    "subreddit": "python",
    "keywords": ["tutorial", "guide"],
    "date_range": "2024-01-01 to 2024-12-31",
    "limit": 50
  }
}
```

#### Advanced Search
```http
POST /api/search
```

**Request Body:**
```json
{
  "subreddits": ["python", "javascript"],
  "keywords": {
    "include": ["tutorial", "guide"],
    "exclude": ["spam", "promotional"]
  },
  "date_range": {
    "from": "2024-01-01",
    "to": "2024-12-31"
  },
  "filters": {
    "min_score": 10,
    "min_comments": 5,
    "min_upvote_ratio": 0.7,
    "exclude_nsfw": true
  },
  "sort": {
    "field": "score",
    "order": "desc"
  },
  "limit": 100
}
```

### Data Export

#### Export Job Data
```http
POST /api/export/{job_id}
```

**Request Body:**
```json
{
  "format": "csv",
  "include_posts": true,
  "include_comments": true,
  "include_metadata": true,
  "filters": {
    "min_score": 5,
    "date_from": "2024-01-01"
  }
}
```

**Response:**
```json
{
  "export_id": "export_abc123",
  "download_url": "https://api.potterlabs.xyz/exports/export_abc123.csv",
  "expires_at": "2024-01-08T00:00:00Z",
  "file_size": "2.5 MB",
  "record_count": 1500
}
```

#### Download Export
```http
GET /exports/{export_id}.{format}
```

Returns the actual file data with appropriate Content-Type headers.

### Analytics

#### Get Engagement Trends
```http
GET /api/analytics/engagement-trends?job_id=job_abc123&granularity=daily
```

**Response:**
```json
{
  "trends": [
    {
      "date": "2024-01-01",
      "posts": 45,
      "avg_score": 125.5,
      "comments": 230
    }
  ]
}
```

#### Get Sentiment Analysis
```http
GET /api/analytics/sentiment?job_id=job_abc123
```

**Response:**
```json
{
  "sentiment_distribution": [
    {"name": "positive", "value": 65.2},
    {"name": "neutral", "value": 28.1},
    {"name": "negative", "value": 6.7}
  ],
  "total_analyzed": 1500
}
```

### Billing (Paddle Integration)

#### Create Subscription
```http
POST /api/billing/subscription
```

**Request Body:**
```json
{
  "plan_id": "pro_monthly",
  "payment_method": "card"
}
```

#### Get Billing Portal URL
```http
GET /api/billing/portal
```

**Response:**
```json
{
  "portal_url": "https://billing.paddle.com/subscriptions/...",
  "expires_at": "2024-01-01T01:00:00Z"
}
```

### Health & Status

#### Health Check
```http
GET /health
```

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-01T00:00:00Z",
  "version": "1.0.0"
}
```

#### Database Health
```http
GET /health/db
```

#### Reddit API Health  
```http
GET /health/reddit
```

## Error Codes

| Code | Description |
|------|-------------|
| 400 | Bad Request - Invalid parameters |
| 401 | Unauthorized - Invalid or missing authentication |
| 403 | Forbidden - Insufficient permissions or quota exceeded |
| 404 | Not Found - Resource doesn't exist |
| 429 | Rate Limited - Too many requests |
| 500 | Internal Server Error - Unexpected server error |

## Error Response Format

```json
{
  "error": {
    "code": "INVALID_SUBREDDIT",
    "message": "The subreddit 'invalidname' does not exist or is private",
    "details": {
      "subreddit": "invalidname",
      "suggestions": ["python", "programming"]
    }
  },
  "request_id": "req_abc123"
}
```

## SDKs & Examples

### cURL Examples

**Create a collection job:**
```bash
curl -X POST "https://api.potterlabs.xyz/api/jobs" \
  -H "Authorization: Bearer tk_your_api_key" \
  -H "Content-Type: application/json" \
  -d '{
    "subreddits": ["python"],
    "sort_types": ["hot"],
    "post_limit": 50
  }'
```

**Search for posts:**
```bash
curl "https://api.potterlabs.xyz/api/scenarios/1/subreddit-keyword-search?subreddit=python&keywords=tutorial&date_from=2024-01-01&date_to=2024-12-31&limit=10" \
  -H "Authorization: Bearer tk_your_api_key"
```

### Python Example
```python
import requests

headers = {
    'Authorization': 'Bearer tk_your_api_key',
    'Content-Type': 'application/json'
}

# Create collection job
response = requests.post(
    'https://api.potterlabs.xyz/api/jobs',
    headers=headers,
    json={
        'subreddits': ['python'],
        'sort_types': ['hot'],
        'post_limit': 100
    }
)

job = response.json()
print(f"Created job: {job['job_id']}")
```

## Webhooks

### Job Completion Webhook
Configure webhook URL in your account settings to receive notifications when jobs complete.

**Payload:**
```json
{
  "event": "job.completed",
  "job_id": "job_abc123",
  "user_id": "user_456",
  "timestamp": "2024-01-01T00:15:30Z",
  "data": {
    "stats": {
      "posts_collected": 150,
      "comments_collected": 750
    }
  }
}
```
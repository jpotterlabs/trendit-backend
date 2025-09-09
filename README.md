# Trendit Backend API

FastAPI backend for the Trendit Reddit data collection platform. Provides REST API endpoints for authentication, data collection, analytics, and billing integration.

## 🚀 Quick Start

### Development Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Initialize database
python init_db.py

# Start development server
uvicorn main:app --reload --port 8000
```

### Testing

```bash
# Run all tests
python test_api.py

# Run specific test suites
python test_collection_api.py
python test_query_api.py

# Test single function
python -c "import asyncio; from test_api import test_reddit_connection; asyncio.run(test_reddit_connection())"
```

## 🏗️ Architecture

### Core Services
- **Authentication**: Auth0 OAuth integration + JWT tokens + API key auth
- **Data Collection**: Async Reddit API data gathering with PRAW/AsyncPRAW
- **Analytics**: Sentiment analysis and engagement metrics
- **Billing**: Paddle subscription management
- **Export**: Multi-format data export (CSV, JSON, Parquet)

### Database Schema
- **Users**: Auth0 integration, subscription status, usage tracking
- **Collection Jobs**: Async job status, parameters, progress
- **Reddit Data**: Posts, comments, metadata storage
- **API Keys**: User API key management with usage limits
- **Billing**: Subscription plans, payment tracking

## 🔑 Environment Configuration

Create `.env` file with these variables:

```bash
# Database
DATABASE_URL=postgresql://user:password@host:port/dbname?sslmode=require

# Reddit API
REDDIT_CLIENT_ID=your_reddit_client_id
REDDIT_CLIENT_SECRET=your_reddit_client_secret
REDDIT_USER_AGENT=Trendit/1.0 by /u/yourusername

# Auth0 Configuration
AUTH0_DOMAIN=your-domain.auth0.com
AUTH0_CLIENT_ID=your_auth0_client_id
AUTH0_CLIENT_SECRET=your_auth0_client_secret
AUTH0_AUDIENCE=https://api.potterlabs.xyz

# JWT Configuration
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=1440
JWT_ALGORITHM=HS256
JWT_SECRET_KEY=your_jwt_secret_key

# API Security
ADMIN_SECRET_KEY=your_admin_secret_key
API_KEY_SALT=your_api_key_salt

# Optional Integrations
OPENROUTER_API_KEY=your_openrouter_key
PADDLE_API_KEY=your_paddle_key
PADDLE_WEBHOOK_SECRET=your_paddle_webhook_secret
PADDLE_ENVIRONMENT=sandbox
```

## 📚 API Documentation

### Authentication

#### Admin Test User Endpoint
```bash
POST /auth/create-test-user
Content-Type: application/json

{
  "admin_key": "your_admin_secret_key"
}

# Response
{
  "user": {
    "email": "test@trendit.dev", 
    "password": "TestPassword123"
  },
  "api_key": "tk_abc123..."
}
```

#### JWT Authentication
```bash
POST /auth/login
Authorization: Bearer jwt_token_from_auth0
```

#### API Key Authentication
```bash
GET /api/any-endpoint
Authorization: Bearer tk_your_api_key
```

### Data Collection

#### Create Collection Job
```bash
POST /api/jobs
Authorization: Bearer your_token
Content-Type: application/json

{
  "subreddits": ["python", "javascript"],
  "sort_types": ["hot", "top"],
  "time_filters": ["week"],
  "post_limit": 100,
  "comment_limit": 50,
  "keywords": ["tutorial", "guide"]
}
```

#### Get Job Status
```bash
GET /api/jobs/{job_id}
Authorization: Bearer your_token
```

### Data Query

#### Subreddit Keyword Search
```bash
GET /api/scenarios/1/subreddit-keyword-search
  ?subreddit=python
  &keywords=tutorial
  &date_from=2024-01-01
  &date_to=2024-12-31
  &limit=100
Authorization: Bearer your_token
```

### Data Export

#### Export Job Data
```bash
POST /api/export/{job_id}
Authorization: Bearer your_token
Content-Type: application/json

{
  "format": "csv",
  "include_posts": true,
  "include_comments": true
}
```

## 🔧 Development

### Code Style
- Follow PEP 8, 88-character line length
- Use type hints and docstrings
- Async/await patterns with proper resource cleanup
- SQLAlchemy ORM with bulk operations
- Pydantic models for request/response validation

### Database Operations
```bash
# Initialize database
python init_db.py

# Reset database (caution!)
python -c "from models.database import reset_database; reset_database()"
```

### Testing Strategy
- Direct Python test files with async patterns
- Reddit API mocking for collection tests
- Auth0 JWT token validation testing
- Database testing with SQLAlchemy fixtures

## 🚀 Deployment

### Production URLs
- **API**: https://api.potterlabs.xyz
- **Frontend**: https://reddit.potterlabs.xyz

### Environment Variables
Set all environment variables in your hosting platform (Render, etc.)

### Health Check
```bash
curl https://api.potterlabs.xyz/health
# Should return: {"status": "healthy"}
```

## 🔐 Security

### Authentication Methods
1. **Auth0 JWT Tokens**: For frontend user authentication
2. **API Keys**: For programmatic access (format: `tk_...`)
3. **Admin Secret**: For administrative operations

### Rate Limiting
- Free tier: 100 API calls per month
- Usage tracked per user and API key
- Subscription-based limits enforced

### Security Best Practices
- All endpoints require authentication
- Input validation with Pydantic models
- SQL injection protection via SQLAlchemy ORM
- Secrets managed via environment variables

## 📊 Monitoring & Analytics

### Usage Tracking
- API call counts per user
- Job completion rates
- Performance metrics
- Error tracking

### Health Monitoring
```bash
GET /health        # Basic health check
GET /health/db     # Database connectivity
GET /health/reddit # Reddit API connectivity
```

## 🛠️ Troubleshooting

### Common Issues

**"Not authenticated" errors:**
1. Check API key format (must start with `tk_`)
2. Verify user has ACTIVE subscription
3. Check usage limits (free tier: 100 calls/month)

**Database connection errors:**
1. Verify DATABASE_URL format
2. Check database server accessibility
3. Confirm SSL mode settings

**Reddit API errors:**
1. Verify Reddit credentials
2. Check rate limiting
3. Validate subreddit names

### Debug Mode
```bash
# Enable debug logging
export LOG_LEVEL=DEBUG
uvicorn main:app --reload --log-level debug
```

## 📝 API Response Formats

### Success Response
```json
{
  "success": true,
  "data": { ... },
  "message": "Operation completed successfully"
}
```

### Error Response
```json
{
  "success": false,
  "error": "Error description",
  "code": "ERROR_CODE"
}
```

## 🤝 Contributing

1. Create feature branch from `main`
2. Follow code style guidelines
3. Add tests for new functionality
4. Update documentation
5. Submit pull request

## 📄 License

Copyright (c) 2024 Potter Labs. All rights reserved.
# Trendit Backend - FastAPI with Auth0 Integration

The backend API service for Trendit Reddit data collection platform with complete Auth0 OAuth integration.

## 🚀 Quick Start

```bash
# Setup virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Initialize database
python init_db.py

# Start the development server
uvicorn main:app --reload --port 8000
```

## 🔧 Configuration

Copy `.env.example` to `.env` and configure:

### Required Environment Variables
```bash
# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/trendit

# Reddit API
REDDIT_CLIENT_ID=your_reddit_client_id
REDDIT_CLIENT_SECRET=your_reddit_client_secret

# Auth0 Integration
AUTH0_DOMAIN=your-tenant.auth0.com
AUTH0_CLIENT_ID=your_auth0_client_id
AUTH0_CLIENT_SECRET=your_auth0_client_secret
AUTH0_AUDIENCE=https://trendit-api.com

# Security
JWT_SECRET_KEY=your-jwt-secret-key
API_KEY_SALT=your-api-key-salt
```

### Optional Environment Variables
```bash
# Billing System (Paddle)
PADDLE_API_KEY=your_paddle_api_key
PADDLE_WEBHOOK_SECRET=your_paddle_webhook_secret
PADDLE_PRO_PRICE_ID=your_pro_price_id
PADDLE_ENTERPRISE_PRICE_ID=your_enterprise_price_id

# AI Features
OPENROUTER_API_KEY=your_openrouter_api_key
```

## 🏗️ Architecture

### Core Services
- **Auth0Service**: JWT verification and user management
- **AsyncRedditClient**: Reddit API data collection
- **DataCollector**: High-level collection scenarios
- **PaddleService**: Subscription and billing management
- **AnalyticsService**: Data analysis and insights

### API Endpoints
- **Authentication** (`/auth`): JWT tokens, API keys, user management
- **Auth0 Integration** (`/auth0`): OAuth callback processing
- **Billing** (`/billing`): Subscription management via Paddle
- **Collection Jobs** (`/api/collect`): Background data collection
- **Data & Analytics** (`/api/data`): Query and analyze collected data
- **Export** (`/api/export`): Multi-format data export

## 🔐 Authentication

### Auth0 OAuth Flow
1. Frontend initiates OAuth with Auth0
2. User authenticates via Google/GitHub
3. Auth0 redirects to frontend with access token
4. Frontend sends access token to `/auth0/callback`
5. Backend verifies token with Auth0 and creates/updates user
6. Returns JWT token and API key for app usage

### Traditional Authentication
- Email/password registration and login
- JWT tokens for session management
- API keys for programmatic access

## 📊 Features

### Reddit Data Collection
- Subreddit post and comment collection
- Advanced filtering by date, score, keywords
- Real-time progress tracking
- Background job processing

### Subscription Management
- Multi-tier pricing (Free, Pro, Enterprise)
- Usage tracking and rate limiting
- Paddle payment processing
- Webhook-based subscription updates

### Data Analysis
- Sentiment analysis integration
- Engagement metrics and trends
- Advanced analytics queries
- Export to CSV, JSON, Parquet formats

## 🧪 Testing

```bash
# Run comprehensive test suite
python test_api.py

# Test specific components
python -c "import asyncio; from test_api import test_reddit_connection; asyncio.run(test_reddit_connection())"

# Test Auth0 integration
curl http://localhost:8000/auth0/health

# Test billing system
python -c "from services.paddle_service import PaddleService; print('Paddle configured')"
```

## 📦 Deployment

### Docker
```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Environment Setup
```bash
# Production environment variables
export DATABASE_URL="postgresql://..."
export AUTH0_DOMAIN="your-tenant.auth0.com"
export PADDLE_API_KEY="your-paddle-key"

# Start production server
uvicorn main:app --host 0.0.0.0 --port 8000
```

## 📚 Documentation

- [Auth0 Setup Guide](../frontend/trendit-frontend/AUTH0_SETUP_GUIDE.md)
- [Billing Integration](PADDLE_BILLING_INTEGRATION.md)
- [API Documentation](API_BILLING_REFERENCE.md)
- [Testing Guide](../backend/AGENTS.md)

## 🔒 Security

- JWT token verification with Auth0 JWKS
- API key authentication for programmatic access
- Paddle webhook signature verification
- Environment-based secret management
- CORS configuration for frontend domains

## 🆘 Support

For issues and questions:
1. Check environment variable configuration
2. Verify database connectivity
3. Test Auth0 integration endpoints
4. Review server logs for detailed error information

---

Built with FastAPI, SQLAlchemy, Auth0, and Paddle for maximum scalability and security.
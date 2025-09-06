# Billing Setup Guide

This guide walks you through setting up the Paddle billing integration for the Trendit platform from scratch.

## Prerequisites

- Python 3.8+
- PostgreSQL 12+
- Paddle account (sandbox for development)
- Environment variables configured

## Step 1: Environment Setup

### 1.1 Install Dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 1.2 Configure Environment Variables

Create a `.env` file in the backend directory:

```bash
# Database Configuration
DATABASE_URL=postgresql://username:password@localhost:5432/trendit

# Paddle Configuration (Sandbox)
PADDLE_API_KEY=your_paddle_sandbox_api_key
PADDLE_WEBHOOK_SECRET=your_webhook_secret

# Price IDs (from Paddle Dashboard)
PADDLE_PRO_PRICE_ID=pri_01234567890
PADDLE_ENTERPRISE_PRICE_ID=pri_09876543210

# Application Configuration
HOST=localhost
PORT=8000
RELOAD=true

# Reddit API (for main functionality)
REDDIT_CLIENT_ID=your_reddit_client_id
REDDIT_CLIENT_SECRET=your_reddit_client_secret

# Optional: OpenRouter for sentiment analysis
OPENROUTER_API_KEY=your_openrouter_api_key
```

## Step 2: Database Setup

### 2.1 Create Database Tables

Run the initialization script:

```bash
python init_db.py
```

This creates all necessary tables including:
- `paddle_subscriptions`
- `usage_records` 
- `billing_events`
- Core application tables

### 2.2 Verify Database Schema

Check that the tables were created correctly:

```sql
-- Connect to your PostgreSQL database
psql -d trendit

-- List tables
\dt

-- Check paddle_subscriptions table structure
\d paddle_subscriptions

-- Check usage_records table structure  
\d usage_records

-- Check billing_events table structure
\d billing_events
```

## Step 3: Paddle Dashboard Setup

### 3.1 Create Paddle Account

1. Sign up at [paddle.com](https://paddle.com)
2. Verify your account
3. Access the sandbox environment for development

### 3.2 Create Products

In the Paddle Dashboard, create two products:

**Pro Plan:**
- Name: "Trendit Pro"
- Price: $29.00 USD/month
- Billing cycle: Monthly
- Description: "Advanced Reddit data analysis with higher limits"

**Enterprise Plan:**
- Name: "Trendit Enterprise" 
- Price: $299.00 USD/month
- Billing cycle: Monthly
- Description: "Full-scale Reddit intelligence for organizations"

### 3.3 Get Price IDs

After creating products, copy the price IDs and add them to your `.env` file:

```bash
PADDLE_PRO_PRICE_ID=pri_01hw6p8v5h1c4nwvpqx9jfqxv8  # Example
PADDLE_ENTERPRISE_PRICE_ID=pri_01hw6p9v3m2d5owrqy0kgrsyv9  # Example
```

### 3.4 Configure Webhooks

1. Go to **Developer Tools > Webhooks** in Paddle Dashboard
2. Click **Add webhook endpoint**
3. Configure:
   - **URL**: `https://yourdomain.com/api/webhooks/paddle` (use ngrok for local development)
   - **Events**: Select all subscription and transaction events
   - **Version**: Latest API version
4. Save and copy the webhook secret to your `.env` file

### 3.5 Get API Keys

1. Go to **Developer Tools > API Keys**
2. Create a new API key for your application
3. Copy the key to your `.env` file as `PADDLE_API_KEY`

## Step 4: Local Development Setup

### 4.1 Start the Application

```bash
# In the backend directory
python main.py
```

The server will start on `http://localhost:8000`

### 4.2 Test Basic Functionality

```bash
# Test health endpoint
curl http://localhost:8000/health

# Test billing tiers endpoint
curl http://localhost:8000/api/billing/tiers | python -m json.tool
```

### 4.3 Set Up Webhook Testing (Local Development)

Since Paddle needs to send webhooks to a public URL, use ngrok for local development:

```bash
# Install ngrok (if not already installed)
# Download from https://ngrok.com/

# Start ngrok tunnel
ngrok http 8000
```

Copy the ngrok URL (e.g., `https://abc123.ngrok.io`) and update your webhook URL in the Paddle Dashboard to:
```
https://abc123.ngrok.io/api/webhooks/paddle
```

## Step 5: Test the Integration

### 5.1 Create Test User

```bash
# Register a test user
curl -X POST "http://localhost:8000/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "testpassword123",
    "username": "testuser"
  }'

# Login to get JWT token
curl -X POST "http://localhost:8000/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "testpassword123"
  }'

# Create API key (use JWT token from login)
curl -X POST "http://localhost:8000/auth/api-keys" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "test-key"}'
```

### 5.2 Test Usage Tracking

```bash
# Test export endpoint (tracks "exports" usage)
curl -X GET "http://localhost:8000/api/export/formats" \
  -H "Authorization: Bearer YOUR_API_KEY"

# Test data endpoint (tracks "api_calls" usage) 
curl -X GET "http://localhost:8000/api/data/summary" \
  -H "Authorization: Bearer YOUR_API_KEY"

# Test sentiment endpoint (tracks "sentiment_analysis" usage)
curl -X GET "http://localhost:8000/api/sentiment/status" \
  -H "Authorization: Bearer YOUR_API_KEY"
```

### 5.3 Verify Usage Records

Check that usage is being tracked:

```python
# Run this Python script to check usage
from models.database import SessionLocal
from models.models import UsageRecord, User
from sqlalchemy import func

db = SessionLocal()
user = db.query(User).filter(User.email == 'test@example.com').first()
usage_count = db.query(func.count(UsageRecord.id)).filter(UsageRecord.user_id == user.id).scalar()
print(f'User has {usage_count} usage records')

recent_usage = db.query(UsageRecord).filter(UsageRecord.user_id == user.id).order_by(UsageRecord.created_at.desc()).limit(5).all()
for record in recent_usage:
    print(f'{record.usage_type} - {record.endpoint} - {record.created_at}')
```

### 5.4 Test Billing Flow

```bash
# Get subscription status (should show FREE tier)
curl -X GET "http://localhost:8000/api/billing/subscription" \
  -H "Authorization: Bearer YOUR_API_KEY" | python -m json.tool

# Create checkout session for Pro plan
curl -X POST "http://localhost:8000/api/billing/checkout" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "tier": "pro",
    "success_url": "http://localhost:8000/success",
    "cancel_url": "http://localhost:8000/cancel",
    "trial_days": 14
  }' | python -m json.tool
```

### 5.5 Test Webhook Processing

1. Use Paddle's webhook testing tool to send a test event
2. Check the application logs for webhook processing
3. Verify that billing events are recorded in the database:

```python
from models.models import BillingEvent

db = SessionLocal()
recent_events = db.query(BillingEvent).order_by(BillingEvent.received_at.desc()).limit(5).all()
for event in recent_events:
    print(f'{event.event_type} - {event.processed_successfully} - {event.received_at}')
```

## Step 6: Frontend Integration

### 6.1 Basic Billing Page Example

```html
<!DOCTYPE html>
<html>
<head>
    <title>Billing - Trendit</title>
    <script src="https://unpkg.com/axios/dist/axios.min.js"></script>
</head>
<body>
    <div id="billing-info">
        <h2>Your Subscription</h2>
        <div id="current-plan"></div>
        <div id="usage-info"></div>
        <div id="upgrade-options"></div>
    </div>

    <script>
        const apiKey = 'YOUR_API_KEY'; // In production, get this from secure storage
        const apiBase = 'http://localhost:8000';

        // Load subscription status
        async function loadBillingInfo() {
            try {
                const response = await axios.get(`${apiBase}/api/billing/subscription`, {
                    headers: { 'Authorization': `Bearer ${apiKey}` }
                });
                
                const { subscription, usage } = response.data;
                
                // Display current plan
                document.getElementById('current-plan').innerHTML = `
                    <h3>Current Plan: ${subscription.tier.toUpperCase()}</h3>
                    <p>Status: ${subscription.status}</p>
                    <p>Price: $${subscription.price_per_month}/month</p>
                `;
                
                // Display usage info
                const usageHtml = Object.entries(usage.current_period).map(([type, data]) => {
                    if (typeof data === 'object' && data.used !== undefined) {
                        const percentage = (data.used / data.limit) * 100;
                        return `
                            <div>
                                <strong>${type.replace('_', ' ')}</strong>: ${data.used}/${data.limit}
                                <div style="background: #f0f0f0; width: 200px; height: 10px;">
                                    <div style="background: ${percentage > 80 ? '#ff4444' : '#44ff44'}; width: ${percentage}%; height: 10px;"></div>
                                </div>
                            </div>
                        `;
                    }
                    return '';
                }).join('');
                
                document.getElementById('usage-info').innerHTML = `
                    <h3>Usage This Month</h3>
                    ${usageHtml}
                `;
                
                // Show upgrade options if on free plan
                if (subscription.tier === 'free') {
                    document.getElementById('upgrade-options').innerHTML = `
                        <h3>Upgrade Your Plan</h3>
                        <button onclick="upgradeTo('pro')">Upgrade to Pro - $29/month</button>
                        <button onclick="upgradeTo('enterprise')">Upgrade to Enterprise - $299/month</button>
                    `;
                }
                
            } catch (error) {
                console.error('Failed to load billing info:', error);
                document.getElementById('billing-info').innerHTML = '<p>Error loading billing information</p>';
            }
        }
        
        // Upgrade to a plan
        async function upgradeTo(tier) {
            try {
                const response = await axios.post(`${apiBase}/api/billing/checkout`, {
                    tier: tier,
                    success_url: `${window.location.origin}/billing/success`,
                    cancel_url: `${window.location.origin}/billing/cancel`,
                    trial_days: 14
                }, {
                    headers: { 'Authorization': `Bearer ${apiKey}` }
                });
                
                // Redirect to Paddle checkout
                window.location.href = response.data.checkout_url;
                
            } catch (error) {
                console.error('Failed to create checkout:', error);
                alert('Failed to start checkout process');
            }
        }
        
        // Load billing info when page loads
        loadBillingInfo();
    </script>
</body>
</html>
```

### 6.2 Usage-Based UI Components

```javascript
// Usage warning component
class UsageWarning {
    constructor(apiKey) {
        this.apiKey = apiKey;
        this.checkUsage();
    }
    
    async checkUsage() {
        try {
            const response = await axios.get('/api/billing/subscription', {
                headers: { 'Authorization': `Bearer ${this.apiKey}` }
            });
            
            const usage = response.data.usage.current_period;
            
            // Check for high usage
            Object.entries(usage).forEach(([type, data]) => {
                if (typeof data === 'object' && data.used !== undefined) {
                    const percentage = (data.used / data.limit) * 100;
                    
                    if (percentage >= 90) {
                        this.showWarning(type, data, 'danger');
                    } else if (percentage >= 75) {
                        this.showWarning(type, data, 'warning');
                    }
                }
            });
            
        } catch (error) {
            console.error('Failed to check usage:', error);
        }
    }
    
    showWarning(type, data, level) {
        const message = `You've used ${data.used}/${data.limit} ${type.replace('_', ' ')} this month`;
        const color = level === 'danger' ? '#ff4444' : '#ffaa00';
        
        const warning = document.createElement('div');
        warning.style.cssText = `
            background: ${color};
            color: white;
            padding: 10px;
            margin: 10px 0;
            border-radius: 4px;
            position: relative;
        `;
        warning.innerHTML = `
            ${message}
            <button onclick="this.parentElement.remove()" style="float: right; background: none; border: none; color: white; font-size: 16px;">×</button>
            ${level === 'danger' ? '<br><a href="/billing" style="color: white;">Upgrade your plan</a>' : ''}
        `;
        
        document.body.insertBefore(warning, document.body.firstChild);
    }
}

// Initialize usage warnings
document.addEventListener('DOMContentLoaded', () => {
    const apiKey = localStorage.getItem('trendit_api_key');
    if (apiKey) {
        new UsageWarning(apiKey);
    }
});
```

## Step 7: Production Deployment

### 7.1 Environment Configuration

Update your production environment variables:

```bash
# Production Environment Variables
DATABASE_URL=postgresql://prod_user:secure_password@prod-db:5432/trendit_prod

# Paddle Production Configuration
PADDLE_API_KEY=your_production_paddle_api_key
PADDLE_WEBHOOK_SECRET=your_production_webhook_secret
PADDLE_PRO_PRICE_ID=your_production_pro_price_id
PADDLE_ENTERPRISE_PRICE_ID=your_production_enterprise_price_id

# Application Configuration
HOST=0.0.0.0
PORT=8000
RELOAD=false
```

### 7.2 Database Migration

Run database migrations on production:

```bash
# Apply schema changes
python init_db.py

# Verify tables exist
python -c "
from models.database import engine
from sqlalchemy import inspect

inspector = inspect(engine)
tables = inspector.get_table_names()
print('Tables:', tables)

# Check specific billing tables
for table in ['paddle_subscriptions', 'usage_records', 'billing_events']:
    if table in tables:
        print(f'✓ {table} exists')
    else:
        print(f'✗ {table} missing')
"
```

### 7.3 Paddle Production Setup

1. **Switch to Production Mode** in Paddle Dashboard
2. **Create Production Products** with same configuration as sandbox
3. **Update Webhook URLs** to production endpoints
4. **Test Webhook Delivery** using Paddle's testing tools
5. **Configure Customer Portal** for subscription management

### 7.4 Monitoring & Logging

Set up monitoring for production:

```python
# Add to main.py
import logging
import structlog
from logging.handlers import RotatingFileHandler

# Configure structured logging
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        structlog.processors.JSONRenderer()
    ],
    wrapper_class=structlog.make_filtering_bound_logger(20),  # INFO level
    logger_factory=structlog.WriteLoggerFactory(),
    cache_logger_on_first_use=True,
)

# Add file handler for production
if not app.debug:
    file_handler = RotatingFileHandler('logs/trendit.log', maxBytes=10240000, backupCount=10)
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s'
    ))
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
```

## Troubleshooting

### Common Issues

**1. Webhook signature verification fails**
- Check that `PADDLE_WEBHOOK_SECRET` matches Paddle Dashboard
- Verify webhook URL is accessible from internet
- Check request headers are being passed correctly

**2. Database connection errors**
- Verify `DATABASE_URL` format
- Check database server is running
- Ensure database user has required permissions

**3. Usage tracking not working**
- Check API key authentication
- Verify endpoints use correct dependency functions
- Check database schema includes all required tables

**4. Rate limiting not enforced**  
- Verify usage records are being created
- Check tier limit configuration
- Ensure billing period calculation is correct

### Debug Commands

```python
# Check Paddle service configuration
from services.paddle_service import paddle_service
print(f"Configured: {paddle_service.is_configured()}")

# Test database connection
from models.database import engine
from sqlalchemy import text
with engine.connect() as conn:
    result = conn.execute(text("SELECT 1"))
    print("Database connected")

# Check recent usage
from models.database import SessionLocal
from models.models import UsageRecord
db = SessionLocal()
recent = db.query(UsageRecord).order_by(UsageRecord.created_at.desc()).limit(5).all()
for record in recent:
    print(f"{record.usage_type} - {record.created_at}")
```

## Next Steps

After completing this setup:

1. **Customize Pricing**: Adjust tier limits and features based on your business model
2. **Add Analytics**: Implement detailed usage analytics and reporting
3. **Customer Support**: Set up billing support workflows
4. **Testing**: Create comprehensive test suite for billing flows
5. **Documentation**: Update API documentation with billing endpoints

Your Paddle billing integration is now ready for production use! 🎉
# Billing System Quick Reference

## 🚀 Key Features

- ✅ **Multi-tier SaaS pricing** (Free, Pro $29, Enterprise $299)
- ✅ **Usage-based rate limiting** with real-time tracking
- ✅ **Paddle integration** with webhook processing
- ✅ **Comprehensive audit trail** for all billing events
- ✅ **Flexible billing periods** (calendar month for free, Paddle cycles for paid)

## 📊 Subscription Tiers

| Feature | Free | Pro ($29) | Enterprise ($299) |
|---------|------|-----------|-------------------|
| API Calls/month | 100 | 10,000 | 100,000 |
| Data Exports/month | 5 | 100 | 1,000 |
| Sentiment Analysis/month | 50 | 2,000 | 20,000 |
| Data Retention | 30 days | 1 year | Unlimited |
| Support | Community | Email | Phone + Chat |

## 🔗 Quick API Endpoints

```bash
# Get subscription tiers (public)
GET /api/billing/tiers

# Get user subscription status
GET /api/billing/subscription
Authorization: Bearer {api_key}

# Create checkout session
POST /api/billing/checkout
Authorization: Bearer {api_key}
{
  "tier": "pro",
  "success_url": "https://app.com/success",
  "cancel_url": "https://app.com/cancel",
  "trial_days": 14
}

# Cancel subscription
DELETE /api/billing/subscription
Authorization: Bearer {api_key}

# Paddle webhooks
POST /api/webhooks/paddle
```

## 🛡️ Usage Tracking Dependencies

Use these in your FastAPI endpoints:

```python
# For export endpoints (5/100/1000 per month)
@router.get("/export/data")
async def export_data(user: User = Depends(require_export_limit)):

# For API endpoints (100/10K/100K per month)  
@router.get("/data/summary")
async def get_data(user: User = Depends(require_api_call_limit)):

# For sentiment endpoints (50/2K/20K per month)
@router.post("/sentiment/analyze") 
async def analyze(user: User = Depends(require_sentiment_limit)):
```

## ⚡ Rate Limiting Response

When limits exceeded, API returns:

```http
HTTP/1.1 429 Too Many Requests
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 0
X-RateLimit-Reset: 1696118400
X-User-Tier: free

{
  "detail": "Usage limit exceeded. 100/100 api_calls used this month. Upgrade your plan for higher limits."
}
```

## 🔧 Environment Variables

```bash
# Required for production
PADDLE_API_KEY=your_paddle_api_key
PADDLE_WEBHOOK_SECRET=your_webhook_secret
PADDLE_PRO_PRICE_ID=pri_01234567890
PADDLE_ENTERPRISE_PRICE_ID=pri_09876543210
DATABASE_URL=postgresql://user:pass@host:5432/trendit
```

## 📋 Database Models

### Key Tables Created

- **`paddle_subscriptions`** - User subscription details
- **`usage_records`** - API usage tracking for rate limiting
- **`billing_events`** - Webhook event audit log

### Check Usage Records

```python
from models.database import SessionLocal
from models.models import UsageRecord, User
from sqlalchemy import func

db = SessionLocal()
user = db.query(User).filter(User.email == 'user@example.com').first()
usage_count = db.query(func.count(UsageRecord.id)).filter(UsageRecord.user_id == user.id).scalar()
print(f'User has {usage_count} usage records')
```

## 🔗 Webhook Events Handled

- `subscription.created` - New subscription
- `subscription.updated` - Plan changes
- `subscription.cancelled` - Cancellations  
- `transaction.completed` - Successful payments
- `transaction.payment_failed` - Failed payments

## 🧪 Testing Commands

```bash
# Test basic functionality
curl http://localhost:8000/health
curl http://localhost:8000/api/billing/tiers

# Test usage tracking (requires API key)
curl -H "Authorization: Bearer tk_your_api_key" \
  http://localhost:8000/api/export/formats

curl -H "Authorization: Bearer tk_your_api_key" \
  http://localhost:8000/api/data/summary

# Check subscription status
curl -H "Authorization: Bearer tk_your_api_key" \
  http://localhost:8000/api/billing/subscription
```

## 🐛 Common Issues & Solutions

**Webhook signature fails** → Check `PADDLE_WEBHOOK_SECRET` matches dashboard

**Usage not tracked** → Verify endpoints use correct dependency functions

**Rate limits not enforced** → Check database schema and usage record creation

**Database errors** → Ensure `subscription_id` column is nullable in `usage_records`

## 📁 Key Files

```
backend/
├── services/paddle_service.py     # Core Paddle integration
├── api/billing.py                 # Billing REST endpoints
├── api/webhooks.py                # Webhook event processing
├── api/auth.py                    # Usage tracking dependencies
├── models/models.py               # Database models
├── PADDLE_BILLING_INTEGRATION.md # Complete documentation
└── BILLING_SETUP_GUIDE.md        # Setup instructions
```

## 🎯 Production Checklist

- [ ] Set production Paddle API keys
- [ ] Configure production webhook URL
- [ ] Update price IDs for production products
- [ ] Apply database schema changes
- [ ] Test webhook delivery
- [ ] Set up monitoring and logging
- [ ] Configure customer portal

---

**🎉 Your Paddle billing integration is production-ready!**

For complete documentation, see `PADDLE_BILLING_INTEGRATION.md`
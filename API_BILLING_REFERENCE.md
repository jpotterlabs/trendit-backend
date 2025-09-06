# Billing API Reference

## Overview

This document provides a complete API reference for the Paddle billing integration endpoints in the Trendit platform.

## Base URL

```
http://localhost:8000  # Development
https://api.trendit.com  # Production
```

## Authentication

All billing endpoints require authentication using an API key:

```http
Authorization: Bearer tk_your_api_key_here
```

## Endpoints

### Public Endpoints

#### Get Subscription Tiers

Get information about available subscription tiers and their features.

```http
GET /api/billing/tiers
```

**Response:**
```json
{
  "tiers": {
    "free": {
      "name": "Free",
      "price": 0,
      "currency": "USD",
      "interval": "month",
      "features": [
        "100 API calls per month",
        "5 data exports per month",
        "50 sentiment analyses per month",
        "30-day data retention",
        "Community support"
      ],
      "limits": {
        "api_calls_per_month": 100,
        "exports_per_month": 5,
        "sentiment_analysis_per_month": 50,
        "data_retention_days": 30
      }
    },
    "pro": {
      "name": "Pro",
      "price": 29,
      "currency": "USD",
      "interval": "month",
      "features": [
        "10,000 API calls per month",
        "100 data exports per month",
        "2,000 sentiment analyses per month",
        "1-year data retention",
        "Priority email support",
        "Advanced analytics"
      ],
      "limits": {
        "api_calls_per_month": 10000,
        "exports_per_month": 100,
        "sentiment_analysis_per_month": 2000,
        "data_retention_days": 365
      }
    },
    "enterprise": {
      "name": "Enterprise",
      "price": 299,
      "currency": "USD",
      "interval": "month",
      "features": [
        "100,000 API calls per month",
        "1,000 data exports per month",
        "20,000 sentiment analyses per month",
        "Unlimited data retention",
        "Phone & chat support",
        "Custom integrations",
        "Dedicated account manager"
      ],
      "limits": {
        "api_calls_per_month": 100000,
        "exports_per_month": 1000,
        "sentiment_analysis_per_month": 20000,
        "data_retention_days": -1
      }
    }
  }
}
```

### User Subscription Endpoints

#### Get User Subscription Status

Get the current user's subscription status and usage information.

```http
GET /api/billing/subscription
Authorization: Bearer {api_key}
```

**Response (Active Subscription):**
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
    "trial_end_date": null,
    "customer_portal_url": "https://customer-portal.paddle.com/subscriptions?token=abc123"
  },
  "usage": {
    "current_period": {
      "start_date": "2025-09-01T00:00:00Z",
      "end_date": "2025-10-01T00:00:00Z",
      "api_calls": {
        "used": 156,
        "limit": 10000,
        "remaining": 9844
      },
      "exports": {
        "used": 3,
        "limit": 100,
        "remaining": 97
      },
      "sentiment_analysis": {
        "used": 24,
        "limit": 2000,
        "remaining": 1976
      }
    },
    "daily_usage": [
      {
        "date": "2025-09-01",
        "api_calls": 45,
        "exports": 2,
        "sentiment_analysis": 12
      },
      {
        "date": "2025-08-31",
        "api_calls": 67,
        "exports": 1,
        "sentiment_analysis": 8
      }
    ]
  }
}
```

**Response (Free User):**
```json
{
  "subscription": {
    "tier": "free",
    "status": "inactive",
    "current_period_start": "2025-09-01T00:00:00Z",
    "current_period_end": "2025-10-01T00:00:00Z",
    "next_billed_at": null,
    "price_per_month": 0,
    "currency": "USD",
    "is_trial": false,
    "trial_end_date": null,
    "customer_portal_url": null
  },
  "usage": {
    "current_period": {
      "start_date": "2025-09-01T00:00:00Z",
      "end_date": "2025-10-01T00:00:00Z",
      "api_calls": {
        "used": 23,
        "limit": 100,
        "remaining": 77
      },
      "exports": {
        "used": 1,
        "limit": 5,
        "remaining": 4
      },
      "sentiment_analysis": {
        "used": 8,
        "limit": 50,
        "remaining": 42
      }
    }
  }
}
```

#### Create Checkout Session

Create a Paddle checkout session for subscription upgrade.

```http
POST /api/billing/checkout
Authorization: Bearer {api_key}
Content-Type: application/json

{
  "tier": "pro",
  "success_url": "https://yourapp.com/billing/success",
  "cancel_url": "https://yourapp.com/billing/cancel",
  "trial_days": 14
}
```

**Request Parameters:**
- `tier` (string, required): Target subscription tier ("pro" or "enterprise")
- `success_url` (string, required): URL to redirect after successful payment
- `cancel_url` (string, required): URL to redirect if payment is cancelled
- `trial_days` (integer, optional): Number of trial days to offer

**Response:**
```json
{
  "checkout_url": "https://pay.paddle.com/checkout?_ptxn=txn_01234567890",
  "tier": "pro",
  "trial_days": 14,
  "expires_at": "2025-09-01T12:00:00Z"
}
```

**Error Response (Invalid Tier):**
```json
{
  "detail": "Invalid tier: premium. Valid tiers are: pro, enterprise"
}
```

#### Update Subscription

Upgrade or downgrade the user's subscription.

```http
PUT /api/billing/subscription
Authorization: Bearer {api_key}
Content-Type: application/json

{
  "new_tier": "enterprise"
}
```

**Request Parameters:**
- `new_tier` (string, required): Target tier ("pro", "enterprise", or "free")

**Response:**
```json
{
  "message": "Subscription updated successfully",
  "subscription": {
    "tier": "enterprise",
    "status": "active",
    "price_per_month": 299.0,
    "currency": "USD",
    "effective_date": "2025-09-01T12:00:00Z",
    "prorated_credit": 12.45
  }
}
```

**Error Response (Downgrade Not Allowed):**
```json
{
  "detail": "Cannot downgrade subscription during trial period"
}
```

#### Cancel Subscription

Cancel the user's subscription (effective at end of billing period).

```http
DELETE /api/billing/subscription
Authorization: Bearer {api_key}
```

**Response:**
```json
{
  "message": "Subscription cancelled successfully",
  "cancellation": {
    "effective_date": "2025-10-01T00:00:00Z",
    "access_until": "2025-10-01T00:00:00Z",
    "refund_amount": 0,
    "reason": "user_requested"
  }
}
```

#### Get Usage Analytics

Get detailed usage analytics for the current billing period.

```http
GET /api/billing/usage
Authorization: Bearer {api_key}
```

**Query Parameters:**
- `days` (integer, optional): Number of days to include in daily breakdown (default: 30)

**Response:**
```json
{
  "current_period": {
    "start_date": "2025-09-01T00:00:00Z",
    "end_date": "2025-10-01T00:00:00Z",
    "days_remaining": 24,
    "total_usage": {
      "api_calls": 156,
      "exports": 3,
      "sentiment_analysis": 24
    },
    "limits": {
      "api_calls": 10000,
      "exports": 100,
      "sentiment_analysis": 2000
    },
    "usage_percentage": {
      "api_calls": 1.56,
      "exports": 3.0,
      "sentiment_analysis": 1.2
    }
  },
  "daily_breakdown": [
    {
      "date": "2025-09-01",
      "api_calls": 45,
      "exports": 2,
      "sentiment_analysis": 12
    },
    {
      "date": "2025-08-31",
      "api_calls": 67,
      "exports": 1,
      "sentiment_analysis": 8
    }
  ],
  "trending": {
    "api_calls": {
      "daily_average": 22.3,
      "trend": "increasing",
      "projected_monthly": 690
    },
    "exports": {
      "daily_average": 0.4,
      "trend": "stable",
      "projected_monthly": 12
    },
    "sentiment_analysis": {
      "daily_average": 3.4,
      "trend": "increasing",
      "projected_monthly": 105
    }
  }
}
```

### Webhook Endpoint

#### Paddle Webhook Handler

Receives and processes Paddle webhook events.

```http
POST /api/webhooks/paddle
Content-Type: application/json
Paddle-Signature: ts=1693526400,h1=abc123def456...
Paddle-Timestamp: 1693526400

{
  "event_id": "evt_01234567890",
  "event_type": "subscription.created",
  "occurred_at": "2025-09-01T10:00:00Z",
  "data": {
    "id": "sub_01234567890",
    "customer_id": "ctm_01234567890",
    "status": "active",
    "items": [
      {
        "price": {
          "id": "pri_01234567890",
          "description": "Trendit Pro Plan",
          "unit_price": {
            "amount": "2900",
            "currency_code": "USD"
          }
        },
        "quantity": 1
      }
    ],
    "billing_cycle": {
      "interval": "month",
      "frequency": 1
    },
    "current_billing_period": {
      "starts_at": "2025-09-01T00:00:00Z",
      "ends_at": "2025-10-01T00:00:00Z"
    },
    "next_billed_at": "2025-10-01T00:00:00Z"
  }
}
```

**Response:**
```json
{
  "received": true,
  "event_id": "evt_01234567890",
  "processed": true
}
```

## Rate Limiting Headers

All API responses include rate limiting information in headers:

```http
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 77
X-RateLimit-Reset: 1696118400
X-User-Tier: free
```

## Error Responses

### Rate Limit Exceeded

```http
HTTP/1.1 429 Too Many Requests
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 0
X-RateLimit-Reset: 1696118400
X-User-Tier: free
Content-Type: application/json

{
  "detail": "Usage limit exceeded. 100/100 api_calls used this month. Upgrade your plan for higher limits.",
  "error_code": "RATE_LIMIT_EXCEEDED",
  "upgrade_url": "/api/billing/checkout"
}
```

### Payment Required

```http
HTTP/1.1 402 Payment Required
Content-Type: application/json

{
  "detail": "Active subscription required to access this endpoint",
  "error_code": "SUBSCRIPTION_REQUIRED",
  "available_plans": ["pro", "enterprise"],
  "upgrade_url": "/api/billing/checkout"
}
```

### Invalid Subscription Tier

```http
HTTP/1.1 400 Bad Request
Content-Type: application/json

{
  "detail": "Invalid tier: premium. Valid tiers are: pro, enterprise",
  "error_code": "INVALID_TIER"
}
```

### Webhook Signature Invalid

```http
HTTP/1.1 401 Unauthorized
Content-Type: application/json

{
  "detail": "Invalid webhook signature",
  "error_code": "INVALID_SIGNATURE"
}
```

## Usage Examples

### JavaScript/TypeScript

```javascript
// Create checkout session
const createCheckout = async (tier, trialDays = null) => {
  const response = await fetch('/api/billing/checkout', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${apiKey}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      tier,
      success_url: `${window.location.origin}/billing/success`,
      cancel_url: `${window.location.origin}/billing/cancel`,
      trial_days: trialDays
    })
  });
  
  const { checkout_url } = await response.json();
  window.location.href = checkout_url;
};

// Get subscription status
const getSubscriptionStatus = async () => {
  const response = await fetch('/api/billing/subscription', {
    headers: {
      'Authorization': `Bearer ${apiKey}`
    }
  });
  
  return await response.json();
};

// Check usage and show upgrade prompt if needed
const checkUsageLimit = async () => {
  try {
    const response = await fetch('/api/export/formats', {
      headers: {
        'Authorization': `Bearer ${apiKey}`
      }
    });
    
    if (response.status === 429) {
      const error = await response.json();
      showUpgradeModal(error.detail);
    }
  } catch (error) {
    console.error('API request failed:', error);
  }
};
```

### Python

```python
import httpx

class TrenditBillingClient:
    def __init__(self, api_key: str, base_url: str = "https://api.trendit.com"):
        self.api_key = api_key
        self.base_url = base_url
        self.headers = {"Authorization": f"Bearer {api_key}"}
    
    async def get_subscription_status(self):
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/api/billing/subscription",
                headers=self.headers
            )
            response.raise_for_status()
            return response.json()
    
    async def create_checkout(self, tier: str, success_url: str, cancel_url: str, trial_days: int = None):
        payload = {
            "tier": tier,
            "success_url": success_url,
            "cancel_url": cancel_url
        }
        if trial_days:
            payload["trial_days"] = trial_days
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/api/billing/checkout",
                headers=self.headers,
                json=payload
            )
            response.raise_for_status()
            return response.json()
    
    async def cancel_subscription(self):
        async with httpx.AsyncClient() as client:
            response = await client.delete(
                f"{self.base_url}/api/billing/subscription",
                headers=self.headers
            )
            response.raise_for_status()
            return response.json()

# Usage
client = TrenditBillingClient("tk_your_api_key")
status = await client.get_subscription_status()
print(f"Current tier: {status['subscription']['tier']}")
```

### curl

```bash
# Get subscription tiers
curl -X GET "https://api.trendit.com/api/billing/tiers"

# Get user subscription status
curl -X GET "https://api.trendit.com/api/billing/subscription" \
  -H "Authorization: Bearer tk_your_api_key"

# Create checkout session for Pro plan with trial
curl -X POST "https://api.trendit.com/api/billing/checkout" \
  -H "Authorization: Bearer tk_your_api_key" \
  -H "Content-Type: application/json" \
  -d '{
    "tier": "pro",
    "success_url": "https://yourapp.com/success",
    "cancel_url": "https://yourapp.com/cancel",
    "trial_days": 14
  }'

# Cancel subscription
curl -X DELETE "https://api.trendit.com/api/billing/subscription" \
  -H "Authorization: Bearer tk_your_api_key"
```

## Webhook Integration

### Setting up Webhooks

1. **Configure Webhook URL** in Paddle Dashboard:
   ```
   https://yourdomain.com/api/webhooks/paddle
   ```

2. **Select Events** to receive:
   - `subscription.created`
   - `subscription.updated`
   - `subscription.cancelled`
   - `transaction.completed`
   - `transaction.payment_failed`

3. **Test Webhook Delivery** using Paddle's webhook testing tools

### Webhook Event Examples

**Subscription Created:**
```json
{
  "event_type": "subscription.created",
  "data": {
    "id": "sub_01234567890",
    "status": "active",
    "customer_id": "ctm_01234567890",
    "billing_cycle": {
      "interval": "month",
      "frequency": 1
    },
    "current_billing_period": {
      "starts_at": "2025-09-01T00:00:00Z",
      "ends_at": "2025-10-01T00:00:00Z"
    }
  }
}
```

**Payment Failed:**
```json
{
  "event_type": "transaction.payment_failed",
  "data": {
    "id": "txn_01234567890",
    "status": "billed",
    "customer_id": "ctm_01234567890",
    "subscription_id": "sub_01234567890",
    "billing_details": {
      "payment_attempts": 2,
      "next_retry_at": "2025-09-03T10:00:00Z"
    }
  }
}
```

This API reference provides complete documentation for integrating with the Trendit billing system using the Paddle payment processor.
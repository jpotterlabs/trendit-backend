# Rate Limiting Implementation

This document describes the improved rate limiting system implemented for dashboard burst protection.

## Problem Statement

The original rate limiting system had a critical flaw: dashboard requests were sampled (only every 5th request was written to the database) to reduce write load, but burst limit checks used the same sampled data. This resulted in undercounting actual requests, allowing users to exceed burst limits.

## Solution

Implemented a dual-layer rate limiting system:

1. **Burst Limiting**: Redis-based sliding window counter for accurate short-term tracking
2. **Monthly Accounting**: Existing database sampling for long-term usage tracking

## Architecture

### Redis-Based Burst Limiting

- **Storage**: Redis sorted sets with timestamp scoring
- **Window**: 5-minute sliding window
- **Limit**: 20 requests per 5 minutes (4 req/min average)
- **Fallback**: In-memory storage if Redis unavailable

### Components

#### `services/rate_limiter.py`
- `RateLimiter` class with Redis and in-memory implementations
- Sliding window counter using Redis sorted sets
- Atomic operations with proper TTL handling
- Graceful fallback to in-memory storage

#### Integration in `api/auth.py`
- `check_dashboard_burst_limit()`: Check if request allowed
- `record_dashboard_request()`: Record request in sliding window
- Preserves existing HTTPException behavior and headers

## Usage

### Dashboard Endpoints
Automatically applied to these endpoints:
- `general_api`
- `data_summary` 
- `jobs_list`
- `subscription_status`

### Environment Configuration

```bash
# Optional Redis configuration (falls back to in-memory)
REDIS_URL=redis://localhost:6379/0
# OR
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
```

### Rate Limit Headers

When burst limit is exceeded:
```
X-RateLimit-Type: burst
X-RateLimit-Window: 5_minutes
X-RateLimit-Current: 20
X-RateLimit-Limit: 20
Retry-After: 60
```

## Implementation Details

### Redis Sliding Window

1. **Check Limit**: Query sorted set for entries in current window
2. **Record Request**: Add timestamp to sorted set with TTL
3. **Cleanup**: Remove expired entries atomically
4. **Atomic Operations**: Use Redis pipelines for consistency

### In-Memory Fallback

1. **Thread-Safe**: Protected with threading.Lock
2. **Sliding Window**: Collections.deque with timestamp filtering
3. **Cleanup**: Periodic cleanup of expired entries
4. **Memory Efficient**: Automatic removal of empty queues

### Database Sampling Preserved

- Monthly usage tracking continues with existing 1:5 sampling ratio
- Only burst limiting uses accurate per-request tracking
- No impact on database write performance

## Benefits

1. **Accurate Burst Protection**: Every dashboard request counted
2. **Performance**: Redis operations are fast and atomic
3. **Reliability**: Graceful fallback to in-memory storage
4. **Compatibility**: Preserves existing API and error handling
5. **Scalability**: Redis allows horizontal scaling

## Monitoring

### Redis Monitoring
- Monitor Redis memory usage for rate limit data
- Keys auto-expire after window (5 minutes)
- Pattern: `burst:{user_id}:{endpoint}`

### Application Logs
- Rate limiter initialization (Redis vs in-memory)
- Burst limit violations with user/endpoint details
- Redis connection failures (falls back gracefully)

## Testing

### Unit Tests
Test cases should cover:
- Redis sliding window accuracy
- In-memory fallback functionality
- Atomic operations and race conditions
- TTL and cleanup behavior

### Integration Tests
- Dashboard burst limit enforcement
- Monthly limit preservation
- Error handling and fallback scenarios
- Multi-user concurrent access

## Future Enhancements

1. **Distributed Rate Limiting**: Redis Cluster support
2. **Dynamic Limits**: Per-user or per-tier burst limits
3. **Analytics**: Rate limit violation tracking and alerting
4. **Admin Interface**: Real-time rate limit monitoring
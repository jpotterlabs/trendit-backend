# Trendit API - cURL Examples

Complete collection of cURL examples for all Trendit API endpoints.

## Authentication - Getting Started

### 🔐 Step 1: Register a New User
```bash
# Register with username, email, and password
curl -X POST "http://localhost:8000/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "myusername",
    "email": "user@example.com", 
    "password": "securepassword123"
  }' | python -m json.tool
```

### 🔑 Step 2: Login to Get Bearer Token
```bash
# Login to get JWT Bearer token
curl -X POST "http://localhost:8000/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com", 
    "password": "securepassword123"
  }' | python -m json.tool

# Returns: {"access_token": "eyJ0eXAi...", "token_type": "bearer"}
```

### 🗝️ Step 3: Create API Key (Optional but Recommended)
```bash
# Create API key using JWT token (replace YOUR_JWT_TOKEN_HERE)
curl -X POST "http://localhost:8000/auth/api-keys" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN_HERE" \
  -H "Content-Type: application/json" \
  -d '{"name": "My API Key"}' | python -m json.tool

# Returns: {"id": 1, "name": "My API Key", "key": "tk_abc123...", "created_at": "..."}
```

### 📋 Authentication Requirements
**All endpoints below require authentication using your Bearer token:**
```bash
-H "Authorization: Bearer YOUR_JWT_TOKEN_OR_API_KEY"
```

**Free Tier Limits (no subscription required):**
- 🔢 **100 API calls per month**
- 📤 **5 exports per month**  
- 🧠 **50 sentiment analyses per month**

---

## Core Endpoints

### Health Check
```bash
# Basic health check
curl -X GET "http://localhost:8000/health"

# Health check with formatted output
curl -s "http://localhost:8000/health" | python -m json.tool
```

### API Information
```bash
# Get API info and features
curl -X GET "http://localhost:8000/"

# Get just the scenarios list
curl -s "http://localhost:8000/" | python -c "import sys,json; data=json.load(sys.stdin); print(json.dumps(data['scenarios'], indent=2))"
```

## Scenarios API - Quickstart Examples

### Scenario 1: Subreddit Keyword Search
```bash
# Basic keyword search
curl -X GET "http://localhost:8000/api/scenarios/1/subreddit-keyword-search?subreddit=python&keywords=fastapi&date_from=2024-01-01&date_to=2024-12-31&limit=5" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"

# Multiple keywords
curl -X GET "http://localhost:8000/api/scenarios/1/subreddit-keyword-search?subreddit=programming&keywords=python,django,flask&date_from=2024-06-01&date_to=2024-12-31&limit=10&sort_by=score" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"

# Search in different subreddit with date range
curl -X GET "http://localhost:8000/api/scenarios/1/subreddit-keyword-search?subreddit=MachineLearning&keywords=pytorch,tensorflow&date_from=2024-01-01&date_to=2024-06-30&limit=15" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"

# Search for async programming posts
curl -X GET "http://localhost:8000/api/scenarios/1/subreddit-keyword-search?subreddit=python&keywords=async,await,asyncio&date_from=2024-01-01&date_to=2024-12-31&limit=20&sort_by=comments" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

### Scenario 2: Multi-Subreddit Trending
```bash
# Trending in programming subreddits today
curl -X GET "http://localhost:8000/api/scenarios/2/trending-multi-subreddits?subreddits=python,programming,coding&timeframe=day&limit=10" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"

# Trending this week in AI subreddits
curl -X GET "http://localhost:8000/api/scenarios/2/trending-multi-subreddits?subreddits=MachineLearning,artificial,OpenAI&timeframe=week&limit=15" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"

# Trending web development topics
curl -X GET "http://localhost:8000/api/scenarios/2/trending-multi-subreddits?subreddits=webdev,javascript,reactjs,node&timeframe=day&limit=20" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"

# Trending in data science communities
curl -X GET "http://localhost:8000/api/scenarios/2/trending-multi-subreddits?subreddits=datascience,analytics,statistics&timeframe=week&limit=12" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

### Scenario 3: Top Posts from r/all
```bash
# Hot posts from r/all today
curl -X GET "http://localhost:8000/api/scenarios/3/top-posts-all?sort_type=hot&time_filter=day&limit=10" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"

# Top posts this week
curl -X GET "http://localhost:8000/api/scenarios/3/top-posts-all?sort_type=top&time_filter=week&limit=25&exclude_nsfw=true" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"

# Rising posts from r/all
curl -X GET "http://localhost:8000/api/scenarios/3/top-posts-all?sort_type=rising&time_filter=hour&limit=15" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"

# Controversial posts this month
curl -X GET "http://localhost:8000/api/scenarios/3/top-posts-all?sort_type=controversial&time_filter=month&limit=20" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

### Scenario 4: Most Popular Posts Today
```bash
# Most popular post in r/python by score
curl -X GET "http://localhost:8000/api/scenarios/4/most-popular-today?subreddit=python&metric=score" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"

# Most commented post in r/programming
curl -X GET "http://localhost:8000/api/scenarios/4/most-popular-today?subreddit=programming&metric=comments" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"

# Highest upvote ratio in r/MachineLearning
curl -X GET "http://localhost:8000/api/scenarios/4/most-popular-today?subreddit=MachineLearning&metric=upvote_ratio" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"

# Most popular in different subreddits
curl -X GET "http://localhost:8000/api/scenarios/4/most-popular-today?subreddit=webdev&metric=score" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
curl -X GET "http://localhost:8000/api/scenarios/4/most-popular-today?subreddit=datascience&metric=comments" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

### Scenario Comments: Advanced Comment Analysis
```bash
# Top comments about Django
curl -X GET "http://localhost:8000/api/scenarios/comments/top-by-criteria?subreddit=python&keywords=django&limit=10" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"

# High-scoring comments in programming
curl -X GET "http://localhost:8000/api/scenarios/comments/top-by-criteria?subreddit=programming&min_score=50&limit=15" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"

# Comments about machine learning
curl -X GET "http://localhost:8000/api/scenarios/comments/top-by-criteria?subreddit=MachineLearning&keywords=neural,networks&limit=20" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"

# Recent quality comments
curl -X GET "http://localhost:8000/api/scenarios/comments/top-by-criteria?subreddit=python&min_score=25&limit=12" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

### Scenario Users: User Activity Analysis
```bash
# Top users by post count in r/python
curl -X GET "http://localhost:8000/api/scenarios/users/top-by-activity?subreddits=python&metric=post_count&limit=10" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"

# Active users across multiple subreddits
curl -X GET "http://localhost:8000/api/scenarios/users/top-by-activity?subreddits=python,programming,webdev&metric=total_score&limit=15" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"

# Most active commenters
curl -X GET "http://localhost:8000/api/scenarios/users/top-by-activity?subreddits=MachineLearning&metric=comment_count&limit=20" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"

# Top contributors in data science
curl -X GET "http://localhost:8000/api/scenarios/users/top-by-activity?subreddits=datascience,statistics&metric=total_score&limit=12" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

### Scenario Examples
```bash
# Get all scenario examples and usage
curl -X GET "http://localhost:8000/api/scenarios/examples" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"

# Pretty print scenarios
curl -s "http://localhost:8000/api/scenarios/examples" | python -m json.tool
```

## Collection API - Persistent Data Pipeline

### Job Management

#### Create Collection Jobs
```bash
# Basic collection job for r/python
curl -X POST "http://localhost:8000/api/collect/jobs" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -H "Content-Type: application/json" \
  -d '{
    "subreddits": ["python"],
    "sort_types": ["hot"],
    "time_filters": ["day"],
    "post_limit": 10,
    "comment_limit": 5,
    "max_comment_depth": 2,
    "min_score": 1,
    "exclude_nsfw": true,
    "anonymize_users": true
  }'

# Multi-subreddit machine learning collection
curl -X POST "http://localhost:8000/api/collect/jobs" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -H "Content-Type: application/json" \
  -d '{
    "subreddits": ["MachineLearning", "artificial", "deeplearning"],
    "sort_types": ["hot", "top"],
    "time_filters": ["day", "week"],
    "post_limit": 50,
    "comment_limit": 20,
    "max_comment_depth": 3,
    "keywords": ["neural", "transformer", "model"],
    "min_score": 25,
    "min_upvote_ratio": 0.8,
    "exclude_nsfw": true,
    "anonymize_users": false
  }'

# Large-scale programming discussion collection
curl -X POST "http://localhost:8000/api/collect/jobs" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -H "Content-Type: application/json" \
  -d '{
    "subreddits": ["programming", "webdev", "javascript", "python"],
    "sort_types": ["hot", "new", "top"],
    "time_filters": ["day"],
    "post_limit": 200,
    "comment_limit": 50,
    "max_comment_depth": 5,
    "keywords": ["framework", "library", "tool"],
    "min_score": 10,
    "min_upvote_ratio": 0.75,
    "exclude_nsfw": true,
    "anonymize_users": true
  }'

# Keyword-specific research collection
curl -X POST "http://localhost:8000/api/collect/jobs" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -H "Content-Type: application/json" \
  -d '{
    "subreddits": ["python", "django", "flask"],
    "sort_types": ["top"],
    "time_filters": ["month"],
    "post_limit": 100,
    "comment_limit": 30,
    "max_comment_depth": 4,
    "keywords": ["fastapi", "async", "performance"],
    "min_score": 50,
    "min_upvote_ratio": 0.85,
    "date_from": "2024-01-01T00:00:00Z",
    "date_to": "2024-12-31T23:59:59Z",
    "exclude_nsfw": true,
    "anonymize_users": false
  }'

# High-volume data science collection
curl -X POST "http://localhost:8000/api/collect/jobs" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -H "Content-Type: application/json" \
  -d '{
    "subreddits": ["datascience", "analytics", "statistics", "MachineLearning"],
    "sort_types": ["hot", "top", "new"],
    "time_filters": ["day", "week"],
    "post_limit": 500,
    "comment_limit": 100,
    "max_comment_depth": 6,
    "keywords": ["dataset", "analysis", "visualization", "pandas"],
    "min_score": 5,
    "min_upvote_ratio": 0.7,
    "exclude_nsfw": true,
    "anonymize_users": true
  }'
```

#### List and Filter Collection Jobs
```bash
# List all collection jobs
curl -X GET "http://localhost:8000/api/collect/jobs" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"

# List with pagination
curl -X GET "http://localhost:8000/api/collect/jobs?page=1&per_page=10" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"

# Filter by status
curl -X GET "http://localhost:8000/api/collect/jobs?status=completed" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
curl -X GET "http://localhost:8000/api/collect/jobs?status=running" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
curl -X GET "http://localhost:8000/api/collect/jobs?status=pending" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
curl -X GET "http://localhost:8000/api/collect/jobs?status=failed" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"

# Combined filtering and pagination
curl -X GET "http://localhost:8000/api/collect/jobs?status=completed&page=2&per_page=5" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

#### Get Job Details and Status
```bash
# Get full job details (replace with actual job ID)
curl -X GET "http://localhost:8000/api/collect/jobs/fdd1714e-2f34-4134-bad9-8625581ebccf" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"

# Get quick status update
curl -X GET "http://localhost:8000/api/collect/jobs/fdd1714e-2f34-4134-bad9-8625581ebccf/status" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"

# Monitor job progress in real-time
while true; do
  curl -s "http://localhost:8000/api/collect/jobs/fdd1714e-2f34-4134-bad9-8625581ebccf/status" | \
    python -c "import sys,json; data=json.load(sys.stdin); print(f'Status: {data[\"status\"]}, Progress: {data[\"progress\"]}%, Posts: {data[\"collected_posts\"]}')"
  sleep 2
done

# Check if job is complete
curl -s "http://localhost:8000/api/collect/jobs/fdd1714e-2f34-4134-bad9-8625581ebccf/status" | \
  python -c "import sys,json; data=json.load(sys.stdin); print('✅ Complete' if data['status'] == 'completed' else '⏳ Running...')"
```

#### Cancel and Delete Jobs
```bash
# Cancel a running job
curl -X POST "http://localhost:8000/api/collect/jobs/fdd1714e-2f34-4134-bad9-8625581ebccf/cancel" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"

# Delete a completed job and all its data (DESTRUCTIVE)
curl -X DELETE "http://localhost:8000/api/collect/jobs/fdd1714e-2f34-4134-bad9-8625581ebccf" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"

# Confirm deletion worked (should return 404)
curl -X GET "http://localhost:8000/api/collect/jobs/fdd1714e-2f34-4134-bad9-8625581ebccf" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

### Collection Workflows

#### Create and Monitor Workflow
```bash
# 1. Create a new collection job
RESPONSE=$(curl -s -X POST "http://localhost:8000/api/collect/jobs" \
  -H "Content-Type: application/json" \
  -d '{
    "subreddits": ["python"],
    "sort_types": ["hot"],
    "time_filters": ["day"],
    "post_limit": 5,
    "comment_limit": 0,
    "min_score": 1,
    "exclude_nsfw": true,
    "anonymize_users": true
  }')

# 2. Extract job ID
JOB_ID=$(echo "$RESPONSE" | python -c "import sys,json; print(json.load(sys.stdin)['job_id'])")
echo "Created job: $JOB_ID"

# 3. Monitor until completion
while true; do
  STATUS=$(curl -s "http://localhost:8000/api/collect/jobs/$JOB_ID/status" | \
    python -c "import sys,json; print(json.load(sys.stdin)['status'])")
  
  if [ "$STATUS" = "completed" ] || [ "$STATUS" = "failed" ]; then
    break
  fi
  
  echo "Job status: $STATUS"
  sleep 1
done

# 4. Get final results
curl -s "http://localhost:8000/api/collect/jobs/$JOB_ID" | \
  python -c "import sys,json; data=json.load(sys.stdin); print(f'Final: {data[\"status\"]} - {data[\"collected_posts\"]} posts collected')"
```

#### Batch Job Creation
```bash
# Create multiple jobs for different subreddits
SUBREDDITS=("python" "programming" "webdev" "javascript" "datascience")

for subreddit in "${SUBREDDITS[@]}"; do
  echo "Creating job for r/$subreddit..."
  
  curl -s -X POST "http://localhost:8000/api/collect/jobs" \
    -H "Content-Type: application/json" \
    -d "{
      \"subreddits\": [\"$subreddit\"],
      \"sort_types\": [\"hot\"],
      \"time_filters\": [\"day\"],
      \"post_limit\": 10,
      \"comment_limit\": 5,
      \"min_score\": 5,
      \"exclude_nsfw\": true,
      \"anonymize_users\": true
    }" | \
    python -c "import sys,json; data=json.load(sys.stdin); print(f'✅ Created job {data[\"job_id\"]} for r/$subreddit')"
    
  sleep 1
done
```

#### Job Statistics and Analysis
```bash
# Get summary of all jobs
curl -s "http://localhost:8000/api/collect/jobs" | \
  python -c "
import sys,json
data=json.load(sys.stdin)
total = data['total']
completed = sum(1 for job in data['jobs'] if job['status'] == 'completed')
running = sum(1 for job in data['jobs'] if job['status'] == 'running')
failed = sum(1 for job in data['jobs'] if job['status'] == 'failed')
total_posts = sum(job['collected_posts'] for job in data['jobs'])
print(f'Jobs: {total} total, {completed} completed, {running} running, {failed} failed')
print(f'Total posts collected: {total_posts}')
"

# Find most productive jobs
curl -s "http://localhost:8000/api/collect/jobs?status=completed" | \
  python -c "
import sys,json
data=json.load(sys.stdin)
jobs = sorted(data['jobs'], key=lambda x: x['collected_posts'], reverse=True)[:5]
print('Top 5 most productive jobs:')
for job in jobs:
    subreddits = ', '.join(job['subreddits'])
    print(f'  {job[\"job_id\"][:8]}... - {job[\"collected_posts\"]} posts from r/{subreddits}')
"

# Calculate collection efficiency
curl -s "http://localhost:8000/api/collect/jobs?status=completed" | \
  python -c "
import sys,json
from datetime import datetime
data=json.load(sys.stdin)
for job in data['jobs'][:3]:
    if job['started_at'] and job['completed_at']:
        start = datetime.fromisoformat(job['started_at'].replace('Z', '+00:00'))
        end = datetime.fromisoformat(job['completed_at'].replace('Z', '+00:00'))
        duration = (end - start).total_seconds()
        rate = job['collected_posts'] / max(duration, 1)
        print(f'Job {job[\"job_id\"][:8]}... - {rate:.2f} posts/second')
"
```

## Query API - Advanced Flexible Queries

### Simple GET Queries
```bash
# Basic simple query
curl -X GET "http://localhost:8000/api/query/posts/simple?subreddits=python&keywords=fastapi&limit=5" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"

# Multiple subreddits with score filter
curl -X GET "http://localhost:8000/api/query/posts/simple?subreddits=python,programming&keywords=django&min_score=50&limit=10" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"

# Search for machine learning posts
curl -X GET "http://localhost:8000/api/query/posts/simple?subreddits=MachineLearning,artificial&keywords=neural,deep&min_score=100&limit=8" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"

# Web development queries
curl -X GET "http://localhost:8000/api/query/posts/simple?subreddits=webdev,javascript&keywords=react,vue&min_score=25&limit=12" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

### Advanced POST Queries

#### Complex Post Filtering
```bash
# High-quality Python posts with multiple filters
curl -X POST "http://localhost:8000/api/query/posts" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -H "Content-Type: application/json" \
  -d '{
    "subreddits": ["python", "programming"],
    "keywords": ["async", "performance", "optimization"],
    "min_score": 100,
    "min_upvote_ratio": 0.85,
    "exclude_keywords": ["beginner", "help", "question"],
    "sort_type": "top",
    "time_filter": "week",
    "limit": 15
  }'

# Machine Learning research posts
curl -X POST "http://localhost:8000/api/query/posts" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -H "Content-Type: application/json" \
  -d '{
    "subreddits": ["MachineLearning", "artificial"],
    "keywords": ["transformer", "neural", "model"],
    "min_score": 200,
    "min_comments": 20,
    "exclude_nsfw": true,
    "exclude_stickied": true,
    "sort_type": "top",
    "time_filter": "month",
    "limit": 20
  }'

# Web development framework comparison
curl -X POST "http://localhost:8000/api/query/posts" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -H "Content-Type: application/json" \
  -d '{
    "subreddits": ["webdev", "javascript", "reactjs"],
    "keywords": ["framework", "comparison", "vs"],
    "min_score": 50,
    "min_upvote_ratio": 0.8,
    "max_comments": 200,
    "sort_type": "hot",
    "limit": 12
  }'

# Data science tutorials and guides
curl -X POST "http://localhost:8000/api/query/posts" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -H "Content-Type: application/json" \
  -d '{
    "subreddits": ["datascience", "analytics", "statistics"],
    "keywords": ["tutorial", "guide", "how-to"],
    "min_score": 75,
    "exclude_keywords": ["basic", "beginner"],
    "content_types": ["text", "link"],
    "sort_type": "top",
    "time_filter": "month",
    "limit": 10
  }'

# Author-specific filtering
curl -X POST "http://localhost:8000/api/query/posts" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -H "Content-Type: application/json" \
  -d '{
    "subreddits": ["python"],
    "exclude_authors": ["AutoModerator", "bot"],
    "min_score": 30,
    "exclude_deleted": true,
    "exclude_removed": true,
    "sort_type": "new",
    "limit": 20
  }'
```

#### Comment Analysis Queries
```bash
# High-quality technical discussions
curl -X POST "http://localhost:8000/api/query/comments" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -H "Content-Type: application/json" \
  -d '{
    "subreddits": ["python", "programming"],
    "keywords": ["architecture", "design", "pattern"],
    "min_score": 15,
    "max_depth": 3,
    "exclude_deleted": true,
    "sort_type": "top",
    "limit": 25
  }'

# Comments from specific posts
curl -X POST "http://localhost:8000/api/query/comments" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -H "Content-Type: application/json" \
  -d '{
    "post_ids": ["abc123", "def456"],
    "min_score": 10,
    "max_depth": 2,
    "exclude_deleted": true,
    "limit": 50
  }'

# Long-form technical comments
curl -X POST "http://localhost:8000/api/query/comments" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -H "Content-Type: application/json" \
  -d '{
    "subreddits": ["MachineLearning"],
    "min_score": 20,
    "keywords": ["explanation", "detailed", "analysis"],
    "exclude_authors": ["AutoModerator"],
    "sort_type": "best",
    "limit": 15
  }'

# Discussion thread analysis
curl -X POST "http://localhost:8000/api/query/comments" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -H "Content-Type: application/json" \
  -d '{
    "subreddits": ["webdev", "javascript"],
    "keywords": ["debate", "discussion", "opinion"],
    "min_score": 5,
    "min_depth": 1,
    "max_depth": 4,
    "limit": 30
  }'
```

#### User Analysis Queries
```bash
# Experienced developers analysis
curl -X POST "http://localhost:8000/api/query/users" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -H "Content-Type: application/json" \
  -d '{
    "subreddits": ["python", "programming"],
    "min_total_karma": 5000,
    "min_account_age_days": 730,
    "limit": 20
  }'

# High-karma machine learning contributors
curl -X POST "http://localhost:8000/api/query/users" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -H "Content-Type: application/json" \
  -d '{
    "subreddits": ["MachineLearning", "artificial"],
    "min_comment_karma": 2000,
    "min_link_karma": 1000,
    "min_account_age_days": 365,
    "limit": 15
  }'

# Active recent contributors
curl -X POST "http://localhost:8000/api/query/users" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -H "Content-Type: application/json" \
  -d '{
    "subreddits": ["webdev", "javascript"],
    "min_post_count": 5,
    "min_comment_count": 20,
    "timeframe_days": 30,
    "exclude_suspended": true,
    "limit": 25
  }'

# Specific user profiles
curl -X POST "http://localhost:8000/api/query/users" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -H "Content-Type: application/json" \
  -d '{
    "usernames": ["spez", "kn0thing", "reddit"],
    "limit": 3
  }'

# Premium/verified users
curl -X POST "http://localhost:8000/api/query/users" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -H "Content-Type: application/json" \
  -d '{
    "subreddits": ["python"],
    "include_verified_only": true,
    "min_total_karma": 1000,
    "limit": 10
  }'
```

### Query Examples
```bash
# Get all query examples and documentation
curl -X GET "http://localhost:8000/api/query/examples" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"

# Pretty print query examples
curl -s "http://localhost:8000/api/query/examples" | python -m json.tool
```

## Documentation Endpoints

```bash
# OpenAPI specification
curl -X GET "http://localhost:8000/openapi.json"

# Get just the paths
curl -s "http://localhost:8000/openapi.json" | python -c "import sys,json; data=json.load(sys.stdin); [print(f'{method.upper()} {path}') for path, methods in data['paths'].items() for method in methods.keys()]"

# Count endpoints by tag
curl -s "http://localhost:8000/openapi.json" | python -c "
import sys,json
data=json.load(sys.stdin)
tags = {}
for path, methods in data['paths'].items():
    for method, details in methods.items():
        tag = details.get('tags', ['Untagged'])[0]
        tags[tag] = tags.get(tag, 0) + 1
for tag, count in tags.items():
    print(f'{tag}: {count} endpoints')
"
```

## Batch Testing Examples

```bash
# Test all core endpoints
echo "Testing core endpoints..."
curl -s "http://localhost:8000/" > /dev/null && echo "✅ Root endpoint"
curl -s "http://localhost:8000/health" > /dev/null && echo "✅ Health endpoint"

# Test scenario endpoints
echo "Testing scenario endpoints..."
curl -s "http://localhost:8000/api/scenarios/examples" > /dev/null && echo "✅ Scenarios examples"
curl -s "http://localhost:8000/api/scenarios/1/subreddit-keyword-search?subreddit=python&keywords=test&date_from=2024-01-01&date_to=2024-12-31&limit=1" > /dev/null && echo "✅ Scenario 1"

# Test query endpoints
echo "Testing query endpoints..."
curl -s "http://localhost:8000/api/query/examples" > /dev/null && echo "✅ Query examples"
curl -s "http://localhost:8000/api/query/posts/simple?subreddits=python&limit=1" > /dev/null && echo "✅ Simple query"

# Test collection endpoints
echo "Testing collection endpoints..."
curl -s "http://localhost:8000/api/collect/jobs" > /dev/null && echo "✅ List jobs endpoint"

# Create and test a collection job
echo "Testing collection job creation..."
JOB_RESPONSE=$(curl -s -X POST "http://localhost:8000/api/collect/jobs" \
  -H "Content-Type: application/json" \
  -d '{
    "subreddits": ["python"],
    "sort_types": ["hot"],
    "time_filters": ["day"],
    "post_limit": 2,
    "comment_limit": 0,
    "min_score": 1,
    "exclude_nsfw": true,
    "anonymize_users": true
  }')

if echo "$JOB_RESPONSE" | grep -q "job_id"; then
  echo "✅ Collection job creation"
  
  # Extract job ID and test status endpoint
  JOB_ID=$(echo "$JOB_RESPONSE" | python -c "import sys,json; print(json.load(sys.stdin)['job_id'])")
  sleep 2
  
  curl -s "http://localhost:8000/api/collect/jobs/$JOB_ID/status" > /dev/null && echo "✅ Job status endpoint"
  curl -s "http://localhost:8000/api/collect/jobs/$JOB_ID" > /dev/null && echo "✅ Job details endpoint"
else
  echo "❌ Collection job creation failed"
fi

# Performance test
echo "Performance testing..."
time curl -s "http://localhost:8000/api/query/posts/simple?subreddits=python&keywords=fastapi&limit=5" > /dev/null
```

## Complete Collection API Test Suite

```bash
#!/bin/bash
# Complete test suite for Collection API

echo "🧪 Collection API Test Suite"
echo "============================="

# Test 1: List empty jobs
echo "Test 1: List jobs (should be empty or existing jobs)"
curl -s "http://localhost:8000/api/collect/jobs" | python -c "
import sys,json
data=json.load(sys.stdin)
print(f'✅ Found {data[\"total\"]} existing jobs')
"

# Test 2: Create basic job
echo -e "\nTest 2: Create basic collection job"
BASIC_JOB=$(curl -s -X POST "http://localhost:8000/api/collect/jobs" \
  -H "Content-Type: application/json" \
  -d '{
    "subreddits": ["python"],
    "sort_types": ["hot"],
    "time_filters": ["day"],
    "post_limit": 3,
    "comment_limit": 0,
    "min_score": 1,
    "exclude_nsfw": true,
    "anonymize_users": true
  }')

BASIC_JOB_ID=$(echo "$BASIC_JOB" | python -c "import sys,json; print(json.load(sys.stdin)['job_id'])")
echo "✅ Created basic job: $BASIC_JOB_ID"

# Test 3: Create advanced job with keywords
echo -e "\nTest 3: Create advanced job with keywords"
ADVANCED_JOB=$(curl -s -X POST "http://localhost:8000/api/collect/jobs" \
  -H "Content-Type: application/json" \
  -d '{
    "subreddits": ["python", "programming"],
    "sort_types": ["hot", "top"],
    "time_filters": ["day"],
    "post_limit": 5,
    "comment_limit": 5,
    "max_comment_depth": 2,
    "keywords": ["fastapi", "django"],
    "min_score": 5,
    "min_upvote_ratio": 0.8,
    "exclude_nsfw": true,
    "anonymize_users": false
  }')

ADVANCED_JOB_ID=$(echo "$ADVANCED_JOB" | python -c "import sys,json; print(json.load(sys.stdin)['job_id'])")
echo "✅ Created advanced job: $ADVANCED_JOB_ID"

# Test 4: Monitor job completion
echo -e "\nTest 4: Monitor job completion"
for job_id in "$BASIC_JOB_ID" "$ADVANCED_JOB_ID"; do
  echo "Monitoring job $job_id..."
  for i in {1..10}; do
    STATUS=$(curl -s "http://localhost:8000/api/collect/jobs/$job_id/status" | \
      python -c "import sys,json; data=json.load(sys.stdin); print(data['status'])")
    
    if [ "$STATUS" = "completed" ] || [ "$STATUS" = "failed" ]; then
      echo "✅ Job $job_id completed with status: $STATUS"
      break
    fi
    
    echo "  Status: $STATUS (attempt $i/10)"
    sleep 1
  done
done

# Test 5: Get job details
echo -e "\nTest 5: Get job details"
curl -s "http://localhost:8000/api/collect/jobs/$BASIC_JOB_ID" | python -c "
import sys,json
data=json.load(sys.stdin)
print(f'✅ Job details: {data[\"status\"]} - {data[\"collected_posts\"]} posts, {data[\"collected_comments\"]} comments')
"

# Test 6: List jobs with pagination
echo -e "\nTest 6: Test pagination"
curl -s "http://localhost:8000/api/collect/jobs?page=1&per_page=5" | python -c "
import sys,json
data=json.load(sys.stdin)
print(f'✅ Pagination: page 1, {len(data[\"jobs\"])} jobs returned')
"

# Test 7: Filter by status
echo -e "\nTest 7: Filter by status"
curl -s "http://localhost:8000/api/collect/jobs?status=completed" | python -c "
import sys,json
data=json.load(sys.stdin)
completed_jobs = len(data['jobs'])
print(f'✅ Status filter: found {completed_jobs} completed jobs')
"

# Test 8: Test invalid job ID
echo -e "\nTest 8: Test invalid job ID (should return 404)"
INVALID_RESPONSE=$(curl -s -w "HTTP_%{http_code}" "http://localhost:8000/api/collect/jobs/invalid-job-id")
if echo "$INVALID_RESPONSE" | grep -q "HTTP_404"; then
  echo "✅ Invalid job ID correctly returns 404"
else
  echo "❌ Invalid job ID test failed"
fi

# Test 9: Test job cancellation (create a job to cancel)
echo -e "\nTest 9: Test job cancellation"
CANCEL_JOB=$(curl -s -X POST "http://localhost:8000/api/collect/jobs" \
  -H "Content-Type: application/json" \
  -d '{
    "subreddits": ["python"],
    "sort_types": ["hot"],
    "time_filters": ["day"],
    "post_limit": 100,
    "comment_limit": 50,
    "min_score": 1,
    "exclude_nsfw": true,
    "anonymize_users": true
  }')

CANCEL_JOB_ID=$(echo "$CANCEL_JOB" | python -c "import sys,json; print(json.load(sys.stdin)['job_id'])")

# Try to cancel it immediately
CANCEL_RESPONSE=$(curl -s -X POST "http://localhost:8000/api/collect/jobs/$CANCEL_JOB_ID/cancel")
if echo "$CANCEL_RESPONSE" | grep -q "cancelled successfully"; then
  echo "✅ Job cancellation works"
else
  echo "⚠️  Job may have completed before cancellation"
fi

echo -e "\n🎉 Collection API test suite completed!"
echo "Run this script to verify all Collection API functionality."
```

## Response Processing Examples

```bash
# Extract just titles from posts
curl -s "http://localhost:8000/api/query/posts/simple?subreddits=python&keywords=fastapi&limit=5" | \
  python -c "import sys,json; data=json.load(sys.stdin); [print(f'• {post[\"title\"]}') for post in data['results']]"

# Get execution time and count
curl -s "http://localhost:8000/api/query/posts/simple?subreddits=python&limit=3" | \
  python -c "import sys,json; data=json.load(sys.stdin); print(f'Results: {data[\"count\"]}, Time: {data[\"execution_time_ms\"]:.2f}ms')"

# Extract user karma information
curl -s -X POST "http://localhost:8000/api/query/users" \
  -H "Content-Type: application/json" \
  -d '{"usernames": ["spez"], "limit": 1}' | \
  python -c "import sys,json; data=json.load(sys.stdin); user=data['results'][0]; print(f'{user[\"username\"]}: {user[\"total_karma\"]} karma')"

# Count posts by subreddit
curl -s "http://localhost:8000/api/query/posts/simple?subreddits=python,programming&limit=20" | \
  python -c "
import sys,json
data=json.load(sys.stdin)
subreddits = {}
for post in data['results']:
    sub = post['subreddit']
    subreddits[sub] = subreddits.get(sub, 0) + 1
for sub, count in subreddits.items():
    print(f'{sub}: {count} posts')
"
```

## Data API - Query Stored Data

### Summary and Recent Data
```bash
# Get data collection summary
curl -X GET "http://localhost:8000/api/data/summary" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"

# Get recent posts from all collections
curl -X GET "http://localhost:8000/api/data/posts/recent?limit=10" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"

# Get recent comments from all collections  
curl -X GET "http://localhost:8000/api/data/comments/recent?limit=15" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

### Advanced Post Queries
```bash
# Query posts from specific subreddits
curl -X POST "http://localhost:8000/api/data/posts" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -H "Content-Type: application/json" \
  -d '{
    "subreddits": ["Python", "programming"],
    "limit": 20,
    "sort_by": "score",
    "sort_order": "desc"
  }'

# High-quality posts with keyword filtering
curl -X POST "http://localhost:8000/api/data/posts" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -H "Content-Type: application/json" \
  -d '{
    "subreddits": ["Python"],
    "keywords": ["fastapi", "async", "performance"],
    "min_score": 50,
    "min_upvote_ratio": 0.85,
    "exclude_keywords": ["beginner", "help"],
    "limit": 15,
    "sort_by": "upvote_ratio",
    "sort_order": "desc"
  }'

# Posts from specific collection jobs
curl -X POST "http://localhost:8000/api/data/posts" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -H "Content-Type: application/json" \
  -d '{
    "collection_job_ids": ["2359bab0-5a7a-4b1f-98fe-2db1c54eb5b9"],
    "min_score": 10,
    "limit": 25
  }'

# Date range filtering
curl -X POST "http://localhost:8000/api/data/posts" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -H "Content-Type: application/json" \
  -d '{
    "subreddits": ["MachineLearning"],
    "date_from": "2024-08-01T00:00:00Z",
    "date_to": "2024-08-31T23:59:59Z",
    "min_score": 100,
    "limit": 30
  }'

# Content type filtering
curl -X POST "http://localhost:8000/api/data/posts" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -H "Content-Type: application/json" \
  -d '{
    "subreddits": ["webdev"],
    "content_types": ["text", "link"],
    "exclude_nsfw": true,
    "exclude_stickied": true,
    "min_comments": 5,
    "limit": 20
  }'

# Author filtering
curl -X POST "http://localhost:8000/api/data/posts" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -H "Content-Type: application/json" \
  -d '{
    "subreddits": ["python"],
    "authors": ["specific_user"],
    "exclude_authors": ["AutoModerator", "bot"],
    "exclude_deleted": true,
    "limit": 15
  }'
```

### Advanced Comment Queries
```bash
# Query comments with keyword filtering
curl -X POST "http://localhost:8000/api/data/comments" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -H "Content-Type: application/json" \
  -d '{
    "subreddits": ["Python", "programming"],
    "keywords": ["architecture", "design", "pattern"],
    "min_score": 15,
    "max_depth": 3,
    "limit": 25
  }'

# Comments from specific posts
curl -X POST "http://localhost:8000/api/data/comments" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -H "Content-Type: application/json" \
  -d '{
    "post_ids": [1, 2, 3],
    "min_score": 10,
    "exclude_deleted": true,
    "sort_by": "score",
    "sort_order": "desc",
    "limit": 50
  }'

# Deep thread analysis
curl -X POST "http://localhost:8000/api/data/comments" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -H "Content-Type: application/json" \
  -d '{
    "subreddits": ["MachineLearning"],
    "min_score": 20,
    "min_depth": 1,
    "max_depth": 5,
    "keywords": ["explanation", "detailed"],
    "exclude_authors": ["AutoModerator"],
    "limit": 30
  }'

# Comments from specific collection jobs
curl -X POST "http://localhost:8000/api/data/comments" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -H "Content-Type: application/json" \
  -d '{
    "collection_job_ids": ["2359bab0-5a7a-4b1f-98fe-2db1c54eb5b9"],
    "min_score": 5,
    "limit": 40
  }'
```

### Analytics and Insights
```bash
# Get analytics for a specific collection job
curl -X GET "http://localhost:8000/api/data/analytics/2359bab0-5a7a-4b1f-98fe-2db1c54eb5b9" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"

# Get analytics with pretty formatting
curl -s "http://localhost:8000/api/data/analytics/2359bab0-5a7a-4b1f-98fe-2db1c54eb5b9" | jq

# Check if analytics exist for a job
curl -s "http://localhost:8000/api/data/analytics/2359bab0-5a7a-4b1f-98fe-2db1c54eb5b9" | \
  python -c "import sys,json; data=json.load(sys.stdin); print('✅ Analytics available' if 'analytics' in data else '❌ No analytics')"
```

## Export API - Data Export in Multiple Formats

### Supported Formats Information
```bash
# List all supported export formats
curl -X GET "http://localhost:8000/api/export/formats" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"

# Get format information with pretty output
curl -s "http://localhost:8000/api/export/formats" | jq '.supported_formats'
```

### Export Posts Data
```bash
# Export posts as CSV
curl -X POST "http://localhost:8000/api/export/posts/csv" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -H "Content-Type: application/json" \
  -d '{
    "subreddits": ["Python"],
    "limit": 100,
    "sort_by": "score",
    "sort_order": "desc"
  }' --output posts_export.csv

# Export high-quality posts as JSON
curl -X POST "http://localhost:8000/api/export/posts/json" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -H "Content-Type: application/json" \
  -d '{
    "subreddits": ["Python", "programming"],
    "min_score": 50,
    "min_upvote_ratio": 0.8,
    "keywords": ["tutorial", "guide", "best practices"],
    "limit": 50
  }' --output quality_posts.json

# Export posts as JSONL for streaming processing
curl -X POST "http://localhost:8000/api/export/posts/jsonl" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -H "Content-Type: application/json" \
  -d '{
    "subreddits": ["MachineLearning"],
    "keywords": ["research", "paper", "study"],
    "min_score": 100,
    "limit": 200
  }' --output ml_research.jsonl

# Export posts as Parquet for analytics
curl -X POST "http://localhost:8000/api/export/posts/parquet" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -H "Content-Type: application/json" \
  -d '{
    "subreddits": ["datascience", "analytics"],
    "date_from": "2024-08-01T00:00:00Z",
    "date_to": "2024-08-31T23:59:59Z",
    "limit": 1000
  }' --output posts_analytics.parquet

# Export posts with advanced filtering
curl -X POST "http://localhost:8000/api/export/posts/csv" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -H "Content-Type: application/json" \
  -d '{
    "collection_job_ids": ["2359bab0-5a7a-4b1f-98fe-2db1c54eb5b9"],
    "min_score": 25,
    "exclude_nsfw": true,
    "exclude_stickied": true,
    "content_types": ["text", "link"]
  }' --output filtered_posts.csv
```

### Export Comments Data
```bash
# Export comments as CSV
curl -X POST "http://localhost:8000/api/export/comments/csv" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -H "Content-Type: application/json" \
  -d '{
    "subreddits": ["Python"],
    "min_score": 10,
    "max_depth": 3,
    "limit": 500
  }' --output comments_export.csv

# Export high-quality technical comments as JSON
curl -X POST "http://localhost:8000/api/export/comments/json" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -H "Content-Type: application/json" \
  -d '{
    "subreddits": ["programming", "webdev"],
    "keywords": ["architecture", "design", "performance"],
    "min_score": 20,
    "exclude_authors": ["AutoModerator"],
    "limit": 200
  }' --output technical_comments.json

# Export comment threads as JSONL
curl -X POST "http://localhost:8000/api/export/comments/jsonl" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -H "Content-Type: application/json" \
  -d '{
    "post_ids": [1, 2, 3, 4, 5],
    "min_depth": 1,
    "max_depth": 4,
    "sort_by": "score",
    "sort_order": "desc"
  }' --output comment_threads.jsonl

# Export comments for data analysis
curl -X POST "http://localhost:8000/api/export/comments/parquet" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -H "Content-Type: application/json" \
  -d '{
    "subreddits": ["MachineLearning", "artificial"],
    "keywords": ["explanation", "analysis"],
    "min_score": 15,
    "limit": 1000
  }' --output comments_analysis.parquet
```

### Export Complete Job Data
```bash
# Export complete job data as JSON (includes job metadata + posts + comments)
curl -X GET "http://localhost:8000/api/export/job/2359bab0-5a7a-4b1f-98fe-2db1c54eb5b9/json" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  --output complete_job.json

# Export job data as CSV (posts only)
curl -X GET "http://localhost:8000/api/export/job/2359bab0-5a7a-4b1f-98fe-2db1c54eb5b9/csv" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  --output job_posts.csv

# Export job data as JSONL for processing
curl -X GET "http://localhost:8000/api/export/job/2359bab0-5a7a-4b1f-98fe-2db1c54eb5b9/jsonl" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  --output job_data.jsonl

# Export job data as Parquet for analytics
curl -X GET "http://localhost:8000/api/export/job/2359bab0-5a7a-4b1f-98fe-2db1c54eb5b9/parquet" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  --output job_analytics.parquet
```

### Export Workflows and Examples
```bash
# Export workflow: Query -> Filter -> Export
# 1. Find high-quality posts
POSTS_QUERY='{
  "subreddits": ["Python", "programming"],
  "keywords": ["best practices", "architecture", "design"],
  "min_score": 100,
  "min_upvote_ratio": 0.9,
  "limit": 50
}'

# 2. Export as multiple formats for different use cases
echo "Exporting for spreadsheet analysis..."
curl -X POST "http://localhost:8000/api/export/posts/csv" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -H "Content-Type: application/json" \
  -d "$POSTS_QUERY" --output analysis.csv

echo "Exporting for API integration..."
curl -X POST "http://localhost:8000/api/export/posts/json" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -H "Content-Type: application/json" \
  -d "$POSTS_QUERY" --output integration.json

echo "Exporting for data science..."
curl -X POST "http://localhost:8000/api/export/posts/parquet" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -H "Content-Type: application/json" \
  -d "$POSTS_QUERY" --output data_science.parquet

echo "✅ Export workflow completed!"

# Batch export multiple collection jobs
echo "Batch exporting collection jobs..."
JOBS=("2359bab0-5a7a-4b1f-98fe-2db1c54eb5b9" "fdd1714e-2f34-4134-bad9-8625581ebccf")

for job_id in "${JOBS[@]}"; do
  echo "Exporting job: $job_id"
  curl -s -X GET "http://localhost:8000/api/export/job/$job_id/csv" \
    --output "job_${job_id:0:8}.csv"
  echo "✅ Exported job_${job_id:0:8}.csv"
done

# Verify exports
echo -e "\nExport verification:"
ls -la *.csv *.json *.parquet 2>/dev/null | wc -l | \
  python -c "import sys; count=int(sys.stdin.read().strip()); print(f'✅ {count} files exported successfully')"
```

### Export Data Validation
```bash
# Test export formats
echo "Testing export formats..."

# Test CSV export and verify structure
curl -X POST "http://localhost:8000/api/export/posts/csv" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -H "Content-Type: application/json" \
  -d '{"subreddits": ["Python"], "limit": 3}' \
  --output test.csv

if [ -f "test.csv" ]; then
  echo "✅ CSV export successful"
  echo "CSV headers: $(head -1 test.csv)"
  echo "CSV rows: $(wc -l < test.csv)"
  rm test.csv
fi

# Test JSON export and verify structure
curl -s -X POST "http://localhost:8000/api/export/posts/json" \
  -H "Content-Type: application/json" \
  -d '{"subreddits": ["Python"], "limit": 2}' | \
  python -c "
import sys,json
try:
    data=json.load(sys.stdin)
    print(f'✅ JSON export successful - {len(data)} records')
    if data:
        print(f'JSON keys: {list(data[0].keys())[:5]}...')
except:
    print('❌ JSON export failed')
"

# Test JSONL export
curl -s -X POST "http://localhost:8000/api/export/posts/jsonl" \
  -H "Content-Type: application/json" \
  -d '{"subreddits": ["Python"], "limit": 2}' | \
  python -c "
import sys,json
lines = sys.stdin.read().strip().split('\n')
try:
    for line in lines[:1]:
        json.loads(line)
    print(f'✅ JSONL export successful - {len(lines)} lines')
except:
    print('❌ JSONL export failed')
"
```

## Sentiment Analysis API - AI-Powered Content Analysis

### Service Status and Configuration
```bash
# Check sentiment analysis availability and configuration
curl -X GET "http://localhost:8000/api/sentiment/status" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"

# Test sentiment analysis with sample data
curl -X GET "http://localhost:8000/api/sentiment/test" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

### Single Text Analysis
```bash
# Analyze sentiment of a single text
curl -X POST "http://localhost:8000/api/sentiment/analyze" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "I absolutely love this new feature! It works perfectly and makes everything so much easier."
  }'

# Analyze a negative sentiment text
curl -X POST "http://localhost:8000/api/sentiment/analyze" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "This is terrible. I hate how complicated and broken everything is."
  }'

# Analyze neutral content
curl -X POST "http://localhost:8000/api/sentiment/analyze" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "The documentation explains the basic installation process and configuration options."
  }'
```

### Batch Text Analysis
```bash
# Analyze multiple texts in one request
curl -X POST "http://localhost:8000/api/sentiment/analyze-batch" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -H "Content-Type: application/json" \
  -d '{
    "texts": [
      "FastAPI is amazing! I love how easy it is to build APIs.",
      "This framework is terrible. Documentation is confusing.",
      "It works fine, nothing special but gets the job done.",
      "Excellent performance and great developer experience!",
      "Average framework, has some issues but overall okay."
    ]
  }'

# Analyze Reddit post-style content
curl -X POST "http://localhost:8000/api/sentiment/analyze-batch" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -H "Content-Type: application/json" \
  -d '{
    "texts": [
      "Just deployed my first FastAPI app to production. The async support is incredible!",
      "Can someone help? My API keeps throwing 500 errors and I cannot figure out why.",
      "Comparing Django vs FastAPI for our next project. Both have pros and cons.",
      "TIL: You can use background tasks in FastAPI. Game changer for my use case!"
    ]
  }'
```

### Sentiment Analysis Integration
The sentiment analysis service is automatically integrated into the data collection pipeline:

```bash
# Configure OpenRouter API key (required for sentiment analysis)
export OPENROUTER_API_KEY="your_api_key_here"

# Create collection job - posts will automatically get sentiment scores
curl -X POST "http://localhost:8000/api/collect/jobs" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -H "Content-Type: application/json" \
  -d '{
    "subreddits": ["python", "programming"],
    "sort_types": ["hot"],
    "time_filters": ["day"],
    "post_limit": 10,
    "comment_limit": 5,
    "min_score": 25,
    "exclude_nsfw": true,
    "anonymize_users": true
  }'

# Query posts with sentiment scores
curl -X POST "http://localhost:8000/api/data/posts" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -H "Content-Type: application/json" \
  -d '{
    "limit": 10,
    "sort_by": "sentiment_score",
    "sort_order": "desc"
  }' | jq '.results[] | {title: .title, sentiment_score: .sentiment_score, subreddit: .subreddit}'

# Export data with sentiment analysis
curl -X POST "http://localhost:8000/api/export/posts/csv" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -H "Content-Type: application/json" \
  -d '{
    "subreddits": ["python"],
    "min_score": 50,
    "limit": 100
  }' --output posts_with_sentiment.csv
```

### Sentiment Analysis Features
- **Powered by OpenRouter**: Uses Claude 3 Haiku for fast, accurate sentiment analysis
- **Batch Processing**: Efficiently analyzes multiple texts simultaneously
- **Automatic Integration**: Posts are automatically analyzed during collection
- **Graceful Degradation**: System works normally even without API key configured
- **Detailed Statistics**: Provides sentiment distribution and analytics
- **Export Support**: Sentiment scores included in all export formats

### Setup Instructions
1. Sign up for OpenRouter at https://openrouter.ai/
2. Get your API key from the dashboard
3. Set the environment variable: `OPENROUTER_API_KEY=your_key`
4. Restart the server to enable sentiment analysis
5. New collection jobs will automatically include sentiment analysis

## Error Testing

```bash
# Test invalid subreddit
curl -X GET "http://localhost:8000/api/scenarios/1/subreddit-keyword-search?subreddit=invalidsubreddit&keywords=test&date_from=2024-01-01&date_to=2024-12-31" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"

# Test malformed JSON
curl -X POST "http://localhost:8000/api/query/posts" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -H "Content-Type: application/json" \
  -d '{"invalid": json}'

# Test missing required parameters
curl -X GET "http://localhost:8000/api/scenarios/1/subreddit-keyword-search?subreddit=python" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"

# Test invalid date range
curl -X GET "http://localhost:8000/api/scenarios/1/subreddit-keyword-search?subreddit=python&keywords=test&date_from=2024-12-31&date_to=2024-01-01" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"

# Test invalid export format
curl -X POST "http://localhost:8000/api/export/posts/invalid_format" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -H "Content-Type: application/json" \
  -d '{"subreddits": ["Python"], "limit": 5}'

# Test export with no matching data
curl -X POST "http://localhost:8000/api/export/posts/csv" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -H "Content-Type: application/json" \
  -d '{"subreddits": ["NonExistentSubreddit"], "limit": 5}'

# Test data query with invalid job ID
curl -X GET "http://localhost:8000/api/data/analytics/invalid-job-id" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```
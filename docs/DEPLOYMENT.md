# Deployment Guide

This guide covers deploying the Trendit backend API to production environments.

## 🚀 Quick Deploy to Render

### 1. Repository Setup
```bash
# Ensure your code is pushed to GitHub
git push origin main
```

### 2. Render Configuration

**Create new Web Service:**
- Repository: `jpotterlabs/trendit-backend`
- Branch: `main`
- Build Command: `pip install -r requirements.txt`
- Start Command: `uvicorn main:app --host 0.0.0.0 --port $PORT`

### 3. Environment Variables

Set these in Render dashboard:

```bash
# Database (Neon PostgreSQL)
DATABASE_URL=postgresql://neondb_owner:npg_daSvTEL8boA6@ep-silent-mud-af6oce7w-pooler.c-2.us-west-2.aws.neon.tech/neondb?sslmode=require

# Reddit API
REDDIT_CLIENT_ID=-T-xIloy461T3DEpHN8-VQ
REDDIT_CLIENT_SECRET=g9VH1JoWvlt5jMuVfGBIFwOCDt7x0Q
REDDIT_USER_AGENT=Trendit/1.0 by /u/cdarwin7

# Auth0 Configuration
AUTH0_DOMAIN=dev-fcd66rg4kdgkdeap.us.auth0.com
AUTH0_CLIENT_ID=gUGJlkuQtRPlkv2C916KxF9dpsGcDbHR
AUTH0_CLIENT_SECRET=v9UbvDBcF5lOj9C4BRqGIejzsrQfR9K-WoiPAUB32r27Skkl4PgOSJVPNXRtOHk8
AUTH0_AUDIENCE=https://api.potterlabs.xyz

# JWT Configuration  
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=1440
JWT_ALGORITHM=HS256
JWT_SECRET_KEY=45a5b1e7753ec3e4a7e84427adac5d9d

# API Security
ADMIN_SECRET_KEY=4620af14c7f5b9444eef375b1b67d484
API_KEY_SALT=aa0827b7028c4024a6aa32cdcdee4f99

# Optional Integrations
OPENROUTER_API_KEY=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
```

### 4. Database Initialization

After first deployment:
```bash
# SSH into Render instance or run locally pointing to production DB
python init_db.py
```

## 🐳 Docker Deployment

### Dockerfile
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose port
EXPOSE 8000

# Run application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Docker Compose
```yaml
version: '3.8'
services:
  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - REDDIT_CLIENT_ID=${REDDIT_CLIENT_ID}
      - REDDIT_CLIENT_SECRET=${REDDIT_CLIENT_SECRET}
      # ... other env vars
    depends_on:
      - db
      - redis

  db:
    image: postgres:15
    environment:
      POSTGRES_DB: trendit
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: password
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

volumes:
  postgres_data:
```

### Build and Deploy
```bash
# Build image
docker build -t trendit-backend .

# Run with environment file
docker run --env-file .env -p 8000:8000 trendit-backend

# Or use docker-compose
docker-compose up -d
```

## ☁️ Cloud Platform Deployments

### AWS ECS/Fargate

**1. Create ECR repository:**
```bash
aws ecr create-repository --repository-name trendit-backend
```

**2. Build and push image:**
```bash
# Get login token
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin 123456789012.dkr.ecr.us-east-1.amazonaws.com

# Build and tag
docker build -t trendit-backend .
docker tag trendit-backend:latest 123456789012.dkr.ecr.us-east-1.amazonaws.com/trendit-backend:latest

# Push
docker push 123456789012.dkr.ecr.us-east-1.amazonaws.com/trendit-backend:latest
```

**3. Create ECS task definition:**
```json
{
  "family": "trendit-backend",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "256",
  "memory": "512",
  "executionRoleArn": "arn:aws:iam::123456789012:role/ecsTaskExecutionRole",
  "containerDefinitions": [
    {
      "name": "trendit-backend",
      "image": "123456789012.dkr.ecr.us-east-1.amazonaws.com/trendit-backend:latest",
      "portMappings": [
        {
          "containerPort": 8000,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {"name": "DATABASE_URL", "value": "postgresql://..."},
        {"name": "REDDIT_CLIENT_ID", "value": "..."}
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/trendit-backend",
          "awslogs-region": "us-east-1",
          "awslogs-stream-prefix": "ecs"
        }
      }
    }
  ]
}
```

### Google Cloud Run

```bash
# Build and push to Google Container Registry
gcloud builds submit --tag gcr.io/PROJECT_ID/trendit-backend

# Deploy to Cloud Run
gcloud run deploy trendit-backend \
  --image gcr.io/PROJECT_ID/trendit-backend \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars="DATABASE_URL=postgresql://...,REDDIT_CLIENT_ID=..."
```

### Azure Container Instances

```bash
# Create resource group
az group create --name trendit-rg --location eastus

# Create container instance
az container create \
  --resource-group trendit-rg \
  --name trendit-backend \
  --image trendit-backend:latest \
  --cpu 1 \
  --memory 1 \
  --ports 8000 \
  --environment-variables \
    DATABASE_URL="postgresql://..." \
    REDDIT_CLIENT_ID="..."
```

## 🗄️ Database Setup

### Neon PostgreSQL (Recommended)

**1. Create database:**
- Sign up at neon.tech
- Create new project
- Copy connection string

**2. Set DATABASE_URL:**
```bash
DATABASE_URL=postgresql://user:password@host/dbname?sslmode=require
```

### Local PostgreSQL

**1. Install PostgreSQL:**
```bash
# Ubuntu/Debian
sudo apt-get install postgresql postgresql-contrib

# macOS
brew install postgresql
```

**2. Create database:**
```bash
sudo -u postgres psql
CREATE DATABASE trendit;
CREATE USER trendituser WITH PASSWORD 'password';
GRANT ALL PRIVILEGES ON DATABASE trendit TO trendituser;
```

**3. Set DATABASE_URL:**
```bash
DATABASE_URL=postgresql://trendituser:password@localhost:5432/trendit
```

## 🔧 Configuration Management

### Environment-Specific Configs

**Production (.env.production):**
```bash
DATABASE_URL=postgresql://production-url
REDDIT_CLIENT_ID=production-reddit-id
LOG_LEVEL=WARNING
DEBUG=false
```

**Staging (.env.staging):**
```bash
DATABASE_URL=postgresql://staging-url
REDDIT_CLIENT_ID=staging-reddit-id
LOG_LEVEL=INFO
DEBUG=true
```

**Development (.env.development):**
```bash
DATABASE_URL=postgresql://localhost/trendit_dev
REDDIT_CLIENT_ID=dev-reddit-id
LOG_LEVEL=DEBUG
DEBUG=true
```

### Secrets Management

**AWS Secrets Manager:**
```python
import boto3
import json

def get_secret(secret_name):
    client = boto3.client('secretsmanager')
    response = client.get_secret_value(SecretId=secret_name)
    return json.loads(response['SecretString'])

# In your application
secrets = get_secret('trendit-backend-secrets')
DATABASE_URL = secrets['DATABASE_URL']
```

**HashiCorp Vault:**
```python
import hvac

client = hvac.Client(url='https://vault.example.com')
client.token = 'your-vault-token'
secrets = client.secrets.kv.v2.read_secret_version(path='trendit-backend')
DATABASE_URL = secrets['data']['data']['DATABASE_URL']
```

## 🔍 Monitoring & Logging

### Health Checks

Add health check endpoint monitoring:
```bash
# Basic health check
curl https://api.potterlabs.xyz/health

# Database health
curl https://api.potterlabs.xyz/health/db

# Reddit API health
curl https://api.potterlabs.xyz/health/reddit
```

### Logging Setup

**Structured logging with JSON:**
```python
import logging
import json
from pythonjsonlogger import jsonlogger

# Configure JSON logging
handler = logging.StreamHandler()
formatter = jsonlogger.JsonFormatter(
    '%(asctime)s %(name)s %(levelname)s %(message)s'
)
handler.setFormatter(formatter)

logger = logging.getLogger()
logger.addHandler(handler)
logger.setLevel(logging.INFO)
```

### Monitoring Tools

**Application Performance Monitoring:**
- Sentry for error tracking
- New Relic for performance monitoring
- DataDog for metrics and logs

**Basic monitoring script:**
```bash
#!/bin/bash
# monitor.sh - Simple health check script

URL="https://api.potterlabs.xyz/health"
RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" $URL)

if [ $RESPONSE -eq 200 ]; then
    echo "$(date): API is healthy"
else
    echo "$(date): API is down (HTTP $RESPONSE)"
    # Send alert notification
fi
```

## 🚨 Troubleshooting

### Common Deployment Issues

**1. Database Connection Errors:**
```bash
# Check connection string format
postgresql://user:password@host:port/database?sslmode=require

# Test connection
python -c "from models.database import engine; print(engine.execute('SELECT 1').scalar())"
```

**2. Environment Variable Issues:**
```bash
# List all environment variables
env | grep REDDIT
env | grep AUTH0
env | grep DATABASE

# Check from within application
python -c "import os; print(os.getenv('DATABASE_URL'))"
```

**3. Port/Binding Issues:**
```bash
# Check if port is in use
lsof -i :8000
netstat -tlnp | grep 8000

# Use different port
uvicorn main:app --port 8080
```

**4. Memory/Resource Issues:**
```bash
# Check memory usage
free -h
ps aux | grep python

# Monitor during startup
top -p $(pgrep python)
```

### Debug Mode

**Enable debug logging:**
```bash
export LOG_LEVEL=DEBUG
export DEBUG=true
uvicorn main:app --log-level debug
```

**Debug database queries:**
```python
import logging
logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)
```

## 🔄 CI/CD Pipeline

### GitHub Actions

**.github/workflows/deploy.yml:**
```yaml
name: Deploy to Production

on:
  push:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Run tests
        run: python test_api.py

  deploy:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - name: Deploy to Render
        uses: render-io/render-deploy-action@v1.0.1
        with:
          service-id: ${{ secrets.RENDER_SERVICE_ID }}
          api-key: ${{ secrets.RENDER_API_KEY }}
```

## 📊 Performance Optimization

### Database Optimization

**Connection pooling:**
```python
from sqlalchemy import create_engine
from sqlalchemy.pool import QueuePool

engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=20,
    max_overflow=30,
    pool_pre_ping=True
)
```

**Query optimization:**
```python
# Use bulk operations
posts = session.bulk_insert_mappings(Post, post_data)

# Optimize N+1 queries
posts = session.query(Post).options(joinedload(Post.comments)).all()
```

### Caching

**Redis caching:**
```python
import redis
import json

redis_client = redis.Redis(host='localhost', port=6379, db=0)

def get_cached_data(key):
    data = redis_client.get(key)
    return json.loads(data) if data else None

def set_cached_data(key, data, ttl=3600):
    redis_client.setex(key, ttl, json.dumps(data))
```

## 🔐 Security Hardening

### HTTPS/SSL Setup

**Nginx reverse proxy:**
```nginx
server {
    listen 443 ssl;
    server_name api.potterlabs.xyz;
    
    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;
    
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### Security Headers

```python
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["api.potterlabs.xyz", "reddit.potterlabs.xyz"]
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://reddit.potterlabs.xyz"],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)
```

## 📈 Scaling

### Horizontal Scaling

**Load balancer configuration:**
```yaml
# docker-compose.yml
version: '3.8'
services:
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
    depends_on:
      - api1
      - api2

  api1:
    build: .
    environment:
      - DATABASE_URL=${DATABASE_URL}

  api2:
    build: .
    environment:
      - DATABASE_URL=${DATABASE_URL}
```

### Auto-scaling

**Kubernetes HPA:**
```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: trendit-backend-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: trendit-backend
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
```
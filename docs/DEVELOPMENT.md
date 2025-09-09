# Development Guide

Complete guide for setting up and developing the Trendit backend API locally.

## 🚀 Quick Setup

### Prerequisites
- Python 3.11+
- PostgreSQL (or use Docker)
- Redis (optional, for caching)
- Git

### 1. Clone Repository
```bash
git clone https://github.com/jpotterlabs/trendit-backend.git
cd trendit-backend
```

### 2. Create Virtual Environment
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate     # Windows
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Environment Setup
```bash
# Copy environment template
cp .env.example .env

# Edit with your credentials
nano .env
```

### 5. Database Setup
```bash
# Initialize database
python init_db.py

# Verify setup
python -c "from models.database import engine; print('Database connected!')"
```

### 6. Start Development Server
```bash
uvicorn main:app --reload --port 8000
```

Visit: [http://localhost:8000/docs](http://localhost:8000/docs) for API documentation

## 🗄️ Database Setup Options

### Option 1: Local PostgreSQL

**Install PostgreSQL:**
```bash
# Ubuntu/Debian
sudo apt-get install postgresql postgresql-contrib

# macOS
brew install postgresql

# Start PostgreSQL service
sudo service postgresql start  # Linux
brew services start postgresql # macOS
```

**Create database and user:**
```bash
sudo -u postgres psql

-- In PostgreSQL shell:
CREATE DATABASE trendit_dev;
CREATE USER trendit_user WITH PASSWORD 'dev_password';
GRANT ALL PRIVILEGES ON DATABASE trendit_dev TO trendit_user;
\q
```

**Update .env:**
```bash
DATABASE_URL=postgresql://trendit_user:dev_password@localhost:5432/trendit_dev
```

### Option 2: Docker PostgreSQL

```bash
# Start PostgreSQL in Docker
docker run --name trendit-postgres \
  -e POSTGRES_DB=trendit_dev \
  -e POSTGRES_USER=trendit_user \
  -e POSTGRES_PASSWORD=dev_password \
  -p 5432:5432 \
  -d postgres:15

# Update .env
DATABASE_URL=postgresql://trendit_user:dev_password@localhost:5432/trendit_dev
```

### Option 3: Use Production Database (Neon)

```bash
# Use Neon database for development (not recommended for team work)
# Replace with your own placeholder; never commit secrets
DATABASE_URL=postgresql://<USER>:<PASSWORD>@<HOST>/<DB>?sslmode=require
```

## 🔑 API Credentials Setup

### Reddit API
1. Go to [reddit.com/prefs/apps](https://www.reddit.com/prefs/apps)
2. Click "Create App" or "Create Another App"
3. Choose "web app" type
4. Set redirect URI to `http://localhost:8000/auth/reddit/callback`
5. Copy Client ID and Secret to `.env`

### Auth0 Setup
1. Go to Auth0 Dashboard → Applications
2. Create new "Single Page Application"
3. Configure URLs:
   ```text
   Allowed Callback URLs: http://localhost:3000/auth/callback
   Allowed Web Origins: http://localhost:3000
   Allowed Logout URLs: http://localhost:3000
   ```
4. Copy Domain, Client ID, Client Secret to `.env`

### Complete .env Template
```bash
# Database
DATABASE_URL=postgresql://trendit_user:dev_password@localhost:5432/trendit_dev

# Reddit API
REDDIT_CLIENT_ID=your_reddit_client_id
REDDIT_CLIENT_SECRET=your_reddit_client_secret  
REDDIT_USER_AGENT=TrenditDev/1.0 by /u/yourusername

# Auth0 Configuration
AUTH0_DOMAIN=your-dev-domain.auth0.com
AUTH0_CLIENT_ID=your_auth0_client_id
AUTH0_CLIENT_SECRET=your_auth0_client_secret
# Use your Auth0 API Identifier (https)
AUTH0_AUDIENCE=https://api.potterlabs.xyz

# JWT Configuration
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=1440
JWT_ALGORITHM=HS256
JWT_SECRET_KEY=dev_secret_key_change_in_production

# API Security  
ADMIN_SECRET_KEY=dev_admin_key_change_in_production
API_KEY_SALT=dev_salt_change_in_production

# Development Settings
DEBUG=true
LOG_LEVEL=DEBUG

# Optional: AI Integration
OPENROUTER_API_KEY=your_openrouter_key_optional
```

## 🧪 Testing

### Run All Tests
```bash
python test_api.py
```

### Run Specific Test Files
```bash
# Collection API tests
python test_collection_api.py

# Query API tests  
python test_query_api.py

# Single test function
python -c "import asyncio; from test_api import test_reddit_connection; asyncio.run(test_reddit_connection())"
```

### Test with Pytest (Optional)
```bash
pip install pytest pytest-asyncio
pytest tests/
```

### Manual API Testing

**Create test user:**
```bash
curl -X POST "http://localhost:8000/auth/create-test-user" \
  -H "Content-Type: application/json" \
  -d '{"admin_key": "dev_admin_key_change_in_production"}'
```

**Test endpoints:**
```bash
# Get health status
curl http://localhost:8000/health

# Test authentication
curl -H "Authorization: Bearer <API_KEY>" \
  http://localhost:8000/auth/profile
```

## 🏗️ Project Structure

```text
trendit-backend/
├── main.py                 # FastAPI application entry point
├── models/                 # Database models
│   ├── database.py         # Database connection and base
│   ├── user.py            # User model
│   ├── job.py             # Collection job models
│   └── reddit_data.py     # Reddit data models
├── api/                   # API endpoints
│   ├── auth.py           # Authentication endpoints
│   ├── jobs.py           # Job management endpoints
│   ├── query.py          # Data query endpoints
│   ├── export.py         # Data export endpoints
│   └── analytics.py      # Analytics endpoints
├── services/             # Business logic services
│   ├── auth_service.py   # Authentication logic
│   ├── reddit_client.py  # Reddit API integration
│   ├── data_collector.py # Data collection logic
│   ├── export_service.py # Export functionality
│   └── analytics_service.py # Analytics processing
├── utils/                # Utility functions
│   ├── auth.py          # Auth helpers
│   ├── reddit.py        # Reddit helpers
│   └── database.py      # Database helpers
├── tests/               # Test files
│   ├── test_auth.py    # Authentication tests
│   ├── test_jobs.py    # Job management tests
│   └── test_reddit.py  # Reddit API tests
├── docs/               # Documentation
│   ├── API.md         # API documentation
│   ├── DEPLOYMENT.md  # Deployment guide
│   └── DEVELOPMENT.md # This file
├── requirements.txt    # Python dependencies
├── .env.example       # Environment template
├── init_db.py         # Database initialization
└── README.md          # Main project README
```

## 🔧 Development Tools

### Code Formatting
```bash
# Install formatting tools
pip install black isort flake8

# Format code
black .
isort .

# Check linting
flake8 .
```

### Type Checking
```bash
# Install mypy
pip install mypy

# Run type checking
mypy main.py api/ models/ services/
```

### Pre-commit Hooks
```bash
# Install pre-commit
pip install pre-commit

# Create .pre-commit-config.yaml
echo "repos:
  - repo: https://github.com/psf/black
    rev: 22.10.0
    hooks:
      - id: black
  - repo: https://github.com/pycqa/isort
    rev: 5.10.1
    hooks:
      - id: isort
  - repo: https://github.com/pycqa/flake8
    rev: 5.0.4
    hooks:
      - id: flake8" > .pre-commit-config.yaml

# Install hooks
pre-commit install
```

## 🐞 Debugging

### Enable Debug Mode
```bash
export DEBUG=true
export LOG_LEVEL=DEBUG
uvicorn main:app --reload --log-level debug
```

### Database Query Debugging
```python
import logging
logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)
```

### VS Code Launch Configuration
Create `.vscode/launch.json`:
```json
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "FastAPI Debug",
            "type": "python",
            "request": "launch",
            "module": "uvicorn",
            "args": [
                "main:app",
                "--reload",
                "--port",
                "8000"
            ],
            "env": {
                "DEBUG": "true",
                "LOG_LEVEL": "DEBUG"
            },
            "console": "integratedTerminal"
        }
    ]
}
```

### Request/Response Logging
Add to main.py:
```python
import logging
from fastapi import Request, Response

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

@app.middleware("http")
async def log_requests(request: Request, call_next):
    logger.debug(f"Request: {request.method} {request.url}")
    response = await call_next(request)
    logger.debug(f"Response: {response.status_code}")
    return response
```

## 📊 Performance Profiling

### Basic Performance Testing
```python
import time
import asyncio

async def profile_endpoint():
    start = time.time()
    # Your endpoint code here
    end = time.time()
    print(f"Execution time: {end - start:.2f}s")
```

### Memory Profiling
```bash
pip install memory-profiler

# Add decorator to functions
@profile
def your_function():
    pass

# Run with profiler
python -m memory_profiler your_script.py
```

### Database Query Profiling
```python
from sqlalchemy import event
from sqlalchemy.engine import Engine
import time

@event.listens_for(Engine, "before_cursor_execute")
def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    context._query_start_time = time.time()

@event.listens_for(Engine, "after_cursor_execute") 
def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    total = time.time() - context._query_start_time
    print(f"Query took {total:.4f}s: {statement[:50]}...")
```

## 🔄 Development Workflow

### Feature Development
1. **Create feature branch:**
   ```bash
   git checkout -b feature/new-endpoint
   ```

2. **Write tests first (TDD):**
   ```python
   def test_new_endpoint():
       response = client.get("/api/new-endpoint")
       assert response.status_code == 200
   ```

3. **Implement feature:**
   ```python
   @router.get("/new-endpoint")
   async def new_endpoint():
       return {"message": "Hello World"}
   ```

4. **Test implementation:**
   ```bash
   python test_api.py
   ```

5. **Commit and push:**
   ```bash
   git add .
   git commit -m "Add new endpoint"
   git push origin feature/new-endpoint
   ```

### Code Review Checklist
- [ ] Tests pass locally
- [ ] Code follows PEP 8 style
- [ ] Type hints added to functions
- [ ] Docstrings added to public functions
- [ ] Error handling implemented
- [ ] No secrets in code
- [ ] Database migrations (if needed)

## 🧩 Adding New Features

### New API Endpoint
1. **Add route to appropriate API module:**
   ```python
   # In api/jobs.py
   @router.get("/jobs/{job_id}/status")
   async def get_job_status(job_id: str, current_user: User = Depends(get_current_user)):
       # Implementation here
       pass
   ```

2. **Add Pydantic models:**
   ```python
   # In models/schemas.py
   class JobStatusResponse(BaseModel):
       job_id: str
       status: JobStatus
       progress: float
       created_at: datetime
   ```

3. **Add business logic:**
   ```python
   # In services/job_service.py
   async def get_job_status(job_id: str, user_id: str) -> JobStatusResponse:
       # Business logic here
       pass
   ```

4. **Add tests:**
   ```python
   def test_get_job_status():
       response = client.get("/api/jobs/test_job/status")
       assert response.status_code == 200
       assert response.json()["job_id"] == "test_job"
   ```

### New Database Model
1. **Create model:**
   ```python
   # In models/notification.py
   class Notification(Base):
       __tablename__ = "notifications"
       
       id = Column(Integer, primary_key=True)
       user_id = Column(String, ForeignKey("users.id"))
       message = Column(Text)
       created_at = Column(DateTime, default=datetime.utcnow)
   ```

2. **Add migration:**
   ```python
   # Create migration script or add to init_db.py
   def create_notifications_table():
       # Table creation logic
       pass
   ```

## 🚀 Deployment Testing

### Local Production Testing
```bash
# Test with production-like settings
export DEBUG=false
export LOG_LEVEL=WARNING
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

### Docker Testing
```bash
# Build image
docker build -t trendit-backend-dev .

# Run container
docker run --env-file .env -p 8000:8000 trendit-backend-dev

# Test endpoints
curl http://localhost:8000/health
```

## 📚 Learning Resources

### FastAPI Documentation
- [FastAPI Official Docs](https://fastapi.tiangolo.com/)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)
- [Pydantic Documentation](https://pydantic-docs.helpmanual.io/)

### Reddit API
- [Reddit API Documentation](https://www.reddit.com/dev/api/)
- [PRAW Documentation](https://praw.readthedocs.io/)

### Auth0 Integration
- [Auth0 FastAPI Tutorial](https://auth0.com/docs/quickstart/backend/python)
- [JWT Token Validation](https://auth0.com/docs/tokens/json-web-tokens)

## 🤝 Contributing

1. Fork the repository
2. Create feature branch
3. Make changes with tests
4. Submit pull request
5. Follow code review process

### Pull Request Template
```markdown
## Description
Brief description of changes

## Changes
- [ ] New feature
- [ ] Bug fix  
- [ ] Documentation
- [ ] Refactoring

## Testing
- [ ] Tests added/updated
- [ ] Manual testing completed
- [ ] All tests pass

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Documentation updated
```
# Trendit API Development Guide for Agentic Coding

## Build/Lint/Test Commands

```bash
# Setup
cd backend && pip install -r requirements.txt

# Database
python init_db.py

# Run server
uvicorn main:app --reload --port 8000

# Run all tests
python test_api.py

# Run specific test suites
python test_collection_api.py
python test_query_api.py
python -m pytest  # For pytest-based tests

# Run single test function
python -c "import asyncio; from test_api import test_reddit_connection; asyncio.run(test_reddit_connection())"
```

## Code Style Guidelines

### Imports
- Use absolute imports when possible
- Group imports: standard library, third-party, local
- Import modules, not individual functions when possible
- Use aliases for long module names (e.g., `import pandas as pd`)

### Formatting
- Follow PEP 8
- Use 4 spaces for indentation
- Line length: 88 characters (Black default)
- Use type hints for function parameters and return values
- Use docstrings for all public functions and classes

### Naming Conventions
- Variables/functions: `snake_case`
- Classes: `PascalCase`
- Constants: `UPPER_SNAKE_CASE`
- Private members: prefixed with `_`

### Error Handling
- Use specific exception types
- Log errors with context
- Don't catch generic `Exception` unless re-raising
- Use `finally` blocks for cleanup when needed

### Async Patterns
- Use `async`/`await` consistently
- Prefer async context managers (`async with`)
- Handle async resource cleanup properly

### Database
- Use SQLAlchemy ORM
- Prefer bulk operations for large datasets
- Use transactions for data consistency
- Close sessions properly

### API Design
- Use Pydantic models for request/response validation
- Return consistent error responses
- Use appropriate HTTP status codes
- Document all endpoints with OpenAPI

## Key Files
- `main.py`: FastAPI app setup
- `models/models.py`: Database schema
- `services/data_collector.py`: Core collection logic
- `services/date_filter_fix.py`: Improved date filtering
- `api/*.py`: API endpoints
- `test_*.py`: Test suites
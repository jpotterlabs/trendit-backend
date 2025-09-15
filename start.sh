#!/bin/bash

# Load environment variables from .env file if it exists
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
fi

# Set default port if not specified
PORT=${PORT:-8000}

# Start the FastAPI application with Uvicorn
uvicorn main:app --host 0.0.0.0 --port $PORT --workers 1

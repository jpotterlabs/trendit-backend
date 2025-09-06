"""
Vercel serverless function entry point for FastAPI backend.
"""
from main import app

# Vercel expects a function called 'handler' or the app instance
# This makes the FastAPI app available to Vercel Functions
handler = app
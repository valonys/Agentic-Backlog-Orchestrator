"""
Vercel serverless adapter for the FastAPI backend.
Imports the existing FastAPI app from backend/main.py and exposes it
as a Vercel serverless function.
"""
import sys
import os

# Add the backend directory to the Python path so imports work
backend_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backend")
sys.path.insert(0, backend_dir)

# Set working directory to backend so .env and relative paths resolve
os.chdir(backend_dir)

from main import app  # noqa: E402

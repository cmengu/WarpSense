#!/bin/bash
# Start script for FastAPI backend
# Run this from the backend directory
set -e

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install dependencies if needed
if [ ! -f "venv/.installed" ]; then
    echo "Installing dependencies..."
    pip install -r requirements.txt
    touch venv/.installed
fi

# Run migrations before starting (set -e will exit on failure)
echo "Running database migrations..."
alembic upgrade head

# Start the server
echo "Starting FastAPI server on http://localhost:8000"
echo "API docs available at http://localhost:8000/docs"
uvicorn main:app --reload --host 0.0.0.0 --port 8000

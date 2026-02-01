#!/bin/bash
# Backend test script
# Runs pytest for backend tests

set -e

echo "🧪 Running backend tests..."

cd backend

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "⚠️  Virtual environment not found. Creating one..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install dependencies if needed
if [ ! -f "venv/.deps-installed" ]; then
    echo "📦 Installing dependencies..."
    pip install -r requirements.txt
    touch venv/.deps-installed
fi

# Run tests
pytest tests/ -v

echo "✅ Backend tests passed!"

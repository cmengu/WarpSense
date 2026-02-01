#!/bin/bash
# Automated setup script for FastAPI backend
# Run this when you have internet connectivity

set -e  # Exit on error

echo "🚀 Setting up FastAPI Backend..."
echo ""

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
    echo "✅ Virtual environment created"
else
    echo "✅ Virtual environment already exists"
fi

# Activate virtual environment
echo ""
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo ""
echo "⬆️  Upgrading pip..."
pip install --upgrade pip --quiet

# Install dependencies
echo ""
echo "📥 Installing dependencies..."
pip install -r requirements.txt

# Verify installation
echo ""
echo "✅ Verifying installation..."
python3 -c "from fastapi import FastAPI; print('  ✓ FastAPI installed')" || (echo "  ✗ FastAPI installation failed" && exit 1)
python3 -c "from pydantic import BaseModel; print('  ✓ Pydantic installed')" || (echo "  ✗ Pydantic installation failed" && exit 1)
python3 -c "import uvicorn; print('  ✓ Uvicorn installed')" || (echo "  ✗ Uvicorn installation failed" && exit 1)

echo ""
echo "🎉 Setup complete!"
echo ""
echo "To start the server, run:"
echo "  source venv/bin/activate"
echo "  uvicorn main:app --reload"
echo ""
echo "Or use the start script:"
echo "  ./start.sh"

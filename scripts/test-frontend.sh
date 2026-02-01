#!/bin/bash
# Frontend test script
# Runs Jest for frontend tests

set -e

echo "🧪 Running frontend tests..."

cd my-app

# Install dependencies if needed
if [ ! -d "node_modules" ]; then
    echo "📦 Installing dependencies..."
    npm install
fi

# Run tests
npm test -- --passWithNoTests

echo "✅ Frontend tests passed!"

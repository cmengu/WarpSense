#!/bin/bash
# Start script for both frontend and backend
# Run this from the root directory

echo "🚀 Starting WarpSense development servers..."
echo ""

# Clean up: kill existing processes on 8000/3000, remove Next.js locks
echo "🧹 Cleaning up existing processes..."
lsof -ti:8000 | xargs kill -9 2>/dev/null || true
lsof -ti:3000 | xargs kill -9 2>/dev/null || true
lsof -ti:3001 | xargs kill -9 2>/dev/null || true
lsof -ti:3002 | xargs kill -9 2>/dev/null || true
rm -f my-app/.next/lock my-app/.next/dev/lock 2>/dev/null || true
sleep 1
echo ""

# Check if backend venv exists
if [ ! -d "backend/venv" ]; then
    echo "❌ Backend virtual environment not found!"
    echo "   Run: cd backend && python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt"
    exit 1
fi

# Start backend in background (ENV=development enables seed/wipe routes)
echo "📦 Starting backend on http://localhost:8000..."
cd backend
source venv/bin/activate
ENV=development python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!
cd ..

# Wait a moment for backend to start
sleep 2

# Check if backend started
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo "✅ Backend is running!"
else
    echo "⚠️  Backend may still be starting..."
fi

# Start frontend
echo "🎨 Starting frontend on http://localhost:3000..."
cd my-app
npm run dev &
FRONTEND_PID=$!
cd ..

echo ""
echo "✅ Both servers are starting!"
echo "   Backend:  http://localhost:8000"
echo "   Frontend: http://localhost:3000"
echo ""
echo "Press CTRL+C to stop both servers"
echo "Backend PID: $BACKEND_PID"
echo "Frontend PID: $FRONTEND_PID"

# Wait for interrupt
trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit" INT TERM
wait

# Dashboard API Backend

FastAPI backend for serving dashboard data to the Next.js frontend.

## Setup

1. **Create virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the server:**
   ```bash
   uvicorn main:app --reload
   ```

   Or run directly:
   ```bash
   python main.py
   ```

The server will start on `http://localhost:8000`

## API Endpoints

- `GET /health` - Health check endpoint
- `GET /api/dashboard` - Returns dashboard data (metrics + charts)

## Updating Dashboard Data

Edit `backend/data/mock_data.py` to update dashboard data. The backend will auto-reload (if using `--reload` flag), and the frontend will fetch the updated data on refresh.

## API Documentation

FastAPI automatically generates interactive API documentation:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

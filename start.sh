#!/bin/bash

# PHR Backend Startup Script

echo "Starting PHR Backend API..."

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python -m venv venv
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate || venv\\Scripts\\activate

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Run database migrations
echo "Running database migrations..."
alembic upgrade head

# Start the server
echo "Starting FastAPI server..."
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
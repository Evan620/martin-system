#!/bin/bash

# ECOWAS Backend Server Startup Script
# This script starts the FastAPI backend server with all required dependencies

cd "$(dirname "$0")"

echo "🚀 Starting ECOWAS Backend Server..."
echo ""

# Activate virtual environment
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
    echo "✅ Virtual environment activated"
else
    echo "❌ Virtual environment not found at venv/bin/activate"
    exit 1
fi

# Install critical dependencies if missing
echo ""
echo "📦 Checking critical dependencies..."

pip install -q fastapi uvicorn  2>/dev/null && echo "✅ FastAPI & Uvicorn installed"
pip install -q sqlalchemy alembic asyncpg psycopg2-binary 2>/dev/null && echo "✅ Database libraries installed"
pip install -q email-validator 2>/dev/null && echo "✅ Email validator installed"
pip install -q bcrypt 2>/dev/null && echo "✅ Bcrypt installed"
pip install -q "python-jose[cryptography]" 2>/dev/null && echo "✅ Python-jose installed"
pip install -q icalendar 2>/dev/null && echo "✅ iCalendar installed"
pip install -q passlib 2>/dev/null && echo "✅ Passlib installed"

echo ""
echo "🌐 Starting server at http://localhost:8000"
echo "📚 API docs available at http://localhost:8000/docs"
echo ""
echo "Press CTRL+C to stop the server"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Set PYTHONPATH and start server
# We set PYTHONPATH to the root of the project so that backend.app.main can be found
export PYTHONPATH="$(cd .. && pwd):$(pwd):$PYTHONPATH"
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload --proxy-headers --forwarded-allow-ips='*'

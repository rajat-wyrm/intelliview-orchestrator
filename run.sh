#!/bin/bash

echo "🚀 Starting Answer Evaluation Engine with Dashboard..."
echo "📊 Dashboard will be at: http://127.0.0.1:8000/dashboard"
echo "📖 API Docs will be at: http://127.0.0.1:8000/docs"
echo ""

cd "$(dirname "$0")"

# Auto-seed the database if it doesn't exist
if [ ! -f "evaluation_logs.db" ]; then
    echo "🌱 First run detected. Seeding the database with mock logs..."
    PYTHONPATH=. python3 app/seed.py
fi

PYTHONPATH=. uvicorn app.main:app --reload --port 8000

#!/bin/bash

# Rainmaker Test Runner Script

echo "🧪 Running Rainmaker test suite..."

# Run backend tests
echo "🔧 Running backend tests..."
cd Rainmaker-backend
source venv/bin/activate
pytest tests/ -v --cov=app --cov-report=html
BACKEND_EXIT_CODE=$?

cd ..

# Run frontend tests
echo "🎨 Running frontend tests..."
cd Rainmaker-frontend
npm test -- --run --coverage
FRONTEND_EXIT_CODE=$?

cd ..

# Check results
if [ $BACKEND_EXIT_CODE -eq 0 ] && [ $FRONTEND_EXIT_CODE -eq 0 ]; then
    echo "✅ All tests passed!"
    exit 0
else
    echo "❌ Some tests failed!"
    exit 1
fi
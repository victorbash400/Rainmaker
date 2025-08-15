#!/bin/bash

# Rainmaker Development Setup Script

echo "🚀 Setting up Rainmaker development environment..."

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo "📝 Creating .env file from template..."
    cp .env.example .env
    echo "⚠️  Please update .env file with your actual API keys and configuration"
fi

# Setup backend
echo "🔧 Setting up backend..."
cd Rainmaker-backend

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "🐍 Creating Python virtual environment..."
    python -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install dependencies
echo "📦 Installing Python dependencies..."
pip install -r requirements.txt

cd ..

# Setup frontend
echo "🎨 Setting up frontend..."
cd Rainmaker-frontend

# Install Node.js dependencies
echo "📦 Installing Node.js dependencies..."
npm install

cd ..

# Build and start services
echo "🐳 Building Docker containers..."
docker-compose build

echo "✅ Setup complete!"
echo ""
echo "To start the development environment:"
echo "  docker-compose up -d"
echo ""
echo "To run backend locally:"
echo "  cd Rainmaker-backend && source venv/bin/activate && uvicorn main:app --reload"
echo ""
echo "To run frontend locally:"
echo "  cd Rainmaker-frontend && npm run dev"
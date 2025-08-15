#!/bin/bash

# Rainmaker Deployment Script

ENVIRONMENT=${1:-staging}

echo "🚀 Deploying Rainmaker to $ENVIRONMENT..."

# Validate environment
if [ "$ENVIRONMENT" != "staging" ] && [ "$ENVIRONMENT" != "production" ]; then
    echo "❌ Invalid environment. Use 'staging' or 'production'"
    exit 1
fi

# Run tests first
echo "🧪 Running tests before deployment..."
./scripts/test.sh
if [ $? -ne 0 ]; then
    echo "❌ Tests failed. Deployment aborted."
    exit 1
fi

# Build frontend
echo "🎨 Building frontend..."
cd Rainmaker-frontend
npm run build
cd ..

# Build Docker images
echo "🐳 Building Docker images..."
docker build -t rainmaker-backend:latest ./Rainmaker-backend
docker build -t rainmaker-frontend:latest ./Rainmaker-frontend

# Tag images for environment
docker tag rainmaker-backend:latest rainmaker-backend:$ENVIRONMENT
docker tag rainmaker-frontend:latest rainmaker-frontend:$ENVIRONMENT

echo "✅ Build complete!"
echo "📦 Images tagged for $ENVIRONMENT environment"
echo ""
echo "Next steps:"
echo "1. Push images to container registry"
echo "2. Update ECS service definitions"
echo "3. Deploy to AWS ECS"
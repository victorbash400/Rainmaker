# Rainmaker Technical Stack

## Architecture Overview

Rainmaker uses a modern, scalable architecture with a React frontend and FastAPI backend orchestrating AI agents through LangGraph.

## Frontend Stack

- **Framework**: React 18.2+ with TypeScript
- **Build Tool**: Vite for fast development and optimized builds
- **Styling**: TailwindCSS for utility-first styling
- **State Management**: 
  - Zustand for client state
  - React Query for server state management
- **Real-time**: Socket.io-client for WebSocket connections
- **Testing**: Jest, React Testing Library, Cypress for E2E

## Backend Stack

- **Framework**: FastAPI 0.104+ (Python async web framework)
- **Agent Orchestration**: LangGraph for multi-agent workflows
- **Database**: TiDB Serverless with SQLAlchemy 2.0 async
- **Background Jobs**: Celery + Redis for task processing
- **Real-time**: Socket.io for WebSocket communication
- **Validation**: Pydantic v2 for data models
- **Testing**: pytest, pytest-asyncio, httpx

## Infrastructure

- **Database**: TiDB Serverless (MySQL-compatible, auto-scaling)
- **Cache/Queue**: Redis for caching and job queues
- **File Storage**: AWS S3 for proposals and documents
- **Deployment**: AWS ECS Fargate + Lambda
- **CDN**: CloudFront for frontend assets

## External Integrations

- **AI**: OpenAI API (GPT-4) for agent intelligence
- **Search**: Sonar/Perplexity API for prospect discovery
- **Email**: SendGrid/Mailgun for outreach campaigns
- **Enrichment**: Clearbit API for company data
- **Calendar**: Google Calendar API for scheduling
- **Social**: LinkedIn Sales Navigator API
- **CRM**: HubSpot, Salesforce integration

## MCP (Model Context Protocol) Architecture

All external service integrations use MCP servers for standardized access:

- **Web Search MCP**: Sonar/Perplexity integration
- **Email MCP**: SendGrid/Mailgun integration  
- **Calendar MCP**: Google Calendar integration
- **Database MCP**: TiDB operations with connection pooling
- **File Storage MCP**: AWS S3 operations
- **Enrichment MCP**: Clearbit API wrapper
- **LinkedIn MCP**: Sales Navigator integration
- **Proposal MCP**: PDF generation and templating

## Common Commands

### Development Setup
```bash
# Backend setup
cd Rainmaker-backend
python -m venv venv
venv\Scripts\activate  # Windows
pip install -r requirements.txt
uvicorn main:app --reload

# Frontend setup  
cd Rainmaker-frontend
npm install
npm run dev

# Database migrations
alembic upgrade head

# Run tests
pytest  # Backend
npm test  # Frontend
```

### Production Deployment
```bash
# Build frontend
npm run build

# Deploy to AWS
docker build -t rainmaker-backend .
aws ecs update-service --cluster rainmaker --service backend

# Database backup
pg_dump $DATABASE_URL > backup.sql
```

## Environment Variables

### Required for Development
- `OPENAI_API_KEY`: OpenAI API access
- `TIDB_URL`: TiDB connection string
- `REDIS_URL`: Redis connection string
- `SONAR_API_KEY`: Sonar/Perplexity API key
- `SENDGRID_API_KEY`: Email service API key
- `GOOGLE_CALENDAR_CREDENTIALS`: Calendar API credentials
- `CLEARBIT_API_KEY`: Enrichment API key
- `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY`: S3 access

### Optional for Enhanced Features
- `LINKEDIN_API_KEY`: LinkedIn Sales Navigator
- `HUBSPOT_API_KEY`: CRM integration
- `TWILIO_API_KEY`: SMS notifications

## Code Style Guidelines

- **Python**: Follow PEP 8, use Black formatter, type hints required
- **TypeScript**: Strict mode enabled, ESLint + Prettier
- **Async/Await**: Prefer async patterns throughout
- **Error Handling**: Comprehensive error handling with proper logging
- **Testing**: Minimum 80% code coverage required
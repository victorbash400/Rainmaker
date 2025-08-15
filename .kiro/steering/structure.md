# Rainmaker Project Structure

## Repository Organization

```
Rainmaker/
├── .env.example           # Environment variables template
├── docker-compose.yml     # Local development setup
├── scripts/               # Development scripts
│   ├── setup.sh
│   ├── test.sh
│   └── deploy.sh
├── docs/                  # Documentation
│   ├── API.md
│   ├── DEPLOYMENT.md
│   └── DEVELOPMENT.md
├── .github/               # CI/CD workflows
│   └── workflows/
│       ├── backend.yml
│       └── frontend.yml
├── shared/                # Shared types and constants
│   ├── types/
│   │   ├── api.ts
│   │   └── common.ts
│   └── constants/
│       ├── events.ts
│       └── statuses.ts
├── Rainmaker-backend/     # FastAPI backend application
└── Rainmaker-frontend/    # React frontend application
```

## Backend Structure (Rainmaker-backend/)

```
Rainmaker-backend/
├── app/
│   ├── agents/            # AI agent implementations
│   │   ├── prospect_hunter.py
│   │   ├── enrichment.py
│   │   ├── outreach.py
│   │   ├── conversation.py
│   │   ├── proposal.py
│   │   └── meeting.py
│   ├── api/               # FastAPI route handlers
│   │   ├── v1/
│   │   │   ├── prospects.py
│   │   │   ├── campaigns.py
│   │   │   ├── conversations.py
│   │   │   ├── proposals.py
│   │   │   ├── meetings.py
│   │   │   └── auth.py
│   │   └── deps.py        # Dependency injection
│   ├── core/              # Core application logic
│   │   ├── config.py      # Configuration management
│   │   ├── security.py    # Authentication & authorization
│   │   └── orchestrator.py # LangGraph workflow orchestration
│   ├── db/                # Database layer
│   │   ├── models.py      # SQLAlchemy models
│   │   ├── schemas.py     # Pydantic schemas
│   │   └── session.py     # Database session management
│   ├── mcp/               # MCP server implementations
│   │   ├── web_search.py
│   │   ├── email.py
│   │   ├── calendar.py
│   │   ├── database.py
│   │   ├── enrichment.py
│   │   └── proposal.py
│   ├── services/          # Business logic services
│   │   ├── prospect_service.py
│   │   ├── campaign_service.py
│   │   └── websocket_service.py
│   ├── middleware/        # Custom middleware
│   │   ├── auth.py
│   │   ├── rate_limiting.py
│   │   └── error_handling.py
│   ├── workers/           # Background workers
│   │   ├── agent_worker.py
│   │   └── email_worker.py
│   ├── templates/         # Email and proposal templates
│   │   ├── email/
│   │   │   ├── wedding_outreach.html
│   │   │   ├── corporate_outreach.html
│   │   │   └── follow_up.html
│   │   └── proposals/
│   │       ├── wedding_proposal.html
│   │       └── corporate_proposal.html
│   └── utils/             # Utility functions
│       ├── logging.py
│       └── helpers.py
├── alembic/               # Database migrations
├── tests/                 # Test suite
│   ├── unit/
│   ├── integration/
│   └── e2e/
├── requirements.txt       # Python dependencies
├── Dockerfile            # Container configuration
└── main.py               # Application entry point
```

## Frontend Structure (Rainmaker-frontend/)

```
Rainmaker-frontend/
├── src/
│   ├── components/        # Reusable UI components
│   │   ├── ui/           # Base UI components (buttons, inputs, etc.)
│   │   ├── dashboard/    # Dashboard-specific components
│   │   ├── prospects/    # Prospect management components
│   │   ├── campaigns/    # Campaign management components
│   │   ├── conversations/ # Chat and messaging components
│   │   ├── proposals/    # Proposal builder components
│   │   └── meetings/     # Calendar and meeting components
│   ├── pages/            # Route components
│   │   ├── Dashboard.tsx
│   │   ├── Prospects.tsx
│   │   ├── Campaigns.tsx
│   │   ├── Conversations.tsx
│   │   ├── Proposals.tsx
│   │   ├── Meetings.tsx
│   │   └── Login.tsx
│   ├── layouts/          # Layout components
│   │   ├── DashboardLayout.tsx
│   │   └── AuthLayout.tsx
│   ├── hooks/            # Custom React hooks
│   │   ├── useWebSocket.ts
│   │   ├── useProspects.ts
│   │   ├── useCampaigns.ts
│   │   └── useAuth.ts
│   ├── services/         # API client services
│   │   ├── api.ts        # Base API client
│   │   ├── prospects.ts
│   │   ├── campaigns.ts
│   │   └── websocket.ts
│   ├── store/            # Zustand state management
│   │   ├── authStore.ts
│   │   ├── prospectStore.ts
│   │   └── uiStore.ts
│   ├── lib/              # Utility libraries
│   │   ├── auth.ts
│   │   ├── websocket.ts
│   │   └── constants.ts
│   ├── contexts/         # React contexts
│   │   └── AuthContext.tsx
│   ├── types/            # TypeScript type definitions
│   │   ├── api.ts
│   │   ├── prospect.ts
│   │   ├── campaign.ts
│   │   └── auth.ts
│   ├── utils/            # Utility functions
│   │   ├── formatting.ts
│   │   └── validation.ts
│   ├── App.tsx           # Main application component
│   └── main.tsx          # Application entry point
├── public/               # Static assets
├── tests/                # Test suite
│   ├── components/
│   ├── pages/
│   └── e2e/
├── package.json          # Node.js dependencies
├── vite.config.ts        # Vite configuration
├── tailwind.config.js    # TailwindCSS configuration
└── tsconfig.json         # TypeScript configuration
```

## Configuration Management

### Backend Configuration (app/core/config.py)
```python
class Settings:
    # Database
    TIDB_URL: str
    REDIS_URL: str
    
    # External APIs
    OPENAI_API_KEY: SecretStr
    SONAR_API_KEY: SecretStr
    SENDGRID_API_KEY: SecretStr
    CLEARBIT_API_KEY: SecretStr
    GOOGLE_CALENDAR_CREDENTIALS: SecretStr
    LINKEDIN_API_KEY: SecretStr
    
    # Feature Flags
    ENABLE_AUTOMATIC_OUTREACH: bool = False
    REQUIRE_HUMAN_APPROVAL: bool = True
    
    # Rate Limiting
    MAX_PROSPECTS_PER_DAY: int = 50
    MAX_OUTREACH_PER_HOUR: int = 25
    
    # JWT
    SECRET_KEY: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
```

### Environment Variables (.env.example)
```bash
# Database
TIDB_URL=mysql+pymysql://user:pass@gateway01.us-west-2.prod.aws.tidbcloud.com:4000/rainmaker
REDIS_URL=redis://localhost:6379

# External APIs
OPENAI_API_KEY=sk-...
SONAR_API_KEY=pplx-...
SENDGRID_API_KEY=SG...
CLEARBIT_API_KEY=pk_...
GOOGLE_CALENDAR_CREDENTIALS={"type": "service_account"...}
LINKEDIN_API_KEY=77...

# Feature Flags
ENABLE_AUTOMATIC_OUTREACH=false
REQUIRE_HUMAN_APPROVAL=true

# Security
SECRET_KEY=your-secret-key-here
ACCESS_TOKEN_EXPIRE_MINUTES=1440
```

## Key Architectural Patterns

### Agent-First Design
- Each major business function handled by specialized AI agent
- Agents communicate through shared state managed by LangGraph
- Human-in-the-loop approval points at critical decision stages

### MCP Integration Layer
- All external services accessed through standardized MCP servers
- Consistent error handling, rate limiting, and authentication
- Easy to mock and test individual integrations

### API-First Architecture
- Clean separation between frontend and backend
- RESTful APIs with WebSocket for real-time features
- Comprehensive API documentation with OpenAPI/Swagger

### Database Design
- TiDB Serverless for auto-scaling MySQL-compatible database
- Comprehensive audit trails and activity logging
- Optimized for both transactional and analytical workloads

## File Naming Conventions

- **Python**: snake_case for files, modules, functions, variables
- **TypeScript**: camelCase for variables/functions, PascalCase for components/types
- **Components**: PascalCase with descriptive names (ProspectList.tsx)
- **Hooks**: camelCase starting with "use" (useProspects.ts)
- **Services**: camelCase with "Service" suffix (prospectService.ts)
- **Types**: PascalCase with descriptive names (ProspectData.ts)

## Import Organization

### Python
```python
# Standard library imports
import os
from datetime import datetime

# Third-party imports
from fastapi import FastAPI
from sqlalchemy import Column

# Local imports
from app.core.config import settings
from app.db.models import Prospect
```

### TypeScript
```typescript
// React and third-party imports
import React from 'react'
import { useQuery } from '@tanstack/react-query'

// Local imports
import { Button } from '@/components/ui/Button'
import { useProspects } from '@/hooks/useProspects'
import type { Prospect } from '@/types/prospect'
```

## Development Setup

### Quick Start Scripts
```bash
# Setup development environment
./scripts/setup.sh

# Run tests
./scripts/test.sh

# Deploy to staging
./scripts/deploy.sh staging
```

### Docker Development
```bash
# Start all services
docker-compose up -d

# Backend only
docker-compose up backend redis tidb

# Frontend only
docker-compose up frontend
```
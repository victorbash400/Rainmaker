# Rainmaker Development Guide

## Prerequisites

- Python 3.11+
- Node.js 18+
- Docker and Docker Compose
- Git

## Quick Start

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd Rainmaker
   ```

2. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your API keys and configuration
   ```

3. **Run the setup script**
   ```bash
   ./scripts/setup.sh
   ```

4. **Start the development environment**
   ```bash
   docker-compose up -d
   ```

The application will be available at:
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Documentation: http://localhost:8000/docs

## Development Workflow

### Backend Development

1. **Activate virtual environment**
   ```bash
   cd Rainmaker-backend
   source venv/bin/activate  # Linux/Mac
   venv\Scripts\activate     # Windows
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run database migrations**
   ```bash
   alembic upgrade head
   ```

4. **Start the development server**
   ```bash
   uvicorn main:app --reload
   ```

### Frontend Development

1. **Install dependencies**
   ```bash
   cd Rainmaker-frontend
   npm install
   ```

2. **Start the development server**
   ```bash
   npm run dev
   ```

3. **Run tests**
   ```bash
   npm test
   ```

## Project Structure

```
Rainmaker/
├── Rainmaker-backend/     # FastAPI backend
│   ├── app/
│   │   ├── agents/        # AI agent implementations
│   │   ├── api/           # API route handlers
│   │   ├── core/          # Core application logic
│   │   ├── db/            # Database models and schemas
│   │   ├── mcp/           # MCP server implementations
│   │   └── services/      # Business logic services
│   ├── tests/             # Backend tests
│   └── requirements.txt   # Python dependencies
├── Rainmaker-frontend/    # React frontend
│   ├── src/
│   │   ├── components/    # React components
│   │   ├── pages/         # Page components
│   │   ├── layouts/       # Layout components
│   │   ├── store/         # State management
│   │   └── lib/           # Utility libraries
│   ├── tests/             # Frontend tests
│   └── package.json       # Node.js dependencies
├── shared/                # Shared types and constants
├── scripts/               # Development scripts
└── docs/                  # Documentation
```

## Code Style

### Python (Backend)
- Follow PEP 8 style guide
- Use Black for code formatting
- Use type hints for all functions
- Write docstrings for all public functions

```bash
# Format code
black app/

# Check linting
flake8 app/

# Type checking
mypy app/
```

### TypeScript (Frontend)
- Use ESLint and Prettier for code formatting
- Follow React best practices
- Use TypeScript strict mode
- Write JSDoc comments for complex functions

```bash
# Format code
npm run lint

# Type checking
npm run type-check
```

## Testing

### Backend Tests
```bash
cd Rainmaker-backend
pytest tests/ -v --cov=app
```

### Frontend Tests
```bash
cd Rainmaker-frontend
npm test
npm run test:coverage
```

### End-to-End Tests
```bash
./scripts/test.sh
```

## Database Management

### Create Migration
```bash
cd Rainmaker-backend
alembic revision --autogenerate -m "Description of changes"
```

### Apply Migrations
```bash
alembic upgrade head
```

### Rollback Migration
```bash
alembic downgrade -1
```

## Environment Variables

### Required Variables
- `OPENAI_API_KEY`: OpenAI API key for AI agents
- `TIDB_URL`: Database connection string
- `REDIS_URL`: Redis connection string
- `SECRET_KEY`: JWT secret key

### Optional Variables
- `SONAR_API_KEY`: Sonar/Perplexity API key
- `SENDGRID_API_KEY`: SendGrid API key
- `CLEARBIT_API_KEY`: Clearbit API key
- `GOOGLE_CALENDAR_CREDENTIALS`: Google Calendar API credentials

## Debugging

### Backend Debugging
1. Set `DEBUG=true` in `.env`
2. Use Python debugger: `import pdb; pdb.set_trace()`
3. Check logs: `docker-compose logs backend`

### Frontend Debugging
1. Use browser developer tools
2. Check console for errors
3. Use React Developer Tools extension

## Common Issues

### Port Already in Use
```bash
# Kill process using port 8000
lsof -ti:8000 | xargs kill -9

# Kill process using port 3000
lsof -ti:3000 | xargs kill -9
```

### Database Connection Issues
1. Check TiDB connection string in `.env`
2. Verify database is running
3. Check firewall settings

### API Key Issues
1. Verify all required API keys are set in `.env`
2. Check API key permissions and quotas
3. Test API keys with curl commands

## Contributing

1. Create a feature branch from `main`
2. Make your changes
3. Write tests for new functionality
4. Run the test suite
5. Submit a pull request

## Deployment

See [DEPLOYMENT.md](./DEPLOYMENT.md) for production deployment instructions.
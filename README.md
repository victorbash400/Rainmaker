# Rainmaker

AI-powered event planning sales assistant that automates the entire sales pipeline from prospect discovery through deal closure.

## 🚀 Features

- **Automated Prospect Discovery**: Find potential clients through social media signals and event listings
- **Intelligent Enrichment**: Research and enhance prospect information with event requirements
- **Personalized Outreach**: Generate event-type specific messages across multiple channels
- **Smart Conversations**: Handle prospect inquiries and gather detailed requirements
- **Dynamic Proposals**: Create customized event proposals with comprehensive packages and pricing
- **Seamless Scheduling**: Automate consultation and venue visit scheduling
- **Real-Time Dashboard**: Monitor prospect pipeline, campaign performance, and agent activities
- **Human Oversight**: Built-in approval workflows to maintain quality and compliance

## 🏗️ Architecture

- **Frontend**: React 18 + TypeScript + Vite + TailwindCSS
- **Backend**: FastAPI + Python 3.11 + SQLAlchemy 2.0
- **Database**: TiDB Serverless (MySQL-compatible)
- **Cache/Queue**: Redis + Celery
- **AI Orchestration**: LangGraph with specialized agents
- **External Integrations**: MCP (Model Context Protocol) servers
- **Deployment**: AWS ECS Fargate + S3 + CloudFront

## 🛠️ Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- Docker and Docker Compose
- OpenAI API key

### Setup

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

5. **Access the application**
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - API Documentation: http://localhost:8000/docs

### Demo Login
- Email: `admin@rainmaker.com`
- Password: `password`

## 📁 Project Structure

```
Rainmaker/
├── Rainmaker-backend/     # FastAPI backend application
│   ├── app/
│   │   ├── agents/        # AI agent implementations
│   │   ├── api/           # API route handlers
│   │   ├── core/          # Core application logic
│   │   ├── db/            # Database models and schemas
│   │   ├── mcp/           # MCP server implementations
│   │   └── services/      # Business logic services
│   └── tests/             # Backend tests
├── Rainmaker-frontend/    # React frontend application
│   ├── src/
│   │   ├── components/    # React components
│   │   ├── pages/         # Page components
│   │   ├── layouts/       # Layout components
│   │   ├── store/         # State management (Zustand)
│   │   └── lib/           # Utility libraries
│   └── tests/             # Frontend tests
├── shared/                # Shared types and constants
├── scripts/               # Development scripts
├── docs/                  # Documentation
└── .github/               # CI/CD workflows
```

## 🤖 AI Agents

Rainmaker uses specialized AI agents orchestrated by LangGraph:

1. **Prospect Hunter Agent**: Discovers potential clients through social media and event listings
2. **Enrichment Agent**: Researches and enhances prospect information
3. **Outreach Agent**: Generates and sends personalized messages
4. **Conversation Agent**: Handles prospect responses and gathers requirements
5. **Proposal Agent**: Creates customized event proposals
6. **Meeting Agent**: Schedules consultations and manages calendar integration

## 🔌 MCP Integration

All external services are accessed through standardized MCP (Model Context Protocol) servers:

- **Web Search MCP**: Sonar/Perplexity API integration
- **Email MCP**: SendGrid/Mailgun integration
- **Calendar MCP**: Google Calendar integration
- **Database MCP**: TiDB operations with connection pooling
- **File Storage MCP**: AWS S3 operations
- **Enrichment MCP**: Clearbit API wrapper
- **LinkedIn MCP**: Sales Navigator integration
- **Proposal MCP**: PDF generation and templating

## 🧪 Testing

### Run All Tests
```bash
./scripts/test.sh
```

### Backend Tests
```bash
cd Rainmaker-backend
pytest tests/ -v --cov=app
```

### Frontend Tests
```bash
cd Rainmaker-frontend
npm test
```

## 📚 Documentation

- [API Documentation](docs/API.md)
- [Development Guide](docs/DEVELOPMENT.md)
- [Deployment Guide](docs/DEPLOYMENT.md)

## 🚀 Deployment

Rainmaker is designed for AWS deployment:

1. **Backend**: ECS Fargate with Application Load Balancer
2. **Frontend**: S3 + CloudFront
3. **Database**: TiDB Serverless
4. **Cache**: Redis ElastiCache

See [DEPLOYMENT.md](docs/DEPLOYMENT.md) for detailed instructions.

## 🔧 Configuration

### Required Environment Variables

```bash
# Core
OPENAI_API_KEY=sk-your-openai-api-key
TIDB_URL=mysql+pymysql://user:pass@host:port/database
REDIS_URL=redis://localhost:6379
SECRET_KEY=your-secret-key

# External APIs (Optional)
SONAR_API_KEY=pplx-your-sonar-key
SENDGRID_API_KEY=SG.your-sendgrid-key
CLEARBIT_API_KEY=pk_your-clearbit-key
GOOGLE_CALENDAR_CREDENTIALS={"type": "service_account"...}
LINKEDIN_API_KEY=your-linkedin-key

# AWS
AWS_ACCESS_KEY_ID=your-aws-access-key
AWS_SECRET_ACCESS_KEY=your-aws-secret-key
AWS_S3_BUCKET=your-s3-bucket
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

- 📧 Email: support@rainmaker.com
- 📖 Documentation: [docs/](docs/)
- 🐛 Issues: [GitHub Issues](https://github.com/your-org/rainmaker/issues)

## 🎯 Roadmap

- [ ] Advanced analytics and reporting
- [ ] Multi-language support
- [ ] Mobile application
- [ ] Webhook integrations
- [ ] Advanced AI model fine-tuning
- [ ] Enterprise SSO integration

---

Built with ❤️ for event planning professionals
# Concept - AI-Powered Learning Platform

A modern, full-stack educational platform powered by AI tutoring capabilities. Built with React, TypeScript, and Node.js following professional software development practices.

## Project Overview

Concept is a sophisticated learning management system that leverages AI to provide personalized tutoring experiences. The platform combines an elegant, brutalist UI/UX design with a robust backend infrastructure.

**Key Features:**
- AI-powered personalized tutoring
- Interactive concept learning roadmaps
- Real-time chat-based learning interface
- Learning progress tracking and analytics
- High-contrast, accessible design system

## Quick Start

See [GETTING_STARTED.md](GETTING_STARTED.md) for rapid setup (5 minutes)

## Documentation

Complete documentation is available in the `/docs` directory:

- [GETTING_STARTED.md](GETTING_STARTED.md) - Quick start guide
- [REPOSITORY_OVERVIEW.md](REPOSITORY_OVERVIEW.md) - Complete transformation summary
- [docs/DEVELOPMENT_SETUP.md](docs/DEVELOPMENT_SETUP.md) - Detailed setup instructions
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) - System design and architecture
- [docs/API.md](docs/API.md) - Complete API reference
- [docs/PROJECT_STRUCTURE.md](docs/PROJECT_STRUCTURE.md) - Project organization
- [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) - Deployment procedures
- [CONTRIBUTING.md](CONTRIBUTING.md) - Development guidelines

## Technology Stack

**Frontend:**
- React 18+
- TypeScript
- Tailwind CSS
- Shadcn/ui Components

**Backend:**
- Node.js
- Express.js
- PostgreSQL
- Redis

**Tools:**
- Jest (Testing)
- ESLint (Linting)
- Prettier (Formatting)
- Docker (Deployment)

## Core Commands

```bash
# Development
npm run dev              # Run frontend and backend
npm run dev --workspace=frontend  # Frontend only
npm run dev --workspace=backend   # Backend only

# Testing
npm run test            # Run all tests
npm run test:coverage   # Coverage report
npm run test:e2e        # E2E tests

# Code Quality
npm run lint            # ESLint check
npm run format          # Format code
npm run type-check      # TypeScript check
npm run check           # All checks

# Production
npm run build           # Build for production
npm start               # Start production server
```

## Architecture

```
Frontend (React SPA)
    ↓
API Gateway (Express.js)
    ↓
├── Auth Service
├── Concept Service
├── Tutor Service (AI)
└── User Service
    ↓
Database (PostgreSQL) + Cache (Redis)
```

Detailed architecture at [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)

## API Endpoints

Base URL: `http://localhost:5000/api/v1`

Key endpoints:
- `POST /auth/login` - User authentication
- `GET /concepts` - List concepts
- `POST /tutor/chat` - AI tutoring chat
- `GET /users/me` - Current user profile

Full API documentation: [docs/API.md](docs/API.md)

## Project Structure

```
Concept/
├── frontend/           # React + TypeScript SPA
├── backend/            # Node.js API
├── tests/              # E2E tests
├── docs/               # Documentation
├── design_guidelines.json
└── Configuration files
```

Complete structure: [docs/PROJECT_STRUCTURE.md](docs/PROJECT_STRUCTURE.md)

## Development Workflow

1. Create feature branch: `git checkout -b feature/your-feature`
2. Make changes and write tests
3. Run checks: `npm run check`
4. Commit: `git commit -m "feat: description"`
5. Push and create PR

See [CONTRIBUTING.md](CONTRIBUTING.md) for complete guidelines.

## Quality Standards

- TypeScript strict mode
- 80%+ test coverage required
- ESLint configuration enforced
- Prettier formatting enforced
- WCAG 2.1 AA accessibility
- Security best practices

## Deployment

**Frontend:** Vercel/Netlify
**Backend:** Docker/Kubernetes
**Database:** Managed PostgreSQL

See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) for details.

## Configuration

Copy environment template and configure:
```bash
cp .env.example .env
```

See [docs/DEVELOPMENT_SETUP.md](docs/DEVELOPMENT_SETUP.md) for details.

## Security

- JWT authentication
- CORS configuration
- Input validation
- Rate limiting
- Environment variable management
- HTTPS/TLS in production

## Support

- Review documentation in `/docs`
- Check existing GitHub issues
- Follow development guidelines in CONTRIBUTING.md
- See REPOSITORY_OVERVIEW.md for project setup details

## Version

- Current: 1.0.0
- Status: Development Ready
- Last Updated: June 2026

## License

Proprietary and Confidential

---

**Getting Started?** Start with [GETTING_STARTED.md](GETTING_STARTED.md)

**Interested in Contributing?** See [CONTRIBUTING.md](CONTRIBUTING.md)

**Need Technical Details?** Check [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)

**Want the Full Story?** Read [REPOSITORY_OVERVIEW.md](REPOSITORY_OVERVIEW.md)

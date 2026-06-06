# Project Structure Guide

This document provides a detailed explanation of the Concept project structure and the purpose of each directory and file.

## Root Directory

```
Concept/
├── .env.example              # Environment variables template
├── .eslintrc.json           # ESLint configuration
├── .gitconfig               # Git configuration
├── .gitignore               # Git ignore rules
├── .prettierrc.json         # Prettier code formatter config
├── CHANGELOG.md             # Version history and changes
├── CONTRIBUTING.md          # Contribution guidelines
├── README.md                # Project overview and setup
├── package.json             # Root package manager config (monorepo)
├── tsconfig.json            # Root TypeScript configuration
├── design_guidelines.json   # UI/UX design system specification
├── frontend/                # React + TypeScript frontend
├── backend/                 # Node.js + Express backend
├── tests/                   # Shared/integration tests
├── memory/                  # Agent memory & context
├── test_reports/            # Test execution reports
└── docs/                    # Project documentation
```

## Frontend (`/frontend`)

React-based single-page application with TypeScript.

```
frontend/
├── public/
│   ├── index.html
│   ├── favicon.ico
│   └── assets/              # Static assets (images, fonts)
│
├── src/
│   ├── components/
│   │   ├── Common/          # Reusable components (Button, Input, etc.)
│   │   ├── Layout/          # Layout components (Header, Sidebar, etc.)
│   │   ├── Features/        # Feature-specific components
│   │   └── __tests__/       # Component tests
│   │
│   ├── pages/
│   │   ├── Home.tsx         # Landing page
│   │   ├── Dashboard.tsx    # Main dashboard
│   │   ├── Search.tsx       # Concept search
│   │   ├── Learning.tsx     # Learning interface
│   │   ├── Profile.tsx      # User profile
│   │   └── NotFound.tsx     # 404 page
│   │
│   ├── hooks/
│   │   ├── useAuth.ts       # Authentication hook
│   │   ├── useSearch.ts     # Search functionality
│   │   ├── useTutor.ts      # AI tutor integration
│   │   └── index.ts         # Export all hooks
│   │
│   ├── context/
│   │   ├── AuthContext.tsx  # Authentication context
│   │   ├── ThemeContext.tsx # Theme context
│   │   └── index.ts         # Export all contexts
│   │
│   ├── services/
│   │   ├── api/
│   │   │   ├── client.ts    # API client setup
│   │   │   ├── concepts.ts  # Concepts endpoints
│   │   │   ├── auth.ts      # Auth endpoints
│   │   │   └── index.ts     # Export all services
│   │   │
│   │   ├── storage.ts       # LocalStorage/SessionStorage
│   │   └── logger.ts        # Logging service
│   │
│   ├── types/
│   │   ├── api.ts           # API response types
│   │   ├── domain.ts        # Domain models
│   │   ├── ui.ts            # UI component types
│   │   └── index.ts         # Type exports
│   │
│   ├── styles/
│   │   ├── globals.css      # Global styles
│   │   ├── tailwind.config.js
│   │   ├── postcss.config.js
│   │   └── variables.css    # CSS custom properties
│   │
│   ├── utils/
│   │   ├── formatters.ts    # Data formatting utilities
│   │   ├── validators.ts    # Input validation
│   │   ├── constants.ts     # App constants
│   │   └── helpers.ts       # Helper functions
│   │
│   ├── __tests__/
│   │   ├── setup.ts         # Test setup
│   │   ├── fixtures.ts      # Test fixtures/mocks
│   │   └── utils.ts         # Test utilities
│   │
│   ├── App.tsx              # Root component
│   ├── App.test.tsx         # App tests
│   ├── index.tsx            # Entry point
│   ├── react-app-env.d.ts   # React type definitions
│   └── vite-env.d.ts        # Vite type definitions (if using Vite)
│
├── package.json             # Frontend dependencies
├── tsconfig.json            # Frontend TypeScript config
├── vite.config.ts           # Vite configuration (if using Vite)
├── .env.example             # Frontend environment template
├── .eslintrc.json           # Frontend-specific ESLint rules
└── README.md                # Frontend-specific documentation
```

## Backend (`/backend`)

Node.js/Express API server with TypeScript.

```
backend/
├── src/
│   ├── controllers/
│   │   ├── authController.ts      # Authentication logic
│   │   ├── conceptController.ts   # Concept CRUD operations
│   │   ├── tutorController.ts     # AI tutor endpoints
│   │   ├── userController.ts      # User management
│   │   └── index.ts               # Export all controllers
│   │
│   ├── services/
│   │   ├── authService.ts         # Auth business logic
│   │   ├── conceptService.ts      # Concept business logic
│   │   ├── tutorService.ts        # AI tutor integration
│   │   ├── emailService.ts        # Email sending
│   │   └── index.ts               # Export all services
│   │
│   ├── models/
│   │   ├── User.ts                # User schema/model
│   │   ├── Concept.ts             # Concept schema/model
│   │   ├── Roadmap.ts             # Learning roadmap
│   │   ├── ChatMessage.ts         # Chat messages
│   │   └── index.ts               # Export all models
│   │
│   ├── middleware/
│   │   ├── auth.ts                # Authentication middleware
│   │   ├── errorHandler.ts        # Error handling
│   │   ├── validation.ts          # Request validation
│   │   ├── logging.ts             # Request logging
│   │   ├── cors.ts                # CORS configuration
│   │   └── index.ts               # Export all middleware
│   │
│   ├── routes/
│   │   ├── auth.ts                # Auth routes
│   │   ├── concepts.ts            # Concept routes
│   │   ├── tutor.ts               # Tutor routes
│   │   ├── users.ts               # User routes
│   │   └── index.ts               # Register all routes
│   │
│   ├── utils/
│   │   ├── db.ts                  # Database connection
│   │   ├── cache.ts               # Caching utilities
│   │   ├── validators.ts          # Input validators
│   │   ├── jwt.ts                 # JWT utilities
│   │   ├── logger.ts              # Logging setup
│   │   └── constants.ts           # Constants
│   │
│   ├── types/
│   │   ├── express.d.ts           # Express type extensions
│   │   ├── api.ts                 # API types
│   │   ├── domain.ts              # Domain models
│   │   └── index.ts               # Type exports
│   │
│   ├── config/
│   │   ├── env.ts                 # Environment config
│   │   ├── database.ts            # Database config
│   │   ├── cors.ts                # CORS config
│   │   └── index.ts               # Export all config
│   │
│   ├── __tests__/
│   │   ├── setup.ts               # Test setup
│   │   ├── fixtures.ts            # Test fixtures
│   │   ├── mocks.ts               # Mock functions
│   │   ├── integration/           # Integration tests
│   │   └── unit/                  # Unit tests
│   │
│   ├── app.ts                     # Express app setup
│   └── index.ts                   # Server entry point
│
├── prisma/
│   ├── schema.prisma              # Database schema (if using Prisma)
│   └── migrations/                # Database migrations
│
├── package.json                   # Backend dependencies
├── tsconfig.json                  # Backend TypeScript config
├── jest.config.js                 # Jest configuration
├── .env.example                   # Backend environment template
├── .eslintrc.json                 # Backend-specific ESLint
├── Dockerfile                     # Docker configuration
└── README.md                      # Backend-specific documentation
```

## Tests (`/tests`)

Integration and end-to-end tests.

```
tests/
├── e2e/
│   ├── auth.cy.ts                 # Authentication E2E tests
│   ├── search.cy.ts               # Search functionality E2E
│   ├── learning.cy.ts             # Learning flow E2E
│   └── fixtures.ts                # Test data
│
├── integration/
│   ├── api.test.ts                # API integration tests
│   ├── database.test.ts           # Database operations
│   └── fixtures.ts
│
├── support/
│   ├── commands.ts                # Custom Cypress commands
│   └── e2e.ts                     # E2E support setup
│
└── cypress.config.ts              # Cypress configuration
```

## Memory (`/memory`)

Agent memory and context management for AI operations.

```
memory/
├── context/
│   ├── project_context.md         # Overall project context
│   ├── current_state.md           # Current development state
│   └── decisions.md               # Key decisions made
│
├── conversations/
│   └── [session-id]/              # Conversation history
│
└── knowledge_base/
    ├── architecture.md            # System architecture notes
    ├── api_reference.md           # API documentation
    └── troubleshooting.md         # Known issues & solutions
```

## Documentation (`/docs`)

Additional project documentation.

```
docs/
├── ARCHITECTURE.md                # System architecture
├── API.md                         # API endpoints documentation
├── DATABASE.md                    # Database schema documentation
├── DEPLOYMENT.md                  # Deployment procedures
├── DEVELOPMENT.md                 # Development workflow
├── TESTING.md                     # Testing strategies
├── PERFORMANCE.md                 # Performance guidelines
├── SECURITY.md                    # Security practices
├── TROUBLESHOOTING.md             # Common issues & solutions
└── GLOSSARY.md                    # Project terminology
```

## Configuration Files

| File | Purpose |
|------|---------|
| `.env.example` | Template for environment variables |
| `.eslintrc.json` | ESLint code quality rules |
| `.gitconfig` | Git configuration |
| `.gitignore` | Files/folders to ignore in Git |
| `.prettierrc.json` | Code formatting rules |
| `tsconfig.json` | TypeScript compiler options |
| `package.json` | Node.js dependencies and scripts |
| `design_guidelines.json` | UI/UX design specifications |

## Key Principles

1. **Separation of Concerns**: Each directory has a clear, single responsibility
2. **Type Safety**: All code uses TypeScript with strict mode enabled
3. **Test Coverage**: Tests live alongside their modules
4. **Scalability**: Structure supports monorepo growth
5. **Documentation**: Configuration files are self-documenting
6. **Consistency**: Naming conventions are consistent across directories

## Adding New Features

When adding new features, follow this structure:

1. **Backend**: Create service + controller + routes
2. **Frontend**: Create page/component + hooks + types
3. **Tests**: Add unit + integration tests
4. **Docs**: Update relevant documentation
5. **Design**: Ensure compliance with design_guidelines.json

## File Naming Conventions

- **Components**: PascalCase (e.g., `SearchInput.tsx`)
- **Utilities/Services**: camelCase (e.g., `formatDate.ts`)
- **Types**: PascalCase with `.d.ts` or in `types/` (e.g., `UserType.ts`)
- **Constants**: UPPER_SNAKE_CASE (e.g., `API_BASE_URL`)
- **Tests**: Same name as file + `.test.ts` or `.spec.ts`

## Import Organization

```typescript
// 1. External dependencies
import React from 'react';
import { useQuery } from '@tanstack/react-query';

// 2. Internal imports (absolute paths)
import { Button } from '@/components/Button';
import { useAuth } from '@/hooks/useAuth';

// 3. Types
import type { User } from '@/types/domain';

// 4. Styles (if applicable)
import styles from './Component.module.css';
```

For more information, see the main [README.md](../README.md) and specific directory READMEs.

# ConceptForge — Product Requirements Document

## Original Problem Statement
> Create an AI app where you just put concept name and it will generate roadmap, videos, images, study guides and gave you tutor based on your level of knowledge.

## Architecture
- **Backend**: FastAPI (Python) on port 8001, MongoDB via motor (async), JWT (cookie + bearer) auth, emergentintegrations LLM library.
- **Frontend**: React 19, react-router-dom v7, Tailwind, Shadcn UI primitives + custom brutalist Swiss design.
- **AI Providers**:
  - Text (roadmap, study guide, tutor): Claude Sonnet 4.5 (`anthropic/claude-sonnet-4-6`) via Emergent Universal Key.
  - Images: Gemini Nano Banana (`gemini-3.1-flash-image-preview`) via Emergent Universal Key.
  - Videos: Curated YouTube via `yt-dlp` ytsearch (no API key needed).

## User Personas
1. **Self-learner** — types any topic and wants a structured starting point.
2. **Student** — uses the tutor chat to clarify concepts at their level.
3. **Curious professional** — saves multiple concepts to revisit.

## Core Requirements (static)
- Single-input concept generation flow.
- Knowledge-level selector (beginner / intermediate / advanced).
- Outputs: roadmap, study guide, image, videos, tutor.
- Authenticated dashboard storing user's concepts.
- Tutor chat persistence per concept.

## Implemented (2026-02-XX, iteration 1)
- JWT email/password auth: register/login/logout/me, bcrypt hashing, admin seed.
- Concept generation pipeline: roadmap → (study guide || image || videos) in parallel.
- Endpoints: `/api/concepts/generate`, `GET/DELETE /api/concepts/{id}`, `GET /api/concepts`.
- Tutor chat: `POST/GET /api/concepts/{id}/chat` with history replay.
- Brutalist Swiss landing page with hero, sample output card, features grid, process steps, CTA footer.
- Authenticated dashboard with generator + saved-library grid.
- Concept detail page with 5 tabs (Roadmap / Study Guide / Videos / Image / Tutor).
- Multi-step "terminal" loader during generation.
- 17/17 backend tests passing (auth, generation, listing, deletion, tutor, cross-user access control).

## Backlog (priority order)
- **P1** — Streaming tutor responses (SSE) for snappier UX.
- **P1** — Progress checkboxes on roadmap milestones (mark complete).
- **P1** — Share public concept link (read-only).
- **P2** — Re-generate single section (e.g. regenerate image, or refresh videos).
- **P2** — Search & filter the saved library.
- **P2** — Export concept to PDF/Markdown.
- **P2** — Brute-force lockout on login (5 fails → 15 min).
- **P3** — Migrate to FastAPI lifespan, split server.py into modules.
- **P3** — Add Stripe billing for pro tier (unlimited generations, gpt-image-1).

## Test Credentials
See `/app/memory/test_credentials.md`.

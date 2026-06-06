# API Documentation

This document describes all API endpoints available in the Concept platform.

## Base URL

All API requests should be made to:
```
http://localhost:5000/api/v1
```

In production, replace `localhost:5000` with your production domain.

## Authentication

Most endpoints require authentication using JWT tokens.

### Getting a Token

```http
POST /auth/login
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "password123"
}
```

Response:
```json
{
  "token": "eyJhbGciOiJIUzI1NiIs...",
  "refreshToken": "eyJhbGciOiJIUzI1NiIs...",
  "user": {
    "id": "user-123",
    "email": "user@example.com",
    "name": "John Doe"
  }
}
```

### Using the Token

Include the token in the Authorization header:
```http
GET /concepts HTTP/1.1
Authorization: Bearer eyJhbGciOiJIUzI1NiIs...
```

## Authentication Endpoints

### Register User

```http
POST /auth/register
Content-Type: application/json

{
  "email": "newuser@example.com",
  "password": "securepassword",
  "name": "New User"
}
```

Response: `201 Created`
```json
{
  "user": {
    "id": "user-124",
    "email": "newuser@example.com",
    "name": "New User"
  },
  "token": "eyJhbGciOiJIUzI1NiIs..."
}
```

### Login

```http
POST /auth/login
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "password123"
}
```

Response: `200 OK`
```json
{
  "token": "eyJhbGciOiJIUzI1NiIs...",
  "refreshToken": "eyJhbGciOiJIUzI1NiIs...",
  "user": {
    "id": "user-123",
    "email": "user@example.com",
    "name": "John Doe"
  }
}
```

### Logout

```http
POST /auth/logout
Authorization: Bearer <token>
```

Response: `204 No Content`

### Refresh Token

```http
POST /auth/refresh-token
Content-Type: application/json

{
  "refreshToken": "eyJhbGciOiJIUzI1NiIs..."
}
```

Response: `200 OK`
```json
{
  "token": "eyJhbGciOiJIUzI1NiIs...",
  "refreshToken": "eyJhbGciOiJIUzI1NiIs..."
}
```

## Concepts Endpoints

### List Concepts

```http
GET /concepts?page=1&limit=10&search=react
Authorization: Bearer <token>
```

Query Parameters:
- `page` (optional): Page number (default: 1)
- `limit` (optional): Items per page (default: 10)
- `search` (optional): Search term
- `category` (optional): Filter by category

Response: `200 OK`
```json
{
  "data": [
    {
      "id": "concept-1",
      "title": "React Fundamentals",
      "description": "Learn the basics of React",
      "category": "frontend",
      "difficulty": "beginner",
      "createdAt": "2026-06-01T10:00:00Z"
    }
  ],
  "pagination": {
    "page": 1,
    "limit": 10,
    "total": 42,
    "pages": 5
  }
}
```

### Get Concept

```http
GET /concepts/:id
Authorization: Bearer <token>
```

Response: `200 OK`
```json
{
  "id": "concept-1",
  "title": "React Fundamentals",
  "description": "Learn the basics of React",
  "category": "frontend",
  "difficulty": "beginner",
  "content": "Detailed content here...",
  "createdAt": "2026-06-01T10:00:00Z",
  "updatedAt": "2026-06-01T10:00:00Z"
}
```

### Create Concept

```http
POST /concepts
Authorization: Bearer <token>
Content-Type: application/json

{
  "title": "New Concept",
  "description": "Description",
  "category": "frontend",
  "difficulty": "beginner",
  "content": "Content here..."
}
```

Response: `201 Created`

### Update Concept

```http
PUT /concepts/:id
Authorization: Bearer <token>
Content-Type: application/json

{
  "title": "Updated Title",
  "description": "Updated description"
}
```

Response: `200 OK`

### Delete Concept

```http
DELETE /concepts/:id
Authorization: Bearer <token>
```

Response: `204 No Content`

## Tutor Endpoints

### Send Chat Message

```http
POST /tutor/chat
Authorization: Bearer <token>
Content-Type: application/json

{
  "message": "Explain React hooks",
  "conceptId": "concept-1",
  "conversationId": "conv-123"
}
```

Response: `200 OK`
```json
{
  "response": "React hooks are functions that let you use state...",
  "conversationId": "conv-123",
  "timestamp": "2026-06-06T10:30:00Z"
}
```

### Get Chat History

```http
GET /tutor/history/:conversationId
Authorization: Bearer <token>
```

Query Parameters:
- `limit` (optional): Number of messages (default: 50)
- `offset` (optional): Pagination offset (default: 0)

Response: `200 OK`
```json
{
  "messages": [
    {
      "id": "msg-1",
      "role": "user",
      "content": "Explain React hooks",
      "timestamp": "2026-06-06T10:30:00Z"
    },
    {
      "id": "msg-2",
      "role": "assistant",
      "content": "React hooks are functions that let you use state...",
      "timestamp": "2026-06-06T10:30:05Z"
    }
  ],
  "total": 2
}
```

### Get Learning Roadmap

```http
GET /tutor/roadmap/:conceptId
Authorization: Bearer <token>
```

Query Parameters:
- `userLevel` (optional): User's knowledge level (beginner|intermediate|advanced)

Response: `200 OK`
```json
{
  "conceptId": "concept-1",
  "nodes": [
    {
      "id": "node-1",
      "title": "Basics",
      "description": "Learn the basics",
      "level": 1,
      "children": ["node-2"]
    },
    {
      "id": "node-2",
      "title": "Intermediate",
      "description": "Advanced concepts",
      "level": 2,
      "children": []
    }
  ]
}
```

## User Endpoints

### Get Current User

```http
GET /users/me
Authorization: Bearer <token>
```

Response: `200 OK`
```json
{
  "id": "user-123",
  "email": "user@example.com",
  "name": "John Doe",
  "profilePicture": "https://...",
  "joinedAt": "2026-01-01T10:00:00Z"
}
```

### Update User Profile

```http
PUT /users/me
Authorization: Bearer <token>
Content-Type: application/json

{
  "name": "Jane Doe",
  "profilePicture": "https://..."
}
```

Response: `200 OK`

### Get User Progress

```http
GET /users/:id/progress
Authorization: Bearer <token>
```

Response: `200 OK`
```json
{
  "userId": "user-123",
  "concepts": [
    {
      "conceptId": "concept-1",
      "title": "React Fundamentals",
      "progress": 75,
      "status": "in_progress",
      "completedAt": null
    }
  ],
  "totalProgress": 45,
  "streak": 5
}
```

## Error Responses

### 400 Bad Request

```json
{
  "error": "Bad Request",
  "message": "Invalid request parameters",
  "details": {
    "field": "email",
    "issue": "Invalid email format"
  }
}
```

### 401 Unauthorized

```json
{
  "error": "Unauthorized",
  "message": "Invalid or missing authentication token"
}
```

### 403 Forbidden

```json
{
  "error": "Forbidden",
  "message": "You do not have permission to access this resource"
}
```

### 404 Not Found

```json
{
  "error": "Not Found",
  "message": "The requested resource was not found"
}
```

### 500 Internal Server Error

```json
{
  "error": "Internal Server Error",
  "message": "An unexpected error occurred"
}
```

## Rate Limiting

API requests are rate limited to prevent abuse:

- **Standard**: 100 requests per 15 minutes per IP
- **Authenticated**: 1000 requests per 15 minutes per user

Rate limit information is included in response headers:
```http
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1623000000
```

## Pagination

Endpoints that return lists support pagination:

```http
GET /concepts?page=1&limit=10
```

Response includes pagination metadata:
```json
{
  "data": [...],
  "pagination": {
    "page": 1,
    "limit": 10,
    "total": 100,
    "pages": 10
  }
}
```

## Testing with cURL

### Login

```bash
curl -X POST http://localhost:5000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "password123"
  }'
```

### Get Concepts

```bash
curl -X GET http://localhost:5000/api/v1/concepts \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Send Chat Message

```bash
curl -X POST http://localhost:5000/api/v1/tutor/chat \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Explain React hooks",
    "conceptId": "concept-1"
  }'
```

## Versioning

The API uses URL versioning: `/api/v1/`

Breaking changes will result in a new version (e.g., `/api/v2/`). Previous versions will remain supported for a deprecation period.

## Documentation

For additional information, refer to:
- [Architecture](./ARCHITECTURE.md) - System design
- [Development Setup](./DEVELOPMENT_SETUP.md) - Getting started
- [Contributing](../CONTRIBUTING.md) - Development guidelines

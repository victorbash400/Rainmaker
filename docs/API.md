# Rainmaker API Documentation

## Overview

The Rainmaker API is built with FastAPI and provides endpoints for managing prospects, campaigns, conversations, proposals, and meetings. All endpoints require authentication via JWT tokens.

## Base URL

```
http://localhost:8000
```

## Authentication

All API endpoints (except `/auth/login` and `/auth/register`) require a Bearer token in the Authorization header:

```
Authorization: Bearer <your-jwt-token>
```

## Endpoints

### Authentication

#### POST /api/v1/auth/login
Login with email and password to receive an access token.

**Request Body:**
```json
{
  "email": "user@example.com",
  "password": "password"
}
```

**Response:**
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "token_type": "bearer",
  "expires_in": 86400
}
```

#### POST /api/v1/auth/register
Register a new user account.

**Request Body:**
```json
{
  "email": "user@example.com",
  "name": "John Doe",
  "password": "password",
  "role": "sales_rep"
}
```

### Prospects

#### GET /api/v1/prospects
Get paginated list of prospects with optional filtering.

**Query Parameters:**
- `page` (int): Page number (default: 1)
- `per_page` (int): Items per page (default: 20, max: 100)
- `status` (string): Filter by prospect status
- `prospect_type` (string): Filter by prospect type
- `search` (string): Search in name, email, or company name

**Response:**
```json
{
  "items": [...],
  "total": 100,
  "page": 1,
  "per_page": 20,
  "pages": 5
}
```

#### GET /api/v1/prospects/{prospect_id}
Get a specific prospect by ID.

#### POST /api/v1/prospects
Create a new prospect.

#### PUT /api/v1/prospects/{prospect_id}
Update a prospect.

#### DELETE /api/v1/prospects/{prospect_id}
Delete a prospect.

### Campaigns

#### GET /api/v1/campaigns
Get paginated list of campaigns.

#### GET /api/v1/campaigns/{campaign_id}
Get a specific campaign by ID.

#### POST /api/v1/campaigns
Create a new campaign.

#### POST /api/v1/campaigns/{campaign_id}/approve
Approve a campaign for sending.

### Conversations

#### GET /api/v1/conversations
Get paginated list of conversations.

#### GET /api/v1/conversations/{conversation_id}
Get a specific conversation by ID.

#### POST /api/v1/conversations
Create a new conversation.

#### GET /api/v1/conversations/{conversation_id}/messages
Get all messages in a conversation.

#### POST /api/v1/conversations/{conversation_id}/messages
Add a message to a conversation.

### Proposals

#### GET /api/v1/proposals
Get paginated list of proposals.

#### GET /api/v1/proposals/{proposal_id}
Get a specific proposal by ID.

#### POST /api/v1/proposals
Create a new proposal.

#### POST /api/v1/proposals/{proposal_id}/approve
Approve a proposal for sending.

### Meetings

#### GET /api/v1/meetings
Get paginated list of meetings.

#### GET /api/v1/meetings/{meeting_id}
Get a specific meeting by ID.

#### POST /api/v1/meetings
Create a new meeting.

#### PUT /api/v1/meetings/{meeting_id}/status
Update meeting status.

## Error Responses

All endpoints return consistent error responses:

```json
{
  "error_code": "ERROR_CODE",
  "message": "Human readable error message",
  "success": false
}
```

Common error codes:
- `HTTP_400`: Bad Request
- `HTTP_401`: Unauthorized
- `HTTP_403`: Forbidden
- `HTTP_404`: Not Found
- `HTTP_422`: Validation Error
- `HTTP_500`: Internal Server Error

## Interactive Documentation

Visit `http://localhost:8000/docs` for interactive API documentation with Swagger UI.
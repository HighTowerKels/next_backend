# NexaBill Wallet API Documentation

## Table of Contents
- [API Overview](#api-overview)
- [Authentication](#authentication)
- [API Endpoints](#api-endpoints)
  - [Authentication](#authentication-endpoints)
  - [Wallet](#wallet-endpoints)
- [Request/Response Examples](#requestresponse-examples)
- [Error Handling](#error-handling)
- [Development Setup](#development-setup)
- [Testing](#testing)
- [Additional Notes](#additional-notes)

## API Overview
**Base URL**: `https://api.nexabill.com/v1/`

All API responses are in JSON format. The API follows REST conventions and uses standard HTTP methods and status codes.

## Authentication
The API uses JWT (JSON Web Tokens) for authentication. Include the token in the Authorization header:

```http
Authorization: Bearer <access_token>
API Endpoints

Authentication Endpoints

Register User

POST /auth/register/

Description: Creates new user account with associated wallet

Permissions: AllowAny

Request:

json
{
  "email": "user@example.com",
  "username": "user123",
  "phone_number": "2348123456789",
  "password": "securePassword123"
}
Response (201 Created):

json
{
  "user": {
    "email": "user@example.com",
    "username": "user123",
    "phone_number": "2348123456789"
  },
  "wallet": {
    "wallet_id": "NEXA12345678",
    "balance": "0.00",
    "virtual_account_number": "1234567890",
    "virtual_bank_name": "NexaBank"
  }
}
Login

POST /auth/login/

Description: Authenticates user and returns JWT tokens

Request:

json
{
  "email": "user@example.com",
  "password": "securePassword123"
}
Response (200 OK):

json
{
  "access": "eyJhbGciOi...",
  "refresh": "eyJhbGciOi...",
  "user": {
    "email": "user@example.com",
    "username": "user123",
    "phone_number": "2348123456789"
  }
}
Wallet Endpoints

Get Wallet Details

GET /wallet/

Permissions: IsAuthenticated

Response (200 OK):

json
{
  "wallet_id": "NEXA12345678",
  "balance": "5000.00",
  "virtual_account_number": "1234567890",
  "virtual_bank_name": "NexaBank",
  "created_at": "2023-06-15T12:00:00Z"
}
Withdraw Funds

POST /wallet/withdraw/

Request:

json
{
  "amount": "1000.00",
  "bank_code": "058",
  "account_number": "1234567890",
  "account_name": "John Doe"
}
Response (200 OK):

json
{
  "id": 1,
  "reference": "WDR-123456",
  "amount": "1000.00",
  "transaction_type": "Withdrawal",
  "status": "Success",
  "created_at": "2023-06-15T12:05:00Z"
}
Error Handling

Error Response Format:

json
{
  "status": "error",
  "message": "Detailed error message",
  "code": "ERROR_CODE"
}
Common Error Codes:

Code	Description
400	Bad Request
401	Unauthorized
403	Forbidden
404	Not Found
500	Server Error
Development Setup

Clone repository:
bash
git clone https://github.com/nexabill/backend.git
cd backend
Install dependencies:
bash
pip install -r requirements.txt
Configure environment:
bash
cp .env.example .env
# Edit .env with your configuration
Run migrations:
bash
python manage.py migrate
Start server:
bash
python manage.py runserver
Testing

Run the test suite with:

bash
python manage.py test
Additional Notes

All monetary values use 2 decimal places
Dates follow ISO 8601 format (YYYY-MM-DDTHH:MM:SSZ)
API versioning through URL path (/v1/)
Rate limiting applied to authentication endpoints

This document includes:

1. Clear section organization with table of contents
2. Consistent formatting for endpoints
3. Request/response examples with proper JSON formatting
4. Error handling documentation
5. Development setup instructions
6. Testing information
7. Important notes about API conventions

You can save this as a `.md` file and render it in GitHub/GitLab or convert it to PDF/HTML for distribution. The markdown format makes it easy to maintain and update as the API evolves.
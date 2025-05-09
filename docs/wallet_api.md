# NexaBill Wallet API Documentation

## Table of Contents
- [Overview](#overview)
- [Authentication](#authentication)
- [Endpoints](#endpoints)
  - [Authentication](#authentication-endpoints)
  - [Wallet Operations](#wallet-operations)
  - [Value Added Services](#value-added-services)
- [Error Handling](#error-handling)
- [Rate Limiting](#rate-limiting)

## Overview

Base URL: `https://api.nexabill.com/v1`

The NexaBill Wallet API provides endpoints for managing digital wallets, performing transactions, and accessing value-added services.

## Authentication

The API uses JWT (JSON Web Tokens) for authentication. Include the token in the Authorization header:

```http
Authorization: Bearer <access_token>
```

## Endpoints

### Authentication Endpoints

#### Register User
```http
POST /auth/register/
```

**Request:**
```json
{
  "email": "user@example.com",
  "username": "user123",
  "phone_number": "2348123456789",
  "password": "securePassword123"
}
```

**Response (201 Created):**
```json
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
```

#### Login
```http
POST /auth/login/
```

**Request:**
```json
{
  "email": "user@example.com",
  "password": "securePassword123"
}
```

**Response (200 OK):**
```json
{
  "access": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc..."
}
```

### Wallet Operations

#### Get Wallet Details
```http
GET /wallet/
```

**Response (200 OK):**
```json
{
  "wallet_id": "NEXA12345678",
  "balance": "5000.00",
  "virtual_account_number": "1234567890",
  "virtual_bank_name": "NexaBank"
}
```

#### Process Withdrawal
```http
POST /wallet/withdraw/
```

**Request:**
```json
{
  "amount": "1000.00",
  "bank_code": "058",
  "account_number": "0123456789",
  "account_name": "John Doe"
}
```

#### Transfer Funds
```http
POST /wallet/transfer/
```

**Request:**
```json
{
  "amount": "500.00",
  "recipient_wallet_id": "NEXA87654321",
  "narration": "Payment for services"
}
```

### Value Added Services

#### Purchase Airtime
```http
POST /airtime/buy/
```

**Request:**
```json
{
  "phone_number": "2348123456789",
  "amount": "100.00",
  "network": "MTN"
}
```

#### Purchase Data Bundle
```http
POST /data/buy/
```

**Request:**
```json
{
  "phone_number": "2348123456789",
  "plan_code": "1GB-1000",
  "network": "Airtel"
}
```

## Error Handling

All errors follow this format:

```json
{
  "error": "Error message here",
  "code": "ERROR_CODE",
  "details": {}
}
```

Common Status Codes:
- `200`: Success
- `201`: Created
- `400`: Bad Request
- `401`: Unauthorized
- `403`: Forbidden
- `404`: Not Found
- `500`: Internal Server Error

## Rate Limiting

- Authentication endpoints: 3 requests per minute
- VAS endpoints: 10 requests per minute
- Wallet operations: 30 requests per minute

## Development

### Environment Setup

Required environment variables:
```bash
PAYSCRIBE_API_KEY=xxx
PAYSCRIBE_WEBHOOK_SECRET=xxx
PAYSCRIBE_BASE_URL=https://api.payscribe.com/v1
```

### Running Tests

```bash
python manage.py test wallet
```

### Webhook Integration

Configure your webhook URL in the Payscribe dashboard:
```
https://api.nexabill.com/v1/wallet/deposit/webhook/
```
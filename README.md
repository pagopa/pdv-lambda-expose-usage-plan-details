
# pdv-lambda-expose-usage-plan-details

AWS Lambda function to expose API Gateway API keys and validate API key values.

## Table of Contents

- [Overview](#overview)
- [Endpoints](#endpoints)

## Overview

This Lambda exposes two endpoints via API Gateway:

- **GET /api-keys**: Lists all API Gateway API keys (id and name).
- **POST /validate-api-key**: Validates an API key by comparing the provided value with the one stored in API Gateway.

## Endpoints

### GET `/api-keys`

Returns a list of API keys.

**Response Example:**
```json
{
  "api_keys": [
    { "id": "123abc", "name": "Key 1" },
    { "id": "456def", "name": "Key 2" }
  ]
}
```

### POST `/validate-api-key`

Validates an API key value.

**Request Body:**
```json
{
  "api_key_id": "123abc",
  "api_key_value": "the-key-value"
}
```

**Response Example:**
```json
{ "valid": true }
```
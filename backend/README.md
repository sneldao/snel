# Snel Backend

Backend service for the Snel cross-chain bridging and token management platform.

## Features

- Token bridging via Brian API
- Balance checking
- Transaction status tracking
- Redis for state management

## Setup

1. Copy `.env.example` to `.env` and configure your environment variables:

   ```bash
   cp .env.example .env
   ```

2. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Run the development server:
   ```bash
   uvicorn app.main:app --reload
   ```

## Docker Setup

Run with Docker Compose:

```bash
docker-compose up --build
```

## API Documentation

Once running, visit:

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Project Structure

```
backend/
├── app/
│   ├── api/
│   │   └── v1/
│   │       └── bridges.py
│   ├── core/
│   ├── models/
│   │   └── commands.py
│   └── services/
│       └── brian/
│           └── client.py
├── docker/
├── tests/
├── .env.example
├── docker-compose.yml
├── Dockerfile
└── requirements.txt
```

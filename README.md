# Pointless - AI Crypto Assistant

A friendly crypto command interpreter that helps users swap tokens and answers questions about crypto.

## Features

- Token swaps across multiple chains (Optimism, Base, Scroll)
- Natural language command processing
- Automatic token approval handling
- Multi-chain support with automatic chain detection
- Persistent command storage with Redis

## Supported Chains

- Optimism
- Base
- Scroll
- (More coming soon)

## Local Development Setup

### Prerequisites

- Python 3.12+
- Node.js 18+
- Poetry for Python dependency management
- pnpm for Node.js dependency management
- Redis (via Upstash)

### Environment Variables

Create a `.env.local` file in the root directory:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
ALCHEMY_KEY=your_alchemy_key
COINGECKO_API_KEY=your_coingecko_key
REDIS_URL=your_upstash_redis_url  # Format: rediss://default:token@hostname:port
```

### Redis Setup

The project uses Upstash Redis for persistent storage. To set up:

1. Create a database at [Upstash Console](https://console.upstash.com/)
2. Get your Redis URL from the Upstash dashboard
3. Add the URL to your `.env` file
4. Test the connection:

```bash
poetry run python test_redis_upstash.py
```

### Backend Setup

1. Install Python dependencies:

```bash
poetry install
```

2. Start the FastAPI server:

```bash
poetry run uvicorn api:app --reload --port 8000
```

### Frontend Setup

1. Install Node.js dependencies:

```bash
cd frontend
pnpm install
```

2. Start the Next.js development server:

```bash
pnpm dev
```

## Production Setup (Vercel)

### Vercel Configuration

The project uses Vercel's serverless functions for the backend. Configuration is managed through `vercel.json`:

```json
{
  "version": 2,
  "builds": [
    {
      "src": "api.py",
      "use": "@vercel/python",
      "config": {
        "maxDuration": 60,
        "memory": 1024,
        "runtime": "python3.12",
        "handler": "app",
        "includeFiles": ["kyber.py", "configure_logging.py"]
      }
    },
    {
      "src": "frontend/package.json",
      "use": "@vercel/next"
    }
  ],
  "routes": [
    {
      "src": "/api/(.*)",
      "dest": "/api.py"
    },
    {
      "src": "/(.*)",
      "dest": "/frontend/$1"
    }
  ],
  "regions": ["iad1"],
  "env": {
    "PYTHONUNBUFFERED": "1",
    "PYTHONPATH": ".",
    "PYTHONIOENCODING": "utf-8",
    "QUICKNODE_ENDPOINT": "https://api.kyberswap.com"
  }
}
```

### Environment Variables (Vercel)

Set these in your Vercel project settings:

- `ALCHEMY_KEY`
- `COINGECKO_API_KEY`
- `NEXT_PUBLIC_API_URL` (set to your production domain)
- `REDIS_URL` (your Upstash Redis URL)

### Dependencies

The project uses specific versions of dependencies that are known to work with Vercel's serverless environment:

```requirements.txt
fastapi==0.115.8
uvicorn==0.34.0
pydantic==2.10.6
httpx==0.28.1
python-dotenv==1.0.1
slowapi==0.1.9
eth-rpc-py==0.1.26
eth-account==0.13.5
eth-typing==5.2.0
dowse==0.1.0
emp-agents>=0.2.0.post1,<0.3.0
upstash-redis==1.2.0
```

## Key Differences Between Local and Production

### Backend

- Local: Runs as a standalone FastAPI server
- Production: Runs as Vercel serverless functions

### API URLs

- Local: `http://localhost:8000`
- Production: Your Vercel deployment URL

### CORS Configuration

The backend supports these origins:

```python
allow_origins=[
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "https://snel-pointless.vercel.app",
    "https://snel-pointless-git-main-papas-projects-5b188431.vercel.app",
]
```

## Underpinned by Dowse

Dowse is a Python library that enables you to build intelligent agents capable of:

- Parsing natural language commands and questions
- Classifying inputs into different types (e.g. commands vs questions)
- Executing structured commands based on natural language requests
- Responding to user queries with relevant information
- Building complex pipelines for command processing

## Key Features

- **Natural Language Processing**: Convert human language into structured commands
- **Flexible Pipeline Architecture**: Build custom processing flows with branching logic
- **Built-in Command Handlers**: Ready-to-use handlers for common operations
- **Extensible Design**: Easy to add new command types and handlers
- **Async Support**: Built for high-performance async/await operations

## Project Structure

```
dowse-pointless/
├── api.py              # FastAPI backend server
├── frontend/          # Next.js frontend application
├── .env              # Environment variables
└── README.md         # This file

## Troubleshooting

### Common Issues

1. API Connection Errors
   - Check CORS settings
   - Verify environment variables
   - Ensure correct API URL configuration

2. Swap Failures
   - Verify token approvals
   - Check token addresses for the chain
   - Ensure sufficient balance

### Logs

- Local: Available in terminal running the FastAPI server
- Production: Check Vercel deployment logs

## Contributing

1. Fork the repository
2. Create a feature branch
3. Submit a pull request

## License

MIT

## Notes on Dowse Implementation Challenges

During our attempt to integrate Dowse for natural language command processing, we encountered several challenges that led us to implement our own command parsing solution:

1. Type System Complexity
   - Dowse's type system is highly opinionated and tightly coupled with Pydantic
   - The generic type parameters for Pipeline, Classifier, and Executor were difficult to align with our use case
   - Validation errors were hard to resolve due to complex inheritance patterns

2. Architecture Constraints
   - Dowse's Pipeline architecture assumes a specific flow that didn't match our swap/price query needs
   - The built-in classifiers and executors were too rigid for our token swap use case
   - Custom implementations required extensive boilerplate to satisfy Dowse's type system

3. Integration Issues
   - Difficulty integrating with our existing token address and chain management
   - Challenges with error handling and transaction flow control
   - Limited flexibility in command parsing and response formatting

4. Alternative Solution
   - Implemented a simpler, more focused command parsing system
   - Direct control over swap command validation and execution
   - Better integration with our existing token price and swap infrastructure
   - More maintainable and easier to extend for our specific use case

These notes are provided to help future development decisions and to document why we chose a custom implementation over the Dowse framework.
```

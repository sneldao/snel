# Pointless - AI Crypto Assistant

A friendly crypto command interpreter that helps users swap tokens and answers questions about crypto.

## Features

- Token swaps across multiple chains (Optimism, Base, Scroll)
- Natural language command processing
- Automatic token approval handling with skip approval option
- Multi-chain support with automatic chain detection
- Persistent command storage with Redis

## Supported Chains

- Optimism
- Base
- Scroll
- Ethereum
- Arbitrum
- Polygon
- Avalanche
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
MORALIS_API_KEY=your_moralis_key
REDIS_URL=your_upstash_redis_url  # Format: rediss://default:token@hostname:port
ZEROX_API_KEY=your_0x_api_key
```

For local development, if you encounter SSL certificate verification issues with the API services, you can set:

```env
DISABLE_SSL_VERIFY=true
```

**Note:** This should only be used in development environments, never in production.

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
poetry run python main.py
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

The project uses Vercel's serverless functions for the backend. Configuration is managed through several files:

1. `vercel.json` - Main configuration file for Vercel deployment
2. `vercel.build.sh` - Custom build script that installs dependencies
3. `runtime.txt` - Specifies the Python version (3.12)
4. `vercel.ignore` - Specifies files to ignore during deployment

The main configuration in `vercel.json`:

```json
{
  "version": 2,
  "buildCommand": "chmod +x vercel.build.sh && ./vercel.build.sh",
  "builds": [
    {
      "src": "api/index.py",
      "use": "@vercel/python",
      "config": {
        "maxDuration": 90,
        "memory": 1024,
        "runtime": "python3.12",
        "handler": "app",
        "includeFiles": [
          "app/**",
          "src/**",
          "requirements.txt",
          "*.py",
          ".env*"
        ],
        "excludeFiles": [
          "**/*.test.py",
          "**/*_test.py",
          "test_*.py",
          "tests/**",
          ".pytest_cache/**",
          "__pycache__/**",
          ".coverage",
          ".env.test",
          "test_redis_simple.py",
          "test_redis_ssl.py",
          "test_redis_upstash.py"
        ]
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
      "dest": "/api/index.py"
    },
    {
      "handle": "filesystem"
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
- `MORALIS_API_KEY`
- `ZEROX_API_KEY` (for 0x API access)
- `NEXT_PUBLIC_API_URL` (set to your production domain)
- `REDIS_URL` (your Upstash Redis URL)

### Dependencies

The project uses specific versions of dependencies that are known to work with Vercel's serverless environment. These are defined in `requirements.txt`.

## Key Differences Between Local and Production

### Backend

- Local: Runs as a standalone FastAPI server via `main.py`
- Production: Runs as Vercel serverless functions via `api/index.py`

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

## Transaction Features

### Token Approval Management

The application now supports automatic token approval management with these features:

- **Automatic Approval Detection**: The system automatically detects when token approvals are needed
- **Skip Approval Option**: Commands prefixed with "approved:" will skip the approval check
- **Approval Transaction Tracking**: Track the status of approval transactions with clear feedback
- **Smart Retry Logic**: After successful approval, the system automatically continues with the original transaction

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

3. SSL Certificate Verification Issues (Local Development)
   - Set `DISABLE_SSL_VERIFY=true` in your `.env` file
   - This is only for local development and should not be used in production

### Logs

- Local: Available in terminal running the FastAPI server
- Production: Check Vercel deployment logs

## Recent Updates

- Added skip approval functionality to streamline token swaps after approval
- Added SSL certificate verification bypass option for local development
- Added support for 0x API as the default swap aggregator
- Enhanced token lookup functionality to better handle contract addresses
- Improved error messages for token lookup failures
- Added support for direct contract address input in swap commands

## Contributing

1. Fork the repository
2. Create a feature branch
3. Submit a pull request

## License

MIT

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
├── api/              # API entry point for Vercel
├── app/              # Main application code
├── frontend/         # Next.js frontend application
├── backup/           # Backup of previous configurations (for reference only)
├── vercel.json       # Vercel deployment configuration
├── vercel.build.sh   # Build script for Vercel
├── runtime.txt       # Python runtime specification
├── vercel.ignore     # Files to ignore during deployment
├── requirements.txt  # Python dependencies
├── main.py           # Local development entry point
├── .env              # Environment variables
└── README.md         # This file
```

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

## Configuration

### Environment Variables

The application requires several environment variables to be set:

- `REDIS_URL`: URL for the Redis instance
- `REDIS_PASSWORD`: Password for Redis (if using Upstash)
- `OPENAI_API_KEY`: API key for OpenAI services
- `ZEROX_API_KEY`: API key for 0x Protocol swap functionality (get one at https://dashboard.0x.org)

## Setting Up Swap Functionality

To enable swap functionality through the 0x protocol, you need to:

1. Visit the [0x Dashboard](https://dashboard.0x.org) and create an account
2. Generate an API key for your application
3. Add the key to your environment variables as `ZEROX_API_KEY`
4. Restart the application to ensure the key is loaded

Without a valid 0x API key, swap functionality may be rate-limited or fail.

```

```

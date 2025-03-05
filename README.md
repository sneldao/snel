# Snel - AI Crypto Assistant

A friendly crypto command interpreter that helps users swap tokens, set up DCA (Dollar Cost Average) orders, and answers questions about crypto.

## Features

- **Token Swaps**: Execute token swaps across multiple chains
- **DCA (Dollar Cost Average)**: Set up recurring purchases of crypto assets
- **Price Queries**: Get real-time price information for tokens
- **Natural Language Processing**: Understand and process commands in natural language
- **Multi-Chain Support**: Works across Ethereum, Optimism, Base, Scroll, Arbitrum, Polygon, and Avalanche
- **Automatic Token Approval**: Handles token approvals with skip approval option
- **Quote Selection**: Compare quotes from different aggregators
- **Persistent State**: Stores command history and pending operations with Redis

## Supported Chains

- Ethereum
- Optimism
- Base
- Scroll
- Arbitrum
- Polygon
- Avalanche
- (More coming soon)

## Architecture

Snel uses a pipeline architecture to process commands:

1. **Command Input**: User enters a natural language command
2. **Pipeline Processing**: The command is routed to the appropriate agent
3. **Agent Processing**: Specialized agents handle different types of commands
4. **State Management**: Redis stores command history and pending operations
5. **Response Generation**: The response is formatted and returned to the user

### Agent Types

- **Swap Agent**: Handles token swap commands
- **Price Agent**: Processes price queries
- **DCA Agent**: Manages dollar cost averaging setups
- **Default Agent**: Handles general queries

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
OPENAI_API_KEY=your_openai_api_key
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
- `OPENAI_API_KEY` (for AI agent functionality)
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

## Command Types

### Swap Commands

Swap commands allow users to exchange one token for another. Examples:

- `swap 1 ETH for USDC`
- `convert 100 USDC to ETH`
- `approved: swap 0.5 ETH for USDC` (skips approval check)

### DCA Commands

DCA (Dollar Cost Average) commands set up recurring purchases. Examples:

- `dca 0.1 ETH daily into USDC`
- `dollar cost average 50 USDC weekly into ETH`
- `set up dca 100 USDC monthly into ETH for 90 days`

### Price Queries

Price queries get current token prices. Examples:

- `price ETH`
- `how much is 1 BTC worth?`
- `what is the price of ETH in USDC?`

## Transaction Features

### Token Approval Management

The application supports automatic token approval management with these features:

- **Automatic Approval Detection**: The system automatically detects when token approvals are needed
- **Skip Approval Option**: Commands prefixed with "approved:" will skip the approval check
- **Approval Transaction Tracking**: Track the status of approval transactions with clear feedback
- **Smart Retry Logic**: After successful approval, the system automatically continues with the original transaction

### DCA Management

The DCA functionality includes:

- **Frequency Options**: Daily, weekly, or monthly purchases
- **Duration Setting**: Specify how long the DCA should run
- **Token Selection**: Use any supported token pair
- **Approval Handling**: Automatic approval of token spending

## State Management with Redis

The application uses Redis for state management:

- **Command History**: Stores user command history
- **Pending Commands**: Tracks commands awaiting confirmation
- **Swap Confirmation State**: Stores details about pending swaps
- **DCA Configuration**: Stores DCA setup information

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

- Added DCA (Dollar Cost Average) functionality
- Implemented pipeline architecture for command routing
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

## Project Structure

```
snel/
├── api/              # API entry point for Vercel
├── app/              # Main application code
│   ├── agents/       # Agent implementations
│   │   ├── base.py   # Base agent class
│   │   ├── dca_agent.py # DCA agent
│   │   ├── price_agent.py # Price agent
│   │   ├── simple_swap_agent.py # Swap agent
│   │   └── agent_factory.py # Factory for creating agents
│   ├── api/          # API routes
│   │   └── routes/   # Route definitions
│   ├── models/       # Data models
│   │   └── commands.py # Command models
│   └── services/     # Services
│       ├── pipeline.py # Command pipeline
│       ├── redis_service.py # Redis service
│       └── token_service.py # Token service
├── frontend/         # Next.js frontend application
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

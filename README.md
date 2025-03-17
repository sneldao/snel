# SNEL - Your Lazy AI Agent Assistant and Her Crew

Meet SNEL, a comically slow but surprisingly knowledgeable crypto snail who helps users swap tokens, bridge assets across chains, check balances, and answer questions about crypto

## Features

- **Token swaps** across multiple chains (Optimism, Base, Scroll)
- **Cross-chain bridging** with Brian API integration
- **Balance checking** for any token on supported chains
- **Natural language command processing** with snail-like wit
- **Automatic token approval** handling with skip approval option
- **Multi-chain support** with automatic chain detection
- **Persistent command storage** with Redis
- **Messaging platform integration** (WhatsApp, Telegram)
- **Telegram bot with real wallet capabilities** for seamless DeFi interactions on Scroll Sepolia

## Supported Chains

- Optimism
- Base
- Scroll
- Ethereum
- Arbitrum
- Polygon
- Avalanche
- (More coming soon... at a snail's pace, of course)

## Brian API Integration

The project implements the Brian API as an alternative solution for handling swaps, transfers, and bridging on the Scroll network. The Brian API is an Intent Recognition and Execution Engine for Web3 interactions that can understand user intent, provide answers, build transactions, or generate smart contracts.

### Brian API Features

- Automatic detection of Scroll network and use of Brian API for swaps
- Fallback to traditional aggregators if Brian API is unavailable
- Seamless integration with the existing swap UI
- Support for all token pairs available on Scroll
- Cross-chain bridging capabilities
- Token transfer functionality
- Balance checking for any token

### Implementation Details

#### Brian API Service

The `BrianAPIService` class in `app/services/brian_service.py` provides methods to interact with the Brian API:

- `get_swap_transaction`: Gets a swap transaction from the Brian API
- `get_transfer_transaction`: Gets a token transfer transaction
- `get_bridge_transaction`: Gets a cross-chain bridge transaction
- `get_token_balances`: Gets token balances for a wallet
- `extract_parameters`: Extracts parameters from a prompt
- `get_token_info`: Gets token information from the Brian API

#### Brian Agent

The `BrianAgent` class in `app/agents/brian_agent.py` handles natural language processing for Brian API commands:

- `process_transfer_command`: Processes token transfer commands
- `process_bridge_command`: Processes cross-chain bridge commands
- `process_balance_command`: Processes balance check commands

#### Scroll Handler

The `ScrollHandler` class in `app/services/scroll_handler.py` has been updated to use the Brian API for Scroll swaps:

- `use_brian_api`: Uses the Brian API to get a swap transaction for Scroll
- `get_recommended_aggregator`: Now recommends Brian API as the default aggregator for Scroll

## Messaging Platform Integration

The project includes integration with messaging platforms like WhatsApp and Telegram through the `MessagingAgent` class in `app/agents/messaging_agent.py`.

### Messaging Agent Features

- Process commands from WhatsApp and Telegram
- Wallet connection via unique links
- Balance checking for connected wallets
- Token swaps directly from chat
- Price checking for tokens
- Natural language command processing

### Telegram Integration

The project now includes a dedicated Telegram bot built with Node.js that provides a more native Telegram experience with interactive buttons and improved user experience.

#### Telegram Bot Features

- **Real Wallet Creation & Management**: Create and manage real Ethereum wallets directly in Telegram
- **Token Price Checking**: Get real-time token prices with natural language queries
- **Token Swaps**: Initiate and approve token swaps with a simple command
- **Balance Checking**: View your wallet balances for multiple tokens
- **Natural Language Understanding**: Interact with the bot using everyday language
- **Interactive UI**: Buttons and keyboards for easier navigation

#### Telegram Bot Architecture

The Telegram bot uses a hybrid architecture:

- **Node.js Bot**: Handles Telegram-specific UI and wallet interactions
- **Python Backend**: Processes complex queries and DeFi operations
- **Redis Storage**: Securely stores wallet data and user preferences

This approach allows for:

- Better user experience with Telegram-native features
- Leveraging the existing AI capabilities in the Python backend
- Simplified wallet management through the bot interface
- Secure storage of wallet data in Redis

#### Wallet Implementation

The Telegram bot implements real wallet functionality on Scroll Sepolia testnet:

- **Real Ethereum Wallet Creation**: Uses ethers.js to create actual Ethereum wallets
- **Private Key Management**: Securely stores private keys in Redis
- **Balance Checking**: Retrieves real balances from the Scroll Sepolia blockchain
- **Transaction Capabilities**: Supports sending transactions and token swaps
- **Testnet Focus**: Limited to Scroll Sepolia for safety during testing

#### Telegram Bot Setup

To set up the Telegram bot:

1. Navigate to the `telegram-bot` directory
2. Install dependencies:
   ```
   npm install
   ```
3. Create a `.env` file with:
   ```
   TELEGRAM_BOT_TOKEN=your_telegram_bot_token
   API_URL=http://localhost:8000
   ```
4. Start the bot:
   ```
   npm run dev
   ```

#### Telegram Bot Deployment on Vercel

To deploy the Telegram bot to Vercel:

1. Create a new Vercel project for the Telegram bot
2. Add the following environment variables in Vercel:
   - `TELEGRAM_BOT_TOKEN`: Your Telegram bot token
   - `API_URL`: URL to your deployed backend API
   - `NODE_ENV`: Set to "production"
3. Configure the Vercel project to use the `telegram-bot` directory as the root
4. Use the `telegram-bot/vercel.json` file for configuration
5. Deploy the project to Vercel

#### Terms and Conditions

By using the Telegram bot, users agree to the [Terms and Conditions](https://snel-pointless.vercel.app/terms) which outline:

- The non-custodial nature of the service
- User responsibilities for transaction approval
- Financial risks associated with cryptocurrency transactions
- Limitations of liability
- Third-party service interactions

## Local Development Setup

### Prerequisites

- Python 3.12+
- Node.js 18+
- Poetry for Python dependency management
- pnpm for Node.js dependency management
- Redis (via Upstash)

### Environment Variables

Create a `.env.local` file in the root directory:

```
NEXT_PUBLIC_API_URL=http://localhost:8000
ALCHEMY_KEY=your_alchemy_key
COINGECKO_API_KEY=your_coingecko_key
MORALIS_API_KEY=your_moralis_key
REDIS_URL=your_upstash_redis_url  # Format: rediss://default:token@hostname:port
ZEROX_API_KEY=your_0x_api_key
BRIAN_API_KEY=your_brian_api_key
BRIAN_API_URL=https://api.brianknows.org/api/v0
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
```

For local development, if you encounter SSL certificate verification issues with the API services, you can set:

```
DISABLE_SSL_VERIFY=true
```

Note: This should only be used in development environments, never in production.

### Redis Setup

The project uses Upstash Redis for persistent storage. To set up:

1. Create a database at [Upstash Console](https://console.upstash.com/)
2. Get your Redis URL from the Upstash dashboard
3. Add the URL to your `.env` file
4. Test the connection:
   ```
   poetry run python test_redis_upstash.py
   ```

### Backend Setup

Install Python dependencies:

```
poetry install
```

Start the FastAPI server:

```
poetry run python main.py
```

### Frontend Setup

Install Node.js dependencies:

```
cd frontend
pnpm install
```

Start the Next.js development server:

```
pnpm dev
```

### Telegram Bot Setup

Install Node.js dependencies:

```
cd telegram-bot
npm install
```

Start the Telegram bot:

```
npm run dev
```

## Production Setup (Vercel)

### Vercel Configuration

The project uses Vercel's serverless functions for the backend. Configuration is managed through several files:

- `vercel.json` - Main configuration file for Vercel deployment
- `vercel.build.sh` - Custom build script that installs dependencies
- `runtime.txt` - Specifies the Python version (3.12)
- `vercel.ignore` - Specifies files to ignore during deployment (including the telegram-bot directory)

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
          "api/**",
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
- `BRIAN_API_KEY` (for Brian API access)
- `TELEGRAM_BOT_TOKEN` (for Telegram integration)
- `NEXT_PUBLIC_API_URL` (set to your production domain)
- `REDIS_URL` (your Upstash Redis URL)

### Telegram Bot Deployment

For deploying the Telegram bot to Vercel:

1. Create a separate Vercel project for the Telegram bot
2. Set the root directory to `telegram-bot`
3. Add the required environment variables:
   - `TELEGRAM_BOT_TOKEN`
   - `API_URL` (pointing to your main backend)
   - `NODE_ENV=production`
4. Use the `telegram-bot/vercel.json` file for configuration
5. Deploy the project

### Dependencies

The project uses specific versions of dependencies that are known to work with Vercel's serverless environment. These are defined in `requirements.txt`.

## Key Differences Between Local and Production

### Backend

- Local: Runs as a standalone FastAPI server via `main.py`
- Production: Runs as Vercel serverless functions via `api/index.py`

### API URLs

- Local: http://localhost:8000
- Production: Your Vercel deployment URL

### Telegram Bot

- Local: Runs with `npm run dev` using long polling
- Production: Deployed as a separate Vercel project using webhooks

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

The application supports automatic token approval management with these features:

- **Automatic Approval Detection**: The system automatically detects when token approvals are needed
- **Skip Approval Option**: Commands prefixed with "approved:" will skip the approval check
- **Approval Transaction Tracking**: Track the status of approval transactions with clear feedback
- **Smart Retry Logic**: After successful approval, the system automatically continues with the original transaction

## Natural Language Commands

The application supports a variety of natural language commands:

### Swap Commands

- "swap 1 ETH for USDC"
- "swap $50 of ETH for USDC"
- "swap $100 worth of ETH for PEPE"

### Transfer Commands

- "send 10 USDC to 0x123..."
- "transfer 5 ETH to vitalik.eth"

### Bridge Commands

- "bridge 0.1 ETH from Scroll to Base"
- "bridge 50 USDC from scroll to arbitrum"

### Balance Commands

- "check my USDC balance on Scroll"
- "what's my ETH balance"
- "show my balance"

## Troubleshooting

### Common Issues

#### API Connection Errors

- Check CORS settings
- Verify environment variables
- Ensure correct API URL configuration

#### Swap Failures

- Verify token approvals
- Check token addresses for the chain
- Ensure sufficient balance

#### SSL Certificate Verification Issues (Local Development)

- Set `DISABLE_SSL_VERIFY=true` in your `.env` file
- This is only for local development and should not be used in production

#### Brian API Issues

- Ensure `BRIAN_API_KEY` is set correctly
- Check if the token is supported on Scroll
- Verify that the wallet has sufficient balance

#### Telegram Bot Issues

- Ensure `TELEGRAM_BOT_TOKEN` is set correctly
- Check that the bot is running (`npm run dev` locally)
- Verify the API URL is correctly pointing to your backend
- For production, ensure the Vercel deployment is configured correctly
- If using webhooks, ensure the webhook URL is accessible

### Logs

- Local: Available in terminal running the FastAPI server
- Production: Check Vercel deployment logs

## Recent Updates

- Added real wallet creation functionality on Scroll Sepolia testnet
- Added secure wallet storage in Redis
- Added API endpoints for wallet management
- Added Telegram bot with real wallet capabilities
- Added Brian API integration for Scroll network
- Added cross-chain bridging functionality
- Added token transfer capabilities
- Added balance checking for any token
- Added messaging platform integration (WhatsApp, Telegram)
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

### Key Features

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
│   ├── agents/       # Agent implementations (Brian, Swap, etc.)
│   ├── api/          # API routes and endpoints
│   ├── config/       # Configuration files
│   ├── models/       # Data models
│   ├── services/     # Service implementations
│   └── utils/        # Utility functions
├── frontend/         # Next.js frontend application
├── telegram-bot/     # Node.js Telegram bot implementation
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

## Infrastructure and Architecture

### Agent Factory System

The project uses a flexible agent factory system (`app/agents/agent_factory.py`) that provides a centralized way to create and manage different types of agents:

- **Dynamic Agent Creation**: Creates agent instances based on type (swap, price, DCA, messaging, brian)
- **Dependency Injection**: Automatically injects required services into agents
- **Environment Awareness**: Handles different configurations for local and production environments
- **Error Handling**: Provides consistent error handling across all agent types

### Aggregator Selection System

The project implements a robust aggregator selection system with fallback mechanisms:

#### Frontend Component (`frontend/src/components/AggregatorSelection.tsx`)

- **Smart Sorting**: Prioritizes aggregators based on chain and rate
- **Chain-Specific Logic**: Special handling for Scroll chain using Brian API
- **Visual Feedback**: Clear UI showing best rates and recommended options
- **Gas Estimation**: Displays estimated gas costs for each option

#### Backend Support (`app/services/aggregator_fixes.py`)

- **Chain-Specific Fixes**: Customized fixes for different chains
- **Quote Validation**: Ensures quotes are reasonable and valid
- **Gas Estimation**: Adjusts unreasonable gas estimates
- **Router Address Management**: Maintains correct router addresses per chain

### Testing Suite

The project includes a comprehensive testing suite in the `scripts/` and `tests/` directories:

#### Aggregator Testing (`scripts/test_aggregators.py`)

- Tests multiple DEX aggregators (0x, OpenOcean, Uniswap, Kyber)
- Validates quote formats and responses
- Checks gas estimates and slippage calculations
- Verifies chain-specific configurations

#### Token Lookup Testing (`scripts/test_token_lookup.py`)

- Tests token symbol resolution
- Validates contract address lookups
- Checks chain-specific token lists
- Verifies price feed integration

#### Infrastructure Testing

- **Logger Testing** (`api/test_logger.py`): Verifies logging system integration
- **Serverless Testing** (`tests/test_serverless.py`): Tests serverless environment compatibility
- **Redis Testing** (`tests/test_redis.py`): Validates Redis connection and operations

### Test Running

To run the test suite:

```bash
# Run all tests
poetry run pytest

# Run specific test categories
poetry run python scripts/test_aggregators.py
poetry run python scripts/test_token_lookup.py
poetry run python api/test_logger.py
poetry run python tests/test_serverless.py
poetry run python tests/test_redis.py
```

## Notes on Dowse Implementation Challenges

During our attempt to integrate Dowse for natural language command processing, we encountered several challenges that led us to implement our own command parsing solution:

### Type System Complexity

- Dowse's type system is highly opinionated and tightly coupled with Pydantic
- The generic type parameters for Pipeline, Classifier, and Executor were difficult to align with our use case
- Validation errors were hard to resolve due to complex inheritance patterns

### Architecture Constraints

- Dowse's Pipeline architecture assumes a specific flow that didn't match our swap/price query needs
- The built-in classifiers and executors were too rigid for our token swap use case
- Custom implementations required extensive boilerplate to satisfy Dowse's type system

### Integration Issues

- Difficulty integrating with our existing token address and chain management
- Challenges with error handling and transaction flow control
- Limited flexibility in command parsing and response formatting

### Alternative Solution

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
- `BRIAN_API_KEY`: API key for Brian API (get one at https://brianknows.org)
- `TELEGRAM_BOT_TOKEN`: Token for Telegram bot integration

### Setting Up Swap Functionality

To enable swap functionality through the 0x protocol, you need to:

1. Visit the [0x Dashboard](https://dashboard.0x.org) and create an account
2. Generate an API key for your application
3. Add the key to your environment variables as `ZEROX_API_KEY`
4. Restart the application to ensure the key is loaded

Without a valid 0x API key, swap functionality may be rate-limited or fail.

### Setting Up Brian API

To enable Brian API functionality:

1. Visit [Brian API](https://brianknows.org) and create an account
2. Generate an API key for your application
3. Add the key to your environment variables as `BRIAN_API_KEY`
4. Add the API URL to your environment variables as `BRIAN_API_URL`
5. Restart the application to ensure the key is loaded

Without a valid Brian API key, Scroll network functionality may be limited.

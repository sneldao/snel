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
- **External wallet connections** via web-based bridge
- **AI-powered responses** using Google's Gemini API

## Wallet Technology

SNEL allows users to connect their existing wallets through a secure web-based wallet bridge. The wallet connection process:

- **Secure**: User controls their wallet and signing operations
- **Simple**: Connect with MetaMask or other web3 wallets easily
- **Cross-platform**: Works with Telegram and other messaging platforms
- **Stateful**: Maintains connection state in Redis

## Telegram Bot

Snel is available as a Telegram bot! Chat with [@pointless_snel_bot](https://t.me/pointless_snel_bot) to:

- Check token prices
- Connect your existing wallet
- Swap tokens
- Check your wallet balance
- Get real-time crypto information
- Ask general questions about crypto and DeFi

### Bot Commands

- `/start` - Start the bot
- `/help` - Show available commands
- `/connect` - Connect or create a wallet
- `/price [token]` - Check token price (e.g., `/price ETH`)
- `/swap [amount] [token] for [token]` - Create a swap (e.g., `/swap 0.1 ETH for USDC`)
- `/balance` - Check your wallet balance
- `/disconnect` - Disconnect your wallet
- `/networks` - Show available networks
- `/network [chain]` - Switch to a specific network
- `/keys` - Learn about key management and security

You can also chat with Snel naturally, asking questions like "What's the price of ETH?" or "Tell me about Scroll L2." The bot uses Google's Gemini AI to provide informative responses while maintaining a friendly, snail-themed personality.

## Setup

### Prerequisites

- Node.js (v18+)
- Python (v3.10+)
- Redis instance (optional, for persistent storage)

### Environment Variables

Create a `.env.local` file with the following:

```
# API URL - Update for production
NEXT_PUBLIC_API_URL=http://localhost:8000

# Gemini API for AI responses
GEMINI_API_KEY=your_gemini_api_key

# Redis for persistent storage
REDIS_URL=redis://localhost:6379/0

# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
```

### Installation

```bash
# Install frontend dependencies
npm install

# Install backend dependencies
pip install -r requirements.txt

# Start the development server
npm run dev
```

## Telegram Bot Setup

### Creating Your Bot with BotFather

1. Open Telegram and search for @BotFather
2. Send the command `/newbot` to create a new bot
3. Follow the instructions to choose a name and username for your bot
4. Once created, you'll receive a token. Save this as your `TELEGRAM_BOT_TOKEN`

### Simplified Setup with the Run Script

We've created an all-in-one setup script that handles the entire Telegram integration process:

1. Make sure you have your `TELEGRAM_BOT_TOKEN` in the `.env.local` file
2. Navigate to the telegram-bot directory:
   ```
   cd telegram-bot
   ```
3. Run the integration script:
   ```
   ./run.js
   ```
4. The script will:
   - Check if your FastAPI server is running (and start it if needed)
   - Check if ngrok is running (and start it if needed)
   - Verify the Telegram integration
   - Set up the webhook automatically

This is the recommended way to set up the Telegram integration as it handles all the necessary steps in one go.

### Manual Webhook Setup (Alternative)

If you prefer to set up the webhook manually:

1. Set the webhook using:

   ```
   curl -X POST https://api.telegram.org/bot<TELEGRAM_BOT_TOKEN>/setWebhook?url=<YOUR_DOMAIN>/api/messaging/telegram/webhook
   ```

2. Verify the webhook is set:
   ```
   curl -X GET https://api.telegram.org/bot<TELEGRAM_BOT_TOKEN>/getWebhookInfo
   ```

### Testing Locally

For local development, you can send test messages:

```
curl -X POST http://localhost:8000/api/messaging/telegram/process \
  -H "Content-Type: application/json" \
  -d '{"platform":"telegram","user_id":"123456","message":"/start"}'
```

### Configuring Bot AI and Wallet Features

For full functionality:

1. Add your Gemini API key to enable AI responses
2. Ensure Redis is configured for user data persistence

## Commands

- `/start` - Start the bot and receive an introduction
- `/help` - Show available commands
- `/connect` - Create a new wallet
- `/balance` - Check your wallet balance
- `/price [symbol]` - Get the price of a cryptocurrency
- `/swap [amount] [from] for [to]` - Swap tokens
- `/faucet` - Get instructions for receiving testnet ETH
- `/disconnect` - Disconnect your wallet

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

To set up Telegram integration:

1. Create a Telegram bot using BotFather
2. Get your bot token
3. Add the token to your environment variables as `TELEGRAM_BOT_TOKEN`
4. Set up a webhook URL for your bot (pointing to your API endpoint)
5. Enable the Telegram integration in your application

Example commands in Telegram:

- `/connect` - Connect your wallet
- `/balance` - Check your wallet balance
- `/swap 0.1 ETH for USDC` - Swap tokens
- `/price ETH` - Check token price

## Local Development Setup

### Prerequisites

- Python 3.12+
- Node.js 18+
- Poetry for Python dependency management
- pnpm for Node.js dependency management
- Redis (via Upstash)
- API keys for:
  - 0x Protocol (swap aggregator)
  - Coingecko (token prices)
  - Brian API (Scroll transactions)
  - Gemini (AI responses)

### Environment Setup

1. Clone the repository:

```bash
git clone https://github.com/your-username/snel-pointless.git
cd snel-pointless
```

2. Create and activate a Python virtual environment:

```bash
poetry shell
```

3. Install Python dependencies:

```bash
poetry install
```

4. Install Node.js dependencies:

```bash
cd frontend
pnpm install
cd ..
```

5. Set up environment variables:

Create a `.env.local` file in the root directory:

```bash
NEXT_PUBLIC_API_URL=http://localhost:8000
ALCHEMY_KEY=your_alchemy_key
COINGECKO_API_KEY=your_coingecko_key
MORALIS_API_KEY=your_moralis_key
REDIS_URL=your_upstash_redis_url  # Format: rediss://default:token@hostname:port
ZEROX_API_KEY=your_0x_api_key
BRIAN_API_KEY=your_brian_api_key
BRIAN_API_URL=https://api.brianknows.org/api/v0
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
GEMINI_API_KEY=your_gemini_api_key

```

For local development, if you encounter SSL certificate verification issues with the API services, you can set:

```bash
DISABLE_SSL_VERIFY=true
```

Note: This should only be used in development environments, never in production.

6. Set up Redis:

   - Create a database at [Upstash Console](https://console.upstash.com/)
   - Get your Redis URL from the Upstash dashboard
   - Add the URL to your `.env.local` file
   - Test the connection:
     ```bash
     poetry run python test_redis_upstash.py
     ```

7. Start the backend:

```bash
poetry run python server.py
```

8. Start the frontend:

```bash
cd frontend
pnpm dev
```

## Production Setup (Vercel)

### Vercel Configuration

The project uses Vercel's serverless functions for the backend. Configuration is managed through several files:

- `vercel.json` - Main configuration file for Vercel deployment
- `vercel.build.sh` - Custom build script that installs dependencies
- `runtime.txt` - Specifies the Python version (3.12)
- `vercel.ignore` - Specifies files to ignore during deployment

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
- `BRIAN_API_KEY` (for Brian API access)
- `TELEGRAM_BOT_TOKEN` (for Telegram integration)
- `NEXT_PUBLIC_API_URL` (set to your production domain)
- `REDIS_URL` (your Upstash Redis URL)

### Dependencies

The project uses specific versions of dependencies that are known to work with Vercel's serverless environment. These are defined in `requirements.txt`.

## Key Differences Between Local and Production

### Backend

- Local: Runs as a standalone FastAPI server via `server.py`
- Production: Runs as Vercel serverless functions via `api/index.py`

### API URLs

- Local: http://localhost:8000
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

### Logs

- Local: Available in terminal running the FastAPI server
- Production: Check Vercel deployment logs

## Recent Updates

- Added Gemini API integration for intelligent conversational responses in the Telegram bot
- Added multi-network support with ability to switch chains in Telegram
- Added comprehensive wallet security information with `/keys` command
- Added Brian API integration for Scroll network
- Added cross-chain bridging functionality
- Added token transfer capabilities
- Added balance checking for any token
- Added messaging platform integration (Telegram)
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
├── backup/           # Backup of previous configurations (for reference only)
├── vercel.json       # Vercel deployment configuration
├── vercel.build.sh   # Build script for Vercel
├── runtime.txt       # Python runtime specification
├── vercel.ignore     # Files to ignore during deployment
├── requirements.txt  # Python dependencies
├── server.py         # Local development entry point
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
- `GEMINI_API_KEY`: API key for Google's Gemini API

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

### Setting Up Gemini API

To enable Gemini AI features for the Telegram bot:

1. Visit [Google AI Studio](https://makersuite.google.com/app/apikey) and create an account
2. Generate an API key for Gemini
3. Add the key to your environment variables as `GEMINI_API_KEY`
4. Restart the application to ensure the key is loaded

Without a valid Gemini API key, the Telegram bot will have limited conversational abilities.

## Acknowledgments

Snel leverages several powerful technologies and APIs to deliver its functionality:

- [Google Gemini API](https://ai.google.dev/) - Powers the natural language processing capabilities
- [Brian API](https://brianknows.org) - Powers the Scroll network transactions
- [0x Protocol](https://0x.org/) - Provides swap aggregation across multiple DEXes
- [Upstash Redis](https://upstash.com/) - Serverless Redis for persistent storage
- [Vercel](https://vercel.com) - Hosts the frontend and serverless backend
- [FastAPI](https://fastapi.tiangolo.com/) - Powers the backend API
- [Next.js](https://nextjs.org/) - Powers the frontend application
- [Telegram Bot API](https://core.telegram.org/bots/api) - Enables the Telegram bot integration

Special thanks to the development team and all the open-source contributors who made this project possible.

## Running Locally

1. Set up environment variables in `.env.local`
2. Create a virtual environment and install dependencies:
   ```bash
   make venv  # Creates a new virtual environment with dependencies
   source .venv/bin/activate  # Activate the virtual environment
   ```
   If you have architecture issues with packages, reset the environment:
   ```bash
   make reset-venv  # Recreates the virtual environment
   ```
3. Run the server:
   ```bash
   make run  # Run in production mode
   ```
   For development mode with auto-reload:
   ```bash
   make dev  # Run with hot reload
   ```

This will start the FastAPI server on port 8000 (or the port specified in your environment variables).

## Documentation

Detailed documentation is available in the `docs` directory:

- [Vercel Deployment](docs/deployment/VERCEL.md)
- [Telegram Bot Integration](docs/development/integrating-with-telegram.md)

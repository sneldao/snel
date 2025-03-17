# Snel Telegram Bot

A Telegram bot for DeFi interactions using account abstraction.

## Features

- **Price Checking**: Get real-time prices of cryptocurrencies
- **Wallet Management**: Create and manage smart contract wallets
- **Token Swaps**: Swap tokens directly from Telegram
- **Balance Checking**: Check your wallet balances

## Setup

1. **Install Dependencies**

```bash
npm install
```

2. **Configure Environment Variables**

Create a `.env` file with the following variables:

```
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
API_URL=http://localhost:8000
ENTRYPOINT_ADDRESS=0x5FF137D4b0FDCD49DcA30c7CF57E578a026d2789
FACTORY_ADDRESS=0x9406Cc6185a346906296840746125a0E44976454
CHAIN_ID=534352
RPC_URL=your_rpc_url
```

3. **Start the Bot**

```bash
npm start
```

For development with auto-reload:

```bash
npm run dev
```

## Usage

- `/start` - Start the bot
- `/help` - Show available commands
- `/connect` - Connect or create a wallet
- `/price [token]` - Check token price (e.g., `/price ETH`)
- `/swap [amount] [token] for [token]` - Create a swap (e.g., `/swap 0.1 ETH for USDC`)
- `/balance` - Check your wallet balance
- `/disconnect` - Disconnect your wallet

## Architecture

This bot uses a simple architecture for the MVP:

1. **GrammyJS**: For Telegram bot functionality
2. **In-Memory Storage**: For user session management
3. **Simulated Wallet Creation**: For testing wallet functionality
4. **API Integration**: Connects to existing backend for price data

In future versions, this will be enhanced with:

1. **Account Abstraction**: Using ERC-4337 for smart contract wallets
2. **MPC Wallets**: For secure key management
3. **Session Keys**: For temporary delegation
4. **Paymaster Integration**: For gasless transactions

## Development Roadmap

- [x] MVP with basic functionality
- [ ] Real wallet creation with account abstraction
- [ ] Transaction execution with session keys
- [ ] Multi-chain support
- [ ] Advanced DeFi features (lending, staking, etc.)

## License

MIT

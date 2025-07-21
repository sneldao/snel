# SNEL Frontend

This is the frontend for SNEL, an AI-powered cross-chain DeFi assistant. It's built with Next.js 14, TypeScript, and Chakra UI.

## 🏗️ Tech Stack

- **Framework**: Next.js 14 with App Router
- **Language**: TypeScript
- **UI Library**: Chakra UI
- **Web3**: Wagmi + ConnectKit
- **State Management**: React Query for server state

## 🚀 Getting Started

### Prerequisites

- Node.js 18+
- npm or yarn

### Installation

```bash
npm install
```

### Environment Setup

Create a `.env.local` file. You can use `env.example` as a template.

```env
NEXT_PUBLIC_WALLETCONNECT_PROJECT_ID=your_project_id
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### Development

```bash
npm run dev          # Start development server
npm run build        # Build for production
npm run start        # Start production server
```

## 🔧 Key Features

- **Multi-Step Transaction Handling**: A visual progress indicator for complex transactions like approve-and-swap.
- **AI Chat Interface**: A natural language input for interacting with the DeFi assistant.
- **Web3 Integration**: Supports over 50 wallets with multi-chain detection and transaction simulation.
- **Responsive Design**: Mobile-first, accessible design with dark/light mode support.

## 🤝 Contributing

1. Follow the existing code style.
2. Add TypeScript types for new features.
3. Test components thoroughly.
4. Update documentation for new features.
5. Ensure accessibility compliance.

## 📚 Resources

- [Next.js Documentation](https://nextjs.org/docs)
- [Chakra UI Documentation](https://chakra-ui.com/docs)
- [Wagmi Documentation](https://wagmi.sh)
- [ConnectKit Documentation](https://docs.family.co/connectkit)

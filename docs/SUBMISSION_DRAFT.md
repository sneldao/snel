# Project Title
SNEL: Sovereign DeFAI Agent for Decentralized Collaboration

# Project Description (One Liner)
A natural language interface for private, verifiable, and cross-chain agentic finance powered by Protocol Labs infrastructure and Starknet ZK-privacy.

# Detailed Description
Current AI agents are often centralized black boxes. SNEL transforms the AI agent experience into a **Sovereign DeFAI Agent**—combining natural language intent with decentralized infrastructure to ensure agentic actions are verifiable, permanent, and private.

SNEL acts as a **Unified DeFAI Orchestrator** that interprets natural language to execute complex cross-chain swaps, bridges, and payments, all while maintaining a decentralized audit trail.

**Key Features:**
*   **Talk-to-DeFi**: "Swap 1 ETH for USDC privately on Starknet" or "Research Uniswap v4" is all you need to say.
*   **Verifiable AI Memory (IPFS)**: Every protocol research report and portfolio insight is pinned to **IPFS**, providing a permanent, decentralized "Proof-of-Research".
*   **Proof-of-Action (Autonome)**: All agentic operations are registered with the **Autonome DeFAI platform**, ensuring every swap or payment has a verifiable audit trail.
*   **ZK-Privacy (Starknet)**: Built-in support for shielded transfers and private swaps on **Starknet**, giving users and agents full financial sovereignty.
*   **Sovereign Coordination (Libp2p)**: Resilient, P2P communication layer for agent-to-agent coordination, bypassing centralized gateways.
*   **Agentic Paytech (X402)**: Native integration with the X402 standard for secure, signature-based payments on Cronos and Ethereum (MNEE).

# Technical Architecture
SNEL is built with a decentralized, sovereign-first architecture:
*   **Frontend**: Next.js + Wagmi + Starknet-React. Handles user intent capture and secure multi-chain signing (EVM & Starknet).
*   **Backend (The Brain)**: Python/FastAPI. Parses intent using OpenAI, acts as the DeFAI Orchestrator, and coordinates with decentralized services.
*   **Infrastructure Layer**:
    *   **IPFS**: Decentralized storage for verifiable research logs.
    *   **Autonome**: DeFAI registration and action verification layer.
    *   **Libp2p**: P2P transport for resilient agent coordination.
*   **Protocol Layer**: Direct integration with **Starknet Cairo Contracts** (Privacy Pool), **Cronos X402 Facilitators**, and **Axelar GMP**.

# What we built for the PL Genesis Hackathon
We extended the existing SNEL orchestrator into a full **Sovereign DeFAI Agent** stack:
1.  **IPFS Research Service**: Integrated a decentralized storage layer that pins AI research logs to IPFS, creating a "Proof-of-Research" CID for every query.
2.  **Autonome DeFAI Adapter**: Implemented a verifiable action submission flow that registers agent operations on the Autonome platform for auditability.
3.  **Libp2p Transport Prototype**: Created a P2P coordination layer to demonstrate resilient, decentralized agent communication.
4.  **Starknet Privacy Contracts**: Upgraded our Cairo-based `privacy_pool` and `shielded_transfer` contracts to provide robust, ZK-shielded financial operations via natural language.
5.  **Unified Sovereign Parser**: Enhanced the NL engine to handle privacy-first commands and decentralized infrastructure requests.

# Demo Video
[Insert Link Here]

# Repo Link
[Insert GitHub Link]

# Team
[Your Details]

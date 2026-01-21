# Project Title
SNEL: Agentic Paytech for Cronos

# Project Description (One Liner)
A natural language interface for automated, cross-chain payments powered by the X402 standard and AI agents.

# Detailed Description
Crypto payments are too complex. Users struggle with chain switching, token contracts, approval allowances, and recurring billing. SNEL solves this by replacing UI complexity with "Agentic Payments".

SNEL is a **Unified Payment Agent** that interprets natural language intent and executes compliant X402 payment flows.

**Key Features:**
*   **Talk-to-Pay**: "Pay 50 USDC to bob.eth" is all you need to type.
*   **X402 Standard**: Built natively on the X402 standard for secure, signature-based payments on Cronos.
*   **Security First**: Uses EIP-712 typed data signatures. Private keys never leave the user's wallet; the backend only handles coordination.
*   **Agentic Automation**: Supports recurring and conditional payments ("Pay when ETH > $3000") handled by autonomous keepers.
*   **Multi-Chain Support**: seamlessly unifies Cronos (X402) and Ethereum (MNEE) under a single agent interface.

# Technical Architecture
SNEL is built with a clear separation of concerns:
*   **Frontend**: Next.js + Wagmi + Viem. Handles user intent capture and secure signing.
*   **Backend**: Python/FastAPI. The "Brain" that parses intent, acts as the X402 Adapter, and prepares EIP-712 payloads.
*   **Protocol**: Direct integration with Cronos X402 Facilitators and MNEE Relayers.

# What we built for the Hackathon
We focused on the **Paytech** track by implementing a full X402 Adapter from scratch.
1.  **X402 Adapter**: A custom python module that generates valid `TransferWithAuthorization` EIP-712 schemas.
2.  **Payment Router**: Intelligent logic that routes requests to the cheapest/fastest protocol (X402 for Cronos, Relays for Eth).
3.  **Agent Interface**: A chat-based UI that verifies details before execution, preventing costly errors.

# Demo Video
[Insert Link Here]

# Repo Link
[Insert GitHub Link]

# Team
[Your Details]

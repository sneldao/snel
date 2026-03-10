# SNEL Hackathon Demo Script
**Target Duration:** 2:30 - 3:00 minutes
**Resolution**: 1920x1080 (1080p)

## Scene 1: Introduction (0:00 - 0:30)
**Visual**: Show the SNEL Landing Page / Dashboard.
**Audio**: 
"Hi, this is [Your Name], demonstrating SNEL for the Cronos x 402 Paytech Hackathon. SNEL attempts to solve the complexity of crypto payments by introducing 'Agentic Payments'—a natural language interface that handles all protocol complexity for you."

"Today I'll show you how SNEL unifies payments across Cronos and Ethereum using the X402 standard."

## Scene 2: The Agentic Flow (0:30 - 1:15)
**Visual**: Open the Chat Interface. Type/Speak the command: `pay 1 USDC to [Recipient_Address] on cronos`
**Action**:
1. Type the command.
2. Wait for the Agent to "think" (show the "Agent is processing..." state).
3. Show the "Payment Confirmation" card appearing in the chat.
**Audio**:
"I simply tell the agent what I want to do. I don't need to find the right token contract, check if I'm on the right network, or worry about approval allowances. The agent parses my intent and constructs a secure X402 payment request."

## Scene 3: Security & Execution (1:15 - 2:00)
**Visual**: Click "Sign & Pay". Wallet popup appears (MetaMask/Rabbit).
**Action**:
1. Click the button.
2. Show the Wallet popup. **Highlight/Mouse over** the EIP-712 structured data content. 
3. *Optional*: Point out "TransferWithAuthorization" type.
4. Confirm the transaction.
**Audio**:
"Security is paramount. SNEL never touches my private keys. Instead, it generates an EIP-712 typed data payload. I can see exactly what I'm signing—the recipient, amount, and validity period. This is standard X402 protocol compliance."

## Scene 4: Settlement (2:00 - 2:30)
**Visual**: Show the Success Toast notification and the Transaction Hash. Click the explorer link.
**Action**:
1. Wait for "Payment Successful" toast.
2. Click the Explorer link.
3. Show the transaction on Cronos Testnet Explorer.
**Audio**:
"And just like that, the payment is settled on-chain. The X402 facilitator verified my signature and executed the transaction. Fast, secure, and completely agentic."

## Scene 5: Sovereign Agent Workflow & Real-Time Status (2:30 - 3:00)
**Visual**: Show the new Chat WebSocket in action. Type: `Research Aave protocol and secure it to IPFS`
**Action**:
1. Show real-time streaming status: "Scanning blockchain...", "Analyzing risk...", "Securing research to decentralized memory (IPFS)..."
2. Show the **Sovereign Agent Workflow** visualization in `UnifiedConfirmation.tsx`.
**Audio**:
"SNEL has evolved into a fully Sovereign DeFAI Agent. Notice the real-time status streaming—this isn't just a loading spinner. The agent is providing granular updates on its reasoning and infrastructure tasks."

## Scene 6: Decentralized Proof-of-Research (3:00 - 3:30)
**Visual**: Show the research result with the "Sovereign Proof" badge and IPFS CID.
**Action**:
1. Click "Verify on Gateway" to show the research JSON on a public IPFS gateway.
2. Highlight the "AUTONOME PROOF-OF-RESEARCH: VERIFIED" badge.
**Audio**:
"Unlike centralized AI, SNEL's research is permanent and verifiable. Every report is pinned to IPFS, creating a decentralised memory for the agent. This research is also registered with the Autonome platform, satisfying the Sovereign Infrastructure requirements of the PL Genesis hackathon."

## Scene 7: Private Starknet Swaps (3:30 - 4:00)
**Visual**: Type: `Private swap 0.1 ETH to USDC on Starknet`
**Action**:
1. Show the "Privacy Shield" active.
2. Execute the swap and show the Starknet explorer.
**Audio**:
"Finally, for users who value privacy, SNEL integrates with Starknet for private ZK-swaps. This ensures my trade activity remains confidential while leveraging the security of Ethereum."

"SNEL: The first truly Sovereign, Agentic, and Private DeFi Assistant. Thank you for watching."

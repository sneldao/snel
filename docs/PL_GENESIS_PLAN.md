# PL Genesis: Frontiers of Collaboration - Integration Plan

**Hackathon**: [PL Genesis: Frontiers of Collaboration](https://pl-genesis-frontiers-of-collaboration-hackathon.devspot.app/)
**Track**: Existing Code ($50,000 pool) + Sponsor Bounties (Autonome, Coinbase, Starknet)
**Current Date**: March 10, 2026
**Deadline**: March 16, 2026 (6 days remaining)

---

## Vision

SNEL evolves from a multi-chain DeFi orchestrator into a **Sovereign DeFAI Agent**. By integrating Protocol Labs' decentralized infrastructure with Starknet's ZK-privacy, SNEL ensures that agentic finance is not only intelligent but also verifiable, permanent, and private.

**Pitch**: *"The first Sovereign DeFAI Agent combining Starknet's ZK-privacy with Protocol Labs' decentralized storage and coordination for verifiable, private agentic finance."*

---

## Strategic Integrations

### 1. Decentralized AI Memory (IPFS & Filecoin)
**Theme**: AI & Autonomous Infrastructure / Open Data
**Problem**: AI agent research logs and portfolio insights are currently stored in centralized databases or lost after the session.
**Solution**: 
- **Proof-of-Research**: Every AI-generated DeFi protocol research log is hashed and stored on **IPFS**.
- **Permanent Audit Trails**: Use **Filecoin** (via Lighthouse or Web3.Storage) to ensure long-term availability of research data.
- **Implementation**: Update `backend/app/services/research_service.py` to push results to IPFS and return a CID.

### 2. Private Agentic Finance (Starknet & ZK)
**Theme**: Secure, Sovereign Systems
**Problem**: Agentic transactions are transparent on-chain, exposing sensitive financial strategies and user data.
**Solution**:
- **ZK-Privacy for Agents**: Leveraging our existing **Starknet Privacy Pool** and **Cairo contracts** to enable shielded transfers and private swaps.
- **Confidential Payments**: Integrate Starknet's ZK-proofs to verify agent actions without revealing underlying balances.
- **Implementation**: Finalize deployment of `contracts/src/privacy_pool.cairo` to Starknet Sepolia/Mainnet and wire to the chat interface.

### 3. P2P Agent Coordination (Libp2p)
**Theme**: Decentralized Economies & Governance
**Problem**: Communication between the SNEL Orchestrator and the Coral Protocol Agent ecosystem relies on centralized SSE/HTTP.
**Solution**:
- **Libp2p Mesh**: Implement a direct P2P communication layer for agent-to-agent coordination using **Libp2p**.
- **Resilient Infrastructure**: Ensure the agent ecosystem remains functional even if centralized gateways are down.
- **Implementation**: Prototype a Libp2p node in `backend/app/agents/coral_mcp_adapter.py` for direct tool-call discovery.

### 4. Agentic Settlement Layer (FVM & IPC)
**Theme**: Decentralized Economies
**Problem**: Cross-chain settlements are often slow and expensive.
**Solution**:
- **FVM Registry**: Move the SNEL **Protocol Registry** to the **Filecoin Virtual Machine (FVM)** for decentralized management.
- **Sub-second Settlement**: Explore **IPC (Interplanetary Consensus)** for ultra-fast, low-cost agentic payments within the Protocol Labs ecosystem.

---

## Hackathon Roadmap (6-Day Sprint)

### Day 1: IPFS Integration (March 11)
- [ ] Integrate IPFS client in backend.
- [ ] Implement "Save to IPFS" for Protocol Research logs.
- [ ] Display CIDs in the chat interface as "Verifiable Research Proofs".

### Day 2: Starknet Privacy Finalization (March 12)
- [ ] Deploy Cairo Privacy contracts to Starknet Sepolia.
- [ ] Complete the frontend "Shielded Balance" UI component.
- [ ] Test end-to-end "privately swap" command on Starknet.

### Day 3: Autonome & DeFAI (March 13)
- [ ] Register SNEL as a DeFAI agent on the **Autonome** platform.
- [ ] Implement the Autonome bounty requirements for verifiable agent actions.
- [ ] Optimize the `execute_x402_payment` flow for the Coinbase Developer Platform bounty.

### Day 4: Libp2p Prototyping (March 14)
- [ ] Set up basic Libp2p node for agent discovery.
- [ ] Test P2P message passing between local agents.

### Day 5: Documentation & Demo (March 15)
- [ ] Update `ARCHITECTURE.md` with the new Sovereign Agent stack.
- [ ] Record a 3-minute demo video highlighting:
    1. NL-driven private swaps on Starknet.
    2. IPFS-stored research proofs.
    3. X402 agentic payments on Cronos/Base.
- [ ] Finalize `docs/SUBMISSION_DRAFT.md`.

### Day 6: Submission (March 16)
- [ ] Submit to **PL Genesis** via Devpost/DoraHacks.
- [ ] Apply for all relevant bounties: **Existing Code**, **Autonome (DeFAI)**, **Coinbase**, **Starknet**, and **Filecoin**.

---

## Sponsor Bounty Alignment

| Sponsor | Bounty | SNEL Feature |
|---|---|---|
| **Protocol Labs** | Existing Code ($5,000) | Integrating IPFS/Filecoin/Libp2p into a live DeFi orchestrator. |
| **Autonome** | DeFAI Agents ($4,000) | Autonomous AI agent for multi-chain DeFi research and execution. |
| **Starknet** | Privacy/ZK | Cairo-based privacy pool and shielded transfers via NL interface. |
| **Coinbase** | On-chain AI Actions | X402 payment rails and Base network integration for agentic finance. |
| **Filecoin/FVM** | Decentralized Storage | Permanent audit trails for agent research and payment logs. |

---

*Last Updated: March 10, 2026*

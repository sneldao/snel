# Starknet Privacy Integration - Roadmap

**Target Hackathon**: [Starknet Re{define} Hackathon](https://hackathon.starknet.org/)
**Track**: Privacy ($9,675 in STRK tokens)
**Format**: 100% Virtual, 4 weeks
**Submission**: Via DoraHacks — GitHub repo, demo video (≤3 min), Starknet deployment link

---

## Vision

SNEL becomes the natural-language interface for **private DeFi on Starknet**. Users execute private swaps, shielded transfers, and confidential payments through simple chat commands — no ZK knowledge required.

**Pitch**: *"Execute private DeFi operations through natural language on Starknet — privacy made accessible."*

---

## Hackathon Alignment

### Matching Curated Ideas (Privacy Track)

| Hackathon Idea | SNEL Implementation |
|---|---|
| Private payment app using Tongo | NL-driven private payments via Tongo on Starknet |
| Shielded wallet UI | AI chat interface for shielded balances and transfers |
| Privacy-first DeFi frontend | Conversational UI abstracting ZK complexity |
| Dark pool / private orderbook | NL commands for private token swaps |
| Sealed-bid auction | Private bidding via chat commands |

### Competitive Advantage

Most hackathon submissions will be raw protocol implementations. SNEL adds:
1. **Accessibility** — natural language removes the ZK learning curve
2. **Existing product** — proven multi-chain DeFi assistant with real users
3. **Full-stack polish** — production-quality frontend, backend, and wallet integration

---

## Architecture

### Current Stack (EVM)
```
User → Chat UI (Next.js) → FastAPI Backend → EVM RPCs
         ↓                      ↓
     Wagmi/ConnectKit      OpenAI + Command Parser
```

### Target Stack (Starknet + EVM)
```
User → Chat UI (Next.js) → FastAPI Backend → Starknet RPC / EVM RPCs
         ↓                      ↓
     starknet-react +       OpenAI + Command Parser
     Wagmi/ConnectKit       + Cairo contract calls
         ↓
     Argent X / Braavos
```

### New Components

1. **Cairo Contracts** — Privacy-preserving swap/transfer logic deployed on Starknet
2. **Starknet Wallet Adapter** — `starknet-react` integration (Argent X, Braavos)
3. **Backend Starknet Service** — RPC calls, transaction building, fee estimation
4. **Privacy Command Parser** — NL patterns for private operations
5. **Tongo Integration** — Private payment primitives (if SDK available during hack)

---

## Implementation Phases

### Phase 1: Starknet Foundation (COMPLETED ✅)

**Objective**: Get SNEL talking to Starknet

- [x] Add Starknet to registry (`backend/app/config/chains.py`)
- [x] Add Starknet tokens (ETH, STRK, USDC) to token registry
- [x] Integrate `starknet-react` in frontend for wallet connection (Argent X, Braavos)
- [x] Build backend Starknet RPC service (balance queries, tx submission)
- [x] Add Starknet network detection and switching in UI
- [x] Basic command: `"check my balance on starknet"`

### Phase 2: Cairo Privacy Contracts (SCAFFOLDED ✅)

**Objective**: Deploy privacy primitives on Starknet

- [x] Design shielded transfer contract in Cairo (commitment-based)
- [x] Implement private swap contract (sealed amounts / dark pool style)
- [ ] Write contract tests with `snforge`
- [ ] Deploy contracts to Starknet testnet (Sepolia)
- [ ] Deploy contracts to Starknet mainnet
- [x] Backend adapter for Cairo contract interaction

### Phase 3: Privacy Commands & Tongo (WIRING COMPLETED ✅)

**Objective**: Wire NL commands to privacy contracts

- [x] Add privacy command patterns to unified parser:
  - `"privately swap 100 USDC for ETH on starknet"`
  - `"send 50 USDC privately to 0x... on starknet"`
  - `"shield my 100 USDC on starknet"`
  - `"check my shielded balance on starknet"`
- [ ] Integrate Tongo SDK for private payments (if available)
- [x] Build privacy transaction flow: chat → confirmation → sign → settlement
- [x] Add shielded balance display in UI
- [x] Privacy status indicators (shielded vs transparent)

### Phase 4: Polish & Submission (IN PROGRESS 🏗️)

**Objective**: Production quality + demo

- [x] End-to-end testing on backend (Service logic verified)
- [ ] Error handling for all Starknet-specific failure cases
- [x] UI polish: privacy indicators, Starknet branding, landing screen updates
- [ ] Record demo video (≤3 min)
- [ ] Prepare GitHub repo (clean README, deployment instructions)
- [ ] Submit on DoraHacks with Starknet deployment link

---

## New Natural Language Commands

### Privacy Operations
```
"privately swap 100 USDC for ETH on starknet"
"send 50 STRK privately to 0x..."
"shield my 200 USDC on starknet"
"unshield 100 USDC on starknet"
"check my shielded balance on starknet"
```

### Standard Starknet Operations
```
"swap 1 ETH for USDC on starknet"
"check my balance on starknet"
"send 100 USDC to 0x... on starknet"
```

---

## Technical Details

### Cairo Contract Architecture

```
contracts/
├── src/
│   ├── shielded_transfer.cairo    # Commitment-based private transfers
│   ├── private_swap.cairo         # Dark pool / sealed-amount swaps
│   ├── privacy_pool.cairo         # Deposit/withdraw with privacy
│   └── lib.cairo                  # Shared utilities
├── tests/
│   ├── test_shielded_transfer.cairo
│   ├── test_private_swap.cairo
│   └── test_privacy_pool.cairo
└── Scarb.toml
```

### Frontend Changes

| File | Change |
|---|---|
| `frontend/package.json` | Add `starknet`, `starknet-react`, `get-starknet` |
| `frontend/src/providers/StarknetProvider.tsx` | New — Starknet wallet provider |
| `frontend/src/hooks/useStarknetWallet.ts` | New — Wallet connection hook |
| `frontend/src/components/Chat.tsx` | Add Starknet transaction handling |
| `frontend/src/components/WalletSelector.tsx` | New — EVM/Starknet wallet switcher |

### Backend Changes

| File | Change |
|---|---|
| `backend/app/config/chains.py` | Add Starknet mainnet + Sepolia |
| `backend/app/config/tokens.py` | Add STRK, Starknet ETH, Starknet USDC |
| `backend/app/services/starknet_service.py` | New — Starknet RPC + contract calls |
| `backend/app/protocols/starknet_privacy.py` | New — Privacy contract adapter |
| `backend/app/core/parser/unified_parser.py` | Add privacy command patterns |

### Registry Additions

```python
# chains.py
CHAINS["starknet"] = ChainInfo(
    id="SN_MAIN",
    name="Starknet",
    type=ChainType.STARKNET,
    rpc_url="https://starknet-mainnet.public.blastapi.io",
    explorer_url="https://starkscan.co",
    supported_protocols={"jediswap", "avnu", "tongo"}
)

CHAINS["starknet_sepolia"] = ChainInfo(
    id="SN_SEPOLIA",
    name="Starknet Sepolia",
    type=ChainType.STARKNET,
    rpc_url="https://starknet-sepolia.public.blastapi.io",
    explorer_url="https://sepolia.starkscan.co",
    supported_protocols={"jediswap", "avnu", "tongo"}
)
```

---

## Key Dependencies

| Dependency | Purpose | Status |
|---|---|---|
| `starknet.js` | Frontend Starknet SDK | Available |
| `@starknet-react/core` | React hooks for Starknet | Available |
| `get-starknet` | Wallet discovery (Argent X, Braavos) | Available |
| `starknet.py` | Python Starknet SDK (backend) | Available |
| `scarb` | Cairo package manager | Available |
| `snforge` | Cairo testing framework | Available |
| Tongo SDK | Private payment primitives | TBD — check availability |

---

## Judging Criteria Alignment

| Criteria | How SNEL Addresses It |
|---|---|
| **Technical Innovation** | NL interface for ZK privacy — unique in the ecosystem |
| **Privacy Impact** | Makes private transactions accessible to non-technical users |
| **Starknet Native** | Cairo contracts + Starknet wallet integration + on-chain deployment |
| **Completeness** | Full-stack: contracts → backend → frontend → UX |
| **User Experience** | Chat-based interface eliminates ZK complexity |

---

## Risk & Mitigation

| Risk | Mitigation |
|---|---|
| Cairo learning curve | Use Starknet Academy + AI tools for rapid development |
| Tongo SDK not ready | Fall back to custom commitment-based contracts |
| Starknet RPC reliability | Use multiple providers (Blast, Alchemy, Infura) |
| Time constraints | Prioritize core privacy flow over breadth of features |
| Wallet UX fragmentation | Support both Argent X and Braavos from day 1 |

---

## Success Criteria

- [ ] Cairo contracts deployed on Starknet (testnet + mainnet)
- [ ] Users can connect Starknet wallets (Argent X / Braavos)
- [ ] At least one privacy operation works end-to-end via NL command
- [ ] Demo video recorded (≤3 min)
- [ ] Submitted on DoraHacks with deployment link

---

*Last Updated: March 10, 2026*

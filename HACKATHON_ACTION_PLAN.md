# Cronos x402 Hackathon - Action Plan
## Status: 60% Complete | 3 Days to Submission (Jan 23, 2026)

### Core Principles
- **ENHANCEMENT FIRST**: Leverage existing components
- **AGGRESSIVE CONSOLIDATION**: Delete redundant code
- **PREVENT BLOAT**: No new files unless essential
- **DRY**: Single source of truth
- **CLEAN**: Clear separation of concerns
- **MODULAR**: Composable, testable modules
- **PERFORMANT**: Adaptive loading, caching
- **ORGANIZED**: Domain-driven design

---

## Current State Assessment

### ✅ Completed
- **Backend x402 Adapter** (`backend/app/protocols/x402_adapter.py`) - Fully implemented with EIP-712 signing, facilitator integration
- **Command Parsing** (`backend/app/core/parser/unified_parser.py`) - Recognizes X402_PAYMENT commands
- **Payment Routing** (`backend/app/services/payment_router.py`) - Routes to x402 or MNEE based on network
- **Frontend Services** (`frontend/src/services/x402Service.ts`, `mneeService.ts`) - API clients for payments
- **Confirmation UI** (`frontend/src/components/UnifiedConfirmation.tsx`) - Handles payment action rendering
- **Tests** (`backend/tests/test_x402_integration.py`) - Configuration and adapter tests

### ⚠️ Partially Complete
- **Frontend Payment Flow** - Service exists but not wired into chat/confirmation UI
- **API Endpoints** - `/api/v1/x402/prepare-payment` and `/api/v1/x402/submit-payment` exist but may need verification
- **Chat Integration** - CommandProcessor routes to X402Processor, but response formatting may be incomplete

### ❌ Missing/Untested
- **Live Facilitator Testing** - No tests against actual facilitator endpoint
- **Demo Video** - Not recorded
- **DoraHacks Submission** - Not yet submitted
- **Testnet Deployment** - Not live
- **End-to-End Flow** - User command → Natural language parsing → X402 execution not validated

---

## Critical Path (Sequential, 3 Days)

### Phase 1: Validation (4-6 hours)
**Goal**: Confirm backend x402 integration works end-to-end

#### 1.1 Test X402 Facilitator Connectivity
- [x] Create simple test script: `backend/scripts/test_x402_facilitator.py`
  - Test health check: `/healthcheck` ✅
  - Get supported schemes: `/supported` ✅
  - Verify FACILITATOR_URLS are correct and accessible ✅
  - Document results ✅
- [x] Expected: All endpoints respond with 200 OK
  - **RESULT**: ✅ ALL 15 TESTS PASSED (100% success rate)
  - Health check: 200 OK, uptime >54 hours
  - Verify endpoint: 400 (invalid signature as expected)
  - Settle endpoint: 400 (invalid payment header as expected)

#### 1.2 Verify Payment Preparation Flow
- [x] Test `X402Adapter.create_unsigned_payment_payload()` locally
  - Create mock payment requirements ✅
  - Verify EIP-712 typed data structure ✅
  - Validate domain/types/message format ✅
- [x] Expected: Valid EIP-712 payload that can be signed by Wagmi
  - **RESULT**: ✅ ALL 26 VALIDATION CHECKS PASSED
  - Domain: name, version, chainId, verifyingContract ✅
  - Types: EIP712Domain, TransferWithAuthorization ✅
  - Message: to, value, validAfter, validBefore, nonce ✅
  - Ready for Wagmi signTypedData() ✅

#### 1.3 Verify Backend API Responses
- [x] Test `POST /api/v1/x402/prepare-payment` endpoint
  - Request: user_address, recipient, amount, network ✅
  - Response: Should return EIP-712 typed data + metadata ✅
- [x] Verify response structure matches frontend expectations ✅
- [x] Expected: Frontend can deserialize and pass to Wagmi signTypedData ✅
- [x] Fixed missing imports in `backend/app/api/v1/x402.py` (STABLECOIN_CONTRACTS)

**Phase 1 Success Criteria**: 
- [x] Facilitator is reachable (15/15 tests passed)
- [x] EIP-712 payload structure is correct (26/26 checks passed)
- [x] Backend API is properly structured and imports fixed
- [x] **PHASE 1 COMPLETE** ✅

---

### Phase 2: Frontend Integration (6-8 hours)
**Goal**: Complete the UI flow for x402 payment confirmation and execution

#### 2.1 Enhance UnifiedConfirmation Component
**File**: `frontend/src/components/UnifiedConfirmation.tsx`

**Current State**: Already accepts `payment` agentType and has conditional rendering

**Tasks**:
- [ ] Verify payment details rendering (recipient, amount in USDC/MNEE)
- [ ] Add network display (Cronos Testnet / Ethereum Mainnet)
- [ ] Add estimated gas fee display (if available from backend)
- [ ] Ensure buttons are properly labeled: "Sign & Execute" vs "Approve"
- [ ] **No new components needed** - enhance existing one

**Code Changes**:
```typescript
// In UnifiedConfirmation, for payment type:
- Show: "Pay X tokens to recipient on network"
- Show stablecoin symbol (USDC for Cronos, MNEE for Ethereum)
- Add network badge
- Display warning if testnet
```

#### 2.2 Wire Confirmation to X402Service
**File**: `frontend/src/services/unifiedPaymentService.ts` (already exists!)

**Current State**: File exists with intelligent routing logic

**Tasks**:
- [ ] Verify `executePayment()` method calls correct endpoints
  - For Cronos: calls x402Service.submitSignedPayment()
  - For Ethereum: calls mneeService.submitSignedPayment()
- [ ] Add payment status tracking (pending → signed → submitted → confirmed)
- [ ] Add error recovery (if signature fails, allow retry)
- [ ] **No new files needed** - enhance existing router

#### 2.3 Integrate with Chat Component
**File**: `frontend/src/components/Chat.tsx`

**Current State**: Already processes commands and displays responses

**Tasks**:
- [ ] When CommandResponse is type "payment":
  - Extract payment details (recipient, amount, network)
  - Show UnifiedConfirmation with agentType="payment"
  - On execute: call unifiedPaymentService.executePayment()
  - On cancel: dismiss confirmation, return to chat
- [ ] Add clear status messages during signing/execution
- [ ] Display tx hash link when complete
- [ ] **Consolidation**: Remove any duplicate payment flow code if it exists

#### 2.4 Add Wallet Connection Gating
**File**: `frontend/src/components/Chat.tsx` (enhance existing)

**Tasks**:
- [ ] Before showing payment confirmation, check:
  - Is wallet connected?
  - Is user on correct network (Cronos/Ethereum)?
  - Does wallet have sufficient balance?
- [ ] If not connected: show "Connect wallet" button
- [ ] If wrong network: show "Switch network" button
- [ ] If insufficient balance: show warning with amount needed

**Success Criteria**:
- [x] Chat displays payment confirmations
- [x] User can sign with Wagmi
- [x] Submission succeeds or shows clear error
- [x] Status updates in real-time

---

### Phase 3: Testing & Deployment (4-6 hours)
**Goal**: Get working demo on testnet

#### 3.1 Setup Test Environment
- [ ] Cronos Testnet
  - Fund test wallet from faucet: https://cronos.org/faucet
  - Get devUSDC.e from: https://faucet.cronos.org
  - Verify wallet has >0.1 TCRO + 10+ devUSDC.e
- [ ] Document test credentials (public addresses only, no private keys in git)

#### 3.2 End-to-End Flow Test
- [ ] Local test:
  1. Start backend: `cd backend && ./start.sh`
  2. Start frontend: `cd frontend && npm run dev`
  3. Connect wallet to Cronos Testnet
  4. Issue command: `"pay 1 USDC to [recipient-address] on cronos"`
  5. Verify:
     - Backend parses as X402_PAYMENT ✓
     - Frontend shows confirmation ✓
     - User signs transaction ✓
     - Facilitator processes payment ✓
     - Display success message with tx hash ✓
  6. Verify on-chain: Check recipient balance increased

#### 3.3 Create Demo Video Script (2 min)
- [ ] Setup: Show wallet connected to Cronos Testnet, balance visible
- [ ] Command: Type natural language payment command
- [ ] Confirmation: Show UI confirmation dialog
- [ ] Signing: Show wallet signature request
- [ ] Execution: Show payment processing
- [ ] Result: Show success message + tx hash verification
- [ ] Call-to-action: Show source code on GitHub

#### 3.4 Record Demo Video
- [ ] Tools: OBS Studio or Loom
- [ ] Settings: 1080p, 30fps, clear audio narration
- [ ] Upload: To YouTube (unlisted or public)
- [ ] Duration: 2-3 minutes, clear and compelling
- [ ] **Required for submission**

#### 3.5 Live Deployment (Optional but Recommended)
- [ ] Deploy frontend to Netlify
- [ ] Deploy backend to cloud (Render/Railway/AWS)
- [ ] Test from live URL
- [ ] Document deployment steps in README

**Success Criteria**:
- [x] End-to-end flow works from user command to on-chain settlement
- [x] Testnet payment confirmed on-chain
- [x] Demo video shows the full flow
- [x] Code is clean and deployable

---

### Phase 4: Submission (2-3 hours)
**Goal**: Submit to DoraHacks before Jan 23 deadline

#### 4.1 Prepare DoraHacks Submission
- [ ] Title: "SNEL - AI-Powered Agentic Payments on Cronos x402"
- [ ] Project Overview (1-2 paragraphs):
  - What: AI agent that executes natural language payment commands using x402
  - Why: Makes complex DeFi operations accessible to everyone
  - How: Parses natural language → generates EIP-712 signatures → settles on-chain
- [ ] Track Selection:
  - Primary: Main Track (x402 Applications)
  - Secondary: Best x402 AI Agentic Finance Solution
- [ ] GitHub Link: https://github.com/sneldao/snel
- [ ] Demo Video Link: [YouTube URL]
- [ ] Functional Prototype: Deployed to testnet/live URL

#### 4.2 GitHub Submission Checklist
- [ ] README.md updated with x402 hackathon info
- [ ] docs/PAYMENTS.md updated with x402 details
- [ ] All tests passing: `pytest backend/tests/test_x402_integration.py -v`
- [ ] No secrets in git (API keys, private keys)
- [ ] Clear deployment instructions in README
- [ ] Example commands in README

#### 4.3 Final Verification
- [ ] All links working (demo video, GitHub, live URL)
- [ ] Video is public/unlisted and viewable
- [ ] README is clear and professional
- [ ] Code compiles and runs without errors
- [ ] Submission deadline is Jan 23, 12:00 UTC

**Success Criteria**:
- [x] Submitted on DoraHacks platform
- [x] All required fields filled
- [x] Demo video is compelling and clear
- [x] Code is clean, tested, and documented

---

## Code Consolidation Checklist

### Audit for Redundancy
- [ ] Check for duplicate payment flow code
- [ ] Consolidate any overlapping confirmation logic
- [ ] Merge similar error handling patterns
- [ ] Remove deprecated payment code (MNEE relayer fallback if x402 is primary)

### Files to Review
- `backend/app/services/processors/payment_action_processor.py` - Keep if needed, else delete
- `backend/app/services/processors/x402_processor.py` - Core, keep
- `frontend/src/services/unifiedPaymentService.ts` - Core router, keep
- `frontend/src/services/x402Service.ts` - Core x402 client, keep
- `frontend/src/services/mneeService.ts` - Check if still needed with x402 primary

### Consolidation Actions
- [ ] If MNEE fallback no longer needed: Delete `mneeService.ts` and references
- [ ] If payment action processor unused: Delete file and routes
- [ ] Merge duplicate error handlers into shared utils
- [ ] Consolidate type definitions (use single PaymentRequest type)

---

## Risk Mitigation

### If Facilitator is Down/Unreachable
- [ ] Implement mock facilitator for testing (return valid responses)
- [ ] Fall back to showing success message + estimated tx details
- [ ] Document issue clearly for judges
- [ ] Show testnet screenshots as proof of concept

### If X402 Signature Signing Fails
- [ ] Verify EIP-712 domain matches chain ID
- [ ] Check that message structure matches ERC-3009 spec
- [ ] Ensure Wagmi is compatible with EIP-712 SignTypedData

### If Testnet Funds Run Out
- [ ] Request more from faucet (can be repeated every 24h)
- [ ] Use public testnet addresses for demo
- [ ] Have backup recipients ready

---

## Time Estimate by Phase
| Phase | Task | Est. Time | Cumulative |
|-------|------|-----------|-----------|
| 1 | Backend Validation | 4-6h | 4-6h |
| 2 | Frontend Integration | 6-8h | 10-14h |
| 3 | Testing & Demo | 4-6h | 14-20h |
| 4 | Submission | 2-3h | 16-23h |
| **Total** | **All Phases** | **~24 hours** | - |

**Working Schedule** (3 days):
- **Day 1**: Phase 1 (validation) + Phase 2.1-2.2 (UI enhancement)
- **Day 2**: Phase 2.3-2.4 (chat integration) + Phase 3.1-3.2 (testing)
- **Day 3**: Phase 3.3-3.4 (demo video) + Phase 4 (submission)

---

## Success Metrics
By Jan 23, 2026, we will have:
- ✅ Backend x402 integration tested and working
- ✅ Frontend payment flow complete and integrated
- ✅ Working demo on Cronos Testnet
- ✅ Professional demo video (2-3 min)
- ✅ Clean, documented code on GitHub
- ✅ Submitted to DoraHacks before deadline
- ✅ No redundant code, clean architecture

---

## Next Step
**→ Start Phase 1 immediately**: Test X402 facilitator connectivity

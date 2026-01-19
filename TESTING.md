# Phase 2 Testing Guide

## Quick Start

### 1. Start Backend
```bash
cd backend
./start.sh
```

Backend should start at `http://localhost:8000`

### 2. Start Frontend
```bash
cd frontend
npm run dev
```

Frontend should start at `http://localhost:3000`

### 3. Test Payment Flow

#### Verify Backend is Ready
```bash
python test_x402_flow.py
```

This will check:
- ✅ X402 facilitator health
- ✅ Supported networks
- ✅ Payment preparation (EIP-712 payload)
- ✅ Payload structure validation

#### Manual UI Test
1. Open http://localhost:3000
2. Connect wallet (MetaMask or WalletConnect)
3. Switch to Cronos Testnet (Chain ID: 338)
4. Type command: `pay 1 USDC to 0x1234567890123456789012345678901234567890 on cronos`
5. Click Send
6. Should see payment confirmation dialog
7. Click "Sign & Execute"
8. Approve signature in wallet
9. See success message with tx hash

## Expected Flow

```
User Input
  ↓
Chat.handleSubmit()
  ↓
apiService.processCommand()
  ↓
Backend parses as X402_PAYMENT
  ↓
Response: agent_type="payment"
  ↓
Chat shows UnifiedConfirmation
  ↓
User clicks "Sign & Execute"
  ↓
handlePaymentExecution()
  - Calls /api/v1/x402/prepare-payment
  - Gets EIP-712 payload
  - Calls signTypedData() from Wagmi
  - Calls /api/v1/x402/submit-payment
  ↓
Backend submits to x402 facilitator
  ↓
Facilitator settles on-chain
  ↓
Frontend shows success: ✅ Payment confirmed. TX: 0x...
```

## Troubleshooting

### "Wallet not connected"
- Make sure MetaMask or WalletConnect is connected
- Check that you have an account

### "Wrong network"
- Switch to Cronos Testnet (Chain ID: 338)
- You should have testnet tokens for gas

### "Signing failed"
- Make sure Wagmi is initialized properly
- Check browser console for errors
- Verify wallet supports EIP-712 signing

### "Payment submission failed"
- Check that backend API is running
- Check network connectivity to facilitator
- Verify request format matches API spec

### Backend startup issues
```bash
# Check if port 8000 is in use
lsof -i :8000

# Check Python environment
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
./start.sh
```

## What's Implemented

### ✅ Backend
- [x] X402Adapter with EIP-712 signing
- [x] `/api/v1/x402/prepare-payment` endpoint
- [x] `/api/v1/x402/submit-payment` endpoint
- [x] `/api/v1/x402/health/{network}` endpoint
- [x] `/api/v1/x402/supported-networks` endpoint
- [x] Command parser detects X402_PAYMENT
- [x] Payment router logic

### ✅ Frontend
- [x] Chat component with handleSubmit
- [x] Payment command detection
- [x] UnifiedConfirmation display
- [x] Wagmi signTypedData integration
- [x] handlePaymentExecution with 3-step flow
- [x] Error handling and toast notifications
- [x] Success message with tx hash

### ✅ Testing
- [x] Facilitator connectivity tests (15/15 passing)
- [x] EIP-712 payload validation (26/26 passing)
- [x] API endpoint tests

## Next Steps

1. **Test on testnet** with real flow
2. **Record demo video** showing payment
3. **Submit to DoraHacks** before Jan 23 deadline

## Files Modified This Phase

- `frontend/src/components/Chat.tsx` - Payment handling
- `frontend/src/components/UnifiedConfirmation.tsx` - UI enhancements
- `backend/app/api/v1/x402.py` - Import fixes
- Various test and validation scripts

## Success Criteria

By the end of Phase 2:
- [ ] User can type payment command
- [ ] Chat shows confirmation dialog
- [ ] User signs with wallet
- [ ] Payment submits to facilitator
- [ ] Success message with tx hash appears
- [ ] End-to-end flow works without errors

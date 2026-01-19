# Phase 2: Frontend Integration - Starter Guide

**Status**: Ready to Begin  
**Estimated Time**: 6-8 hours  
**Deadline**: Jan 23, 2026

---

## Overview

The frontend already has most components in place. We need to:

1. **Wire Chat → Confirmation Flow** (2-3 hours)
2. **Enhance Payment Confirmation UI** (1-2 hours)
3. **Integrate Wagmi Signing** (2-3 hours)

---

## Step 1: Chat Component Integration (Start Here)

**File**: `frontend/src/components/Chat.tsx`

### What Needs to Happen

When the backend returns a payment command response, we need to:
1. Detect that it's a payment response
2. Show the UnifiedConfirmation component
3. Let user sign with their wallet
4. Submit the signature

### Code Template

```typescript
// In Chat.tsx, around line 200-250 where responses are rendered

// Add this to your response rendering logic:

interface PaymentResponse {
  type: "payment";
  details: {
    recipient?: string;
    amount?: number | string;
    token?: string;
    network?: string;
  };
  status?: "pending" | "signed" | "submitted" | "confirmed";
  txHash?: string;
}

// Inside your message rendering loop:
if (response.type === "payment") {
  return (
    <Box key={message.id} my={4}>
      <UnifiedConfirmation
        agentType="payment"
        content={{
          message: response.message || "Confirm payment",
          type: "payment",
          details: response.details
        }}
        onExecute={() => handlePaymentExecution(response)}
        onCancel={() => {
          // Clear confirmation, return to chat
          setConfirmingPayment(null);
        }}
        isLoading={isExecuting}
      />
    </Box>
  );
}
```

### Helper Functions to Add

```typescript
// Add to Chat.tsx

const [isExecuting, setIsExecuting] = useState(false);

async function handlePaymentExecution(response: PaymentResponse) {
  if (!address) {
    toast({
      title: "Wallet not connected",
      description: "Please connect your wallet first",
      status: "error",
    });
    return;
  }

  try {
    setIsExecuting(true);
    
    // Step 1: Prepare payment (get EIP-712 payload)
    const prepareResponse = await fetch(
      `${process.env.NEXT_PUBLIC_API_URL}/api/v1/x402/prepare-payment`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          user_address: address,
          recipient_address: response.details.recipient,
          amount_usdc: response.details.amount,
          network: response.details.network || "cronos-testnet"
        })
      }
    );
    
    if (!prepareResponse.ok) {
      throw new Error("Failed to prepare payment");
    }
    
    const payload = await prepareResponse.json();
    
    // Step 2: Sign with Wagmi
    const signature = await signTypedData({
      domain: payload.domain,
      types: payload.types,
      primaryType: payload.primaryType,
      message: payload.message,
      account: address
    });
    
    // Step 3: Submit signed payment
    const submitResponse = await fetch(
      `${process.env.NEXT_PUBLIC_API_URL}/api/v1/x402/submit-payment`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          signature,
          user_address: address,
          message: payload.message,
          metadata: payload.metadata
        })
      }
    );
    
    if (!submitResponse.ok) {
      throw new Error("Failed to submit payment");
    }
    
    const result = await submitResponse.json();
    
    // Step 4: Show success
    toast({
      title: "Payment Successful",
      description: `Transaction: ${result.txHash}`,
      status: "success",
    });
    
    // Add to chat history
    setMessages(prev => [...prev, {
      id: Date.now().toString(),
      type: "system",
      content: `✅ Payment confirmed. TX: ${result.txHash}`,
      timestamp: new Date()
    }]);
    
  } catch (error) {
    toast({
      title: "Payment Failed",
      description: error instanceof Error ? error.message : "Unknown error",
      status: "error",
    });
  } finally {
    setIsExecuting(false);
  }
}
```

---

## Step 2: UnifiedConfirmation Enhancement

**File**: `frontend/src/components/UnifiedConfirmation.tsx`

### What's Already There
The component already has a "payment" agentType case. We just need to make sure it displays well.

### Check These Lines

```typescript
// Line ~82-98: The getTitle() function already handles "payment"
// Line ~150+: The details rendering - make sure it shows:
//   - Recipient address (shortened or ENS name)
//   - Amount + symbol (USDC or MNEE)
//   - Network name
//   - Fee (if available)

// Add payment-specific display:
{agentType === "payment" && (
  <VStack spacing={3} align="start" width="100%">
    <HStack justify="space-between" width="100%">
      <Text fontWeight="600">Recipient:</Text>
      <Text fontFamily="monospace">{content.details?.recipient?.slice(0, 10)}...{content.details?.recipient?.slice(-8)}</Text>
    </HStack>
    
    <HStack justify="space-between" width="100%">
      <Text fontWeight="600">Amount:</Text>
      <Text>{content.details?.amount} {content.details?.token || "USDC"}</Text>
    </HStack>
    
    <HStack justify="space-between" width="100%">
      <Text fontWeight="600">Network:</Text>
      <Badge colorScheme="blue">{content.details?.network}</Badge>
    </HStack>
  </VStack>
)}
```

---

## Step 3: Import Required Dependencies

**File**: `frontend/src/components/Chat.tsx`

Add these imports at the top:

```typescript
import { useSignTypedData } from "wagmi";  // For EIP-712 signing
import { UnifiedConfirmation } from "./UnifiedConfirmation";
```

---

## Step 4: Test Locally

### Setup
1. Start backend: `cd backend && ./start.sh`
2. Start frontend: `cd frontend && npm run dev`
3. Open http://localhost:3000

### Test Flow

```
1. Connect wallet (use MetaMask or WalletConnect)
2. Switch to Cronos Testnet (Chain ID: 338)
3. Type: "pay 1 USDC to 0x1234567890123456789012345678901234567890 on cronos"
4. Backend parses as X402_PAYMENT
5. Frontend shows confirmation dialog
6. Click "Confirm" 
7. Sign with wallet (Wagmi shows signature request)
8. Submit signed payment
9. See result: Success or error
```

### Expected Success Flow

```
User Command:
  "pay 1 USDC to 0xabc...123"
        ↓
Backend Response:
  {
    "agentType": "payment",
    "content": {
      "type": "payment",
      "message": "Ready to pay 1 USDC to 0xabc...123",
      "details": {
        "recipient": "0xabc...123",
        "amount": 1,
        "token": "USDC",
        "network": "cronos-testnet"
      }
    }
  }
        ↓
Frontend Shows:
  UnifiedConfirmation with payment details
        ↓
User Clicks "Confirm":
  1. Frontend calls /api/v1/x402/prepare-payment
  2. Backend returns EIP-712 payload
  3. Wagmi shows signature request
  4. User signs
  5. Frontend calls /api/v1/x402/submit-payment
  6. Backend submits to facilitator
  7. Facilitator settles on-chain
  8. Frontend shows success: "✅ Payment confirmed. TX: 0x..."
```

---

## Step 5: Handle Edge Cases

### If Wallet Not Connected
```typescript
if (!address) {
  // Show message in chat
  addMessage("Please connect your wallet to execute payments");
  return;
}
```

### If Wrong Network
```typescript
const currentChainId = useChainId();
if (currentChainId !== 338) {  // Cronos Testnet
  // Show message
  addMessage("Please switch to Cronos Testnet (Chain ID: 338)");
  return;
}
```

### If Insufficient Balance
```typescript
// Check balance before showing confirmation
const balance = await readContract({
  address: USDC_TESTNET,
  abi: ERC20_ABI,
  functionName: "balanceOf",
  args: [address]
});

if (balance < requestedAmount) {
  addMessage(`Insufficient balance. You have ${balance} USDC, need ${requestedAmount}`);
  return;
}
```

---

## Files to Edit (Summary)

| File | Changes | Time |
|------|---------|------|
| `frontend/src/components/Chat.tsx` | Add payment handler + helper functions | 1-2h |
| `frontend/src/components/UnifiedConfirmation.tsx` | Enhance payment display | 30min |
| `frontend/src/services/x402Service.ts` | Already ready, just verify imports | 15min |

**Total**: ~2.5-3 hours

---

## Verification Checklist

Before moving to Phase 3:

- [ ] Chat component detects payment responses
- [ ] UnifiedConfirmation shows with payment details
- [ ] Wallet connection check works
- [ ] EIP-712 signing request appears
- [ ] Backend receives signed payment
- [ ] Facilitator processes payment
- [ ] Success message displayed with tx hash
- [ ] Error messages are clear and helpful

---

## Debugging Tips

### If Signing Fails
- Check: Is Wagmi initialized?
- Check: Is wallet connected?
- Check: Is user on correct chain?
- Check: Does user have testnet tokens?

### If Submission Fails
- Check: Is signature valid?
- Check: Did backend receive correct format?
- Check: Are amounts in correct decimal places?

### If Facilitator Doesn't Respond
- Run: `python backend/scripts/test_x402_facilitator.py`
- Should show all endpoints responding with 200/400 (not 500)

---

## What NOT To Do (PREVENTION FIRST)

❌ Don't create new payment components  
✅ Do: Enhance existing UnifiedConfirmation

❌ Don't duplicate payment logic  
✅ Do: Consolidate in unifiedPaymentService

❌ Don't hardcode addresses or networks  
✅ Do: Use config from constants

---

## Next Phase

Once this is working (testnet transaction confirmed on-chain):

1. Record demo video (2 min)
2. Clean up console logs and debug code
3. Submit to DoraHacks

---

**Ready to Start?** Open `frontend/src/components/Chat.tsx` and begin!

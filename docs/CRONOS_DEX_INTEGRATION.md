# Cronos DEX Integration

## Overview

SNEL now provides intelligent DEX routing on Cronos with specialized protocol adapters for optimal trading and X402 payment support.

## Smart Routing Logic

### MM Finance (USDC Specialist)
- **Use Case**: CRO ↔ USDC swaps
- **Volume Share**: 60% of WCRO/USDC trading
- **Router**: `0x145677FC4d9b8F19B5D56d1820c48e0443049a30`
- **Factory**: `0xd590cC180601AEcD6eeADD9B7f2B7611519544f4`
- **Specialization**: Optimized for X402 payment flows

### VVS Finance (General DEX)
- **Use Case**: All other token pairs (CRO ↔ USDT, etc.)
- **Volume Share**: 64.6% overall trading volume
- **Router**: `0x145863Eb42Cf62847A6Ca784e6416C1682b1b2Ae`
- **Factory**: `0x3B44B2a187a7b3824131F8db5a74194D0a42Fc15`
- **Specialization**: Broad market coverage

## Token Addresses (Official Cronos)

```javascript
// Official Cronos token addresses
USDC: "0xc21223249CA28397B4B6541dfFaEcC539BfF0c59"
WCRO: "0x5C7F8A570d578ED84E63fdFA7b1eE72dEae1AE23"
USDT: "0x66e428c3f67a68878562e79A0234c1F83c208770"
```

## Implementation Files

```
backend/app/protocols/
├── mm_adapter.py          # MM Finance integration
├── vvs_adapter.py         # VVS Finance integration
└── registry.py            # Smart routing logic

backend/app/config/
├── chains.py              # Cronos chain configuration
├── protocols.py           # Protocol contract addresses
└── tokens.py              # Token registry with official addresses

backend/app/services/
└── swap_service.py        # Unified swap service with routing
```

## Usage Examples

### Automatic Routing
```bash
# Routes to MM Finance (USDC specialist)
swap 10 CRO to USDC

# Routes to VVS Finance (general DEX)
swap 10 CRO to USDT

# X402 payment with USDC support
pay 50 USDC to recipient.eth
```

### API Integration
```python
# Smart routing in action
quote = await swap_service.get_quote(
    from_token_id="CRO",
    to_token_id="USDC", 
    amount=Decimal("10"),
    chain_id=25,  # Cronos
    wallet_address=user_address
)
# Automatically uses MM Finance for USDC pairs
```

## Test Results

```
✅ CRO → USDC: MM Finance (1 CRO = 0.091748 USDC)
✅ USDC → CRO: MM Finance (1 USDC = 10.862046 CRO)  
✅ CRO → USDT: VVS Finance (1 CRO = 0.091540 USDT)
```

## Benefits

1. **X402 Integration**: USDC swaps now work, enabling full X402 payment support
2. **Optimal Routing**: Each token pair uses the DEX with best liquidity
3. **Fallback Support**: Automatic fallback between protocols
4. **User Experience**: Transparent routing - users don't need to choose DEX
5. **Cost Efficiency**: Routes to DEX with best rates for each pair

## Status

✅ **PRODUCTION READY** - Fully integrated and tested with real Cronos contracts
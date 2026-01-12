"""
X402 Agentic Payment API Endpoints

Real x402 payment execution endpoints for Cronos EVM.
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
import logging

from app.protocols.x402_adapter import X402Adapter, execute_ai_payment, check_x402_service_health
from app.config.chains import is_x402_privacy_supported

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/x402", tags=["x402"])

class X402PaymentRequest(BaseModel):
    """Request model for x402 payment execution."""
    private_key: str = Field(..., description="Private key for signing (in production, use wallet integration)")
    recipient_address: str = Field(..., description="Recipient wallet address")
    amount_usdc: float = Field(..., gt=0, description="Amount in USDC (e.g., 10.5)")
    network: str = Field(default="cronos-testnet", description="Network: cronos-mainnet or cronos-testnet")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Optional payment metadata")

# --- Decentralized Flow Models ---

class PreparePaymentRequest(BaseModel):
    """Request to prepare a payment for client-side signing."""
    recipient_address: str = Field(..., description="Recipient wallet address")
    user_address: str = Field(..., description="User wallet address (sender)")
    amount_usdc: float = Field(..., gt=0, description="Amount in USDC")
    network: str = Field(default="cronos-testnet", description="Network: cronos-mainnet or cronos-testnet")

class PreparePaymentResponse(BaseModel):
    """EIP-712 Typed Data for signing."""
    domain: Dict[str, Any]
    types: Dict[str, Any]
    primaryType: str
    message: Dict[str, Any]
    metadata: Dict[str, Any] # State to pass back to submit

class SubmitPaymentRequest(BaseModel):
    """Request to submit a signed payment."""
    signature: str = Field(..., description="Hex signature from wallet")
    user_address: str = Field(..., description="User wallet address")
    message: Dict[str, Any] = Field(..., description="Original message that was signed")
    metadata: Dict[str, Any] = Field(..., description="Metadata from prepare step")

# --------------------------------

class X402PaymentResponse(BaseModel):
    """Response model for x402 payment execution."""
    success: bool
    txHash: Optional[str] = None
    blockNumber: Optional[int] = None
    timestamp: Optional[str] = None
    error: Optional[str] = None
    from_address: Optional[str] = None
    to_address: Optional[str] = None
    value: Optional[str] = None
    network: str
    facilitator_url: str

class X402HealthResponse(BaseModel):
    """Response model for x402 service health check."""
    healthy: bool
    network: str
    facilitator_url: str
    supported_schemes: list = []

@router.post("/prepare-payment", response_model=PreparePaymentResponse)
async def prepare_x402_payment(request: PreparePaymentRequest):
    """
    Step 1 (Decentralized): Prepare EIP-712 payload for client-side signing.
    Does NOT require private key.
    """
    try:
        if request.network not in ["cronos-mainnet", "cronos-testnet"]:
            raise HTTPException(status_code=400, detail="Invalid network")
            
        adapter = X402Adapter(request.network)
        
        # Create requirements
        from app.protocols.x402_adapter import X402PaymentRequirements, USDC_CONTRACTS
        payment_requirements = X402PaymentRequirements(
            scheme="exact",
            network=request.network,
            payTo=request.recipient_address,
            asset=USDC_CONTRACTS[request.network],
            maxAmountRequired=str(int(request.amount_usdc * 1_000_000)),
            maxTimeoutSeconds=300
        )
        
        # Generate payload
        payload = await adapter.create_unsigned_payment_payload(
            payment_requirements=payment_requirements,
            amount_usdc=request.amount_usdc
        )
        
        # Inject sender into message
        payload["message"]["from"] = request.user_address
        
        return PreparePaymentResponse(
            domain=payload["domain"],
            types=payload["types"],
            primaryType=payload["primaryType"],
            message=payload["message"],
            metadata=payload["metadata"]
        )
        
    except Exception as e:
        logger.error(f"Failed to prepare payment: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/submit-payment", response_model=X402PaymentResponse)
async def submit_x402_payment(request: SubmitPaymentRequest):
    """
    Step 2 (Decentralized): Submit signed payment header to facilitator.
    """
    try:
        adapter = X402Adapter(request.metadata["network"])
        
        # Construct header
        header_base64 = adapter.construct_payment_header_from_signature(
            signature=request.signature,
            user_address=request.user_address,
            metadata=request.metadata,
            message=request.message
        )
        
        # Reconstruct requirements for settlement
        from app.protocols.x402_adapter import X402PaymentRequirements
        payment_requirements = X402PaymentRequirements(
            scheme=request.metadata["scheme"],
            network=request.metadata["network"],
            payTo=request.message["to"],
            asset=request.metadata["asset"],
            maxAmountRequired=request.metadata["amount_atomic"],
            maxTimeoutSeconds=300 # This comes from metadata implicitly via logic, or we can pass it
        )
        
        # Settle
        result = await adapter.settle_payment(header_base64, payment_requirements)
        
        return X402PaymentResponse(
            success=result.success,
            txHash=result.txHash,
            blockNumber=result.blockNumber,
            timestamp=result.timestamp,
            error=result.error,
            from_address=result.from_address,
            to_address=result.to_address,
            value=result.value,
            network=request.metadata["network"],
            facilitator_url=adapter.facilitator_url
        )

    except Exception as e:
        logger.error(f"Failed to submit payment: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health/{network}", response_model=X402HealthResponse)
async def check_x402_health(network: str = "cronos-testnet"):
    """Check x402 facilitator service health."""
    try:
        if network not in ["cronos-mainnet", "cronos-testnet", "ethereum-mainnet"]:
            raise HTTPException(status_code=400, detail="Invalid network. Use cronos-mainnet, cronos-testnet, or ethereum-mainnet")
        
        adapter = X402Adapter(network)
        
        try:
            # Check health and get supported schemes
            is_healthy = await adapter.check_facilitator_health()
            supported_schemes = await adapter.get_supported_schemes() if is_healthy else []
            
            return X402HealthResponse(
                healthy=is_healthy,
                network=network,
                facilitator_url=adapter.facilitator_url,
                supported_schemes=supported_schemes
            )
        finally:
            await adapter.close()
            
    except Exception as e:
        logger.error(f"X402 health check failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/execute-payment", response_model=X402PaymentResponse)
async def execute_x402_payment(request: X402PaymentRequest):
    """Execute a real x402 agentic payment on Cronos or Ethereum."""
    try:
        # Validate network
        if request.network not in ["cronos-mainnet", "cronos-testnet", "ethereum-mainnet"]:
            raise HTTPException(status_code=400, detail="Invalid network. Use cronos-mainnet, cronos-testnet, or ethereum-mainnet")
        
        # Validate recipient address format
        if not request.recipient_address.startswith("0x") or len(request.recipient_address) != 42:
            raise HTTPException(status_code=400, detail="Invalid recipient address format")
        
        # Validate amount
        if request.amount_usdc <= 0 or request.amount_usdc > 10000:  # Max $10k per transaction
            raise HTTPException(status_code=400, detail="Amount must be between 0 and 10,000 USDC")
        
        # Execute payment using x402 adapter
        adapter = X402Adapter(request.network)
        
        try:
            result = await adapter.execute_agentic_payment(
                private_key=request.private_key,
                recipient_address=request.recipient_address,
                amount_usdc=request.amount_usdc,
                metadata=request.metadata
            )
            
            return X402PaymentResponse(
                success=result.success,
                txHash=result.txHash,
                blockNumber=result.blockNumber,
                timestamp=result.timestamp,
                error=result.error,
                from_address=result.from_address,
                to_address=result.to_address,
                value=result.value,
                network=request.network,
                facilitator_url=adapter.facilitator_url
            )
            
        finally:
            await adapter.close()
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"X402 payment execution failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/verify-payment")
async def verify_x402_payment(
    payment_header: str,
    recipient_address: str,
    amount_usdc: float,
    network: str = "cronos-testnet"
):
    """Verify an x402 payment header without executing."""
    try:
        if network not in ["cronos-mainnet", "cronos-testnet", "ethereum-mainnet"]:
            raise HTTPException(status_code=400, detail="Invalid network")
        
        adapter = X402Adapter(network)
        
        try:
            # Create payment requirements for verification
            from app.protocols.x402_adapter import X402PaymentRequirements, USDC_CONTRACTS
            
            payment_requirements = X402PaymentRequirements(
                scheme="exact",
                network=network,
                payTo=recipient_address,
                asset=USDC_CONTRACTS[network],
                maxAmountRequired=str(int(amount_usdc * 1_000_000)),
                maxTimeoutSeconds=300
            )
            
            # Verify payment
            verification = await adapter.verify_payment(payment_header, payment_requirements)
            
            return {
                "isValid": verification.get("isValid", False),
                "invalidReason": verification.get("invalidReason"),
                "network": network,
                "facilitator_url": adapter.facilitator_url
            }
            
        finally:
            await adapter.close()
            
    except Exception as e:
        logger.error(f"X402 payment verification failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/supported-networks")
async def get_supported_networks():
    """Get networks that support x402 payments."""
    return {
        "networks": [
            {
                "name": "Cronos Mainnet",
                "network_id": "cronos-mainnet",
                "chain_id": 25,
                "stablecoin_contract": "0xf951eC28187D9E5Ca673Da8FE6757E6f0Be5F77C",
                "stablecoin_symbol": "USDC",
                "facilitator_url": "https://facilitator.cronoslabs.org/v2/x402"
            },
            {
                "name": "Cronos Testnet",
                "network_id": "cronos-testnet", 
                "chain_id": 338,
                "stablecoin_contract": "0xc01efAaF7C5C61bEbFAeb358E1161b537b8bC0e0",
                "stablecoin_symbol": "USDC",
                "facilitator_url": "https://facilitator.cronoslabs.org/v2/x402"
            },
            {
                "name": "Ethereum Mainnet",
                "network_id": "ethereum-mainnet",
                "chain_id": 1,
                "stablecoin_contract": "0x7D89c67d3c4E72E8C5c64BE201dC225F99d16aCa",
                "stablecoin_symbol": "MNEE",
                "facilitator_url": "https://facilitator.cronoslabs.org/v2/x402"
            }
        ]
    }
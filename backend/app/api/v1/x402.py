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

@router.get("/health/{network}", response_model=X402HealthResponse)
async def check_x402_health(network: str = "cronos-testnet"):
    """Check x402 facilitator service health."""
    try:
        if network not in ["cronos-mainnet", "cronos-testnet"]:
            raise HTTPException(status_code=400, detail="Invalid network. Use cronos-mainnet or cronos-testnet")
        
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
    """Execute a real x402 agentic payment on Cronos."""
    try:
        # Validate network
        if request.network not in ["cronos-mainnet", "cronos-testnet"]:
            raise HTTPException(status_code=400, detail="Invalid network. Use cronos-mainnet or cronos-testnet")
        
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
        if network not in ["cronos-mainnet", "cronos-testnet"]:
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
                "usdc_contract": "0xf951eC28187D9E5Ca673Da8FE6757E6f0Be5F77C",
                "facilitator_url": "https://facilitator.cronoslabs.org/v2/x402"
            },
            {
                "name": "Cronos Testnet",
                "network_id": "cronos-testnet", 
                "chain_id": 338,
                "usdc_contract": "0xc01efAaF7C5C61bEbFAeb358E1161b537b8bC0e0",
                "facilitator_url": "https://facilitator.cronoslabs.org/v2/x402"
            }
        ]
    }
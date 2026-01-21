"""
X402 Protocol Adapter for Real Agentic Payments

This adapter integrates with the x402 facilitator to enable:
- Real AI-triggered payments on Cronos EVM and Ethereum mainnet
- Automated settlement workflows with actual transactions
- Agent-to-agent transactions with EIP-712 signatures
- Programmable payment authorization via facilitator API
- Support for USDC on Cronos and MNEE stablecoin on Ethereum
"""

import json
import base64
import time
import secrets
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from eth_account import Account
from eth_account.messages import encode_typed_data
import httpx
import logging
import os
from app.config.chains import CHAINS, get_chain_id_by_name
from app.config.tokens import COMMON_TOKENS

logger = logging.getLogger(__name__)

# Default X402 Facilitator URL
DEFAULT_FACILITATOR_URL = os.getenv("X402_FACILITATOR_URL", "https://facilitator.cronoslabs.org/v2/x402")

@dataclass
class X402PaymentRequirements:
    """Payment requirements from x402 server."""
    scheme: str
    network: str
    payTo: str
    asset: str
    maxAmountRequired: str
    maxTimeoutSeconds: int

@dataclass
class X402PaymentResult:
    """Result of x402 payment execution."""
    success: bool
    txHash: Optional[str] = None
    blockNumber: Optional[int] = None
    timestamp: Optional[str] = None
    error: Optional[str] = None
    from_address: Optional[str] = None
    to_address: Optional[str] = None
    value: Optional[str] = None

class X402Adapter:
    """Real adapter for x402 agentic payment protocol on Cronos and Ethereum."""
    
    def __init__(self, network: str = "cronos-testnet"):
        """Initialize with network (cronos-mainnet, cronos-testnet, or ethereum-mainnet)."""
        chain_id = get_chain_id_by_name(network.split('-')[0] if '-' in network else network)
        if not chain_id and network == "cronos-testnet":
            chain_id = 338
        elif not chain_id and network == "cronos-mainnet":
            chain_id = 25
        elif not chain_id and network == "ethereum-mainnet":
            chain_id = 1
            
        if not chain_id or chain_id not in CHAINS:
             raise ValueError(f"Unsupported network: {network}")
             
        self.network = network
        self.chain_id = chain_id
        self.chain_info = CHAINS[chain_id]
        self.network_name = self.chain_info.name
        self.facilitator_url = DEFAULT_FACILITATOR_URL
        
        # Get stablecoin symbol for this network
        self.stablecoin_symbol = "MNEE" if chain_id == 1 else "USDC"
        
        # Get contract address from central token config
        token_data = COMMON_TOKENS.get(chain_id, {}).get(self.stablecoin_symbol.lower())
        if not token_data:
            raise ValueError(f"Stablecoin {self.stablecoin_symbol} not configured for chain {chain_id}")
            
        self.stablecoin_contract = token_data["address"]
        self.client = httpx.AsyncClient(timeout=30.0)
        
        # Keep backward compatibility
        self.usdc_contract = self.stablecoin_contract
        
        logger.info(f"X402Adapter initialized for {self.network_name} (chain {self.chain_id}) using {self.stablecoin_symbol}")
        
    async def check_facilitator_health(self) -> bool:
        """Check if the facilitator service is healthy."""
        try:
            response = await self.client.get(f"{self.facilitator_url.replace('/v2/x402', '')}/healthcheck")
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Facilitator health check failed: {e}")
            return False
    
    async def get_supported_schemes(self) -> List[Dict[str, Any]]:
        """Get supported payment schemes from facilitator."""
        try:
            response = await self.client.get(f"{self.facilitator_url}/supported")
            if response.status_code == 200:
                data = response.json()
                return data.get("kinds", [])
            return []
        except Exception as e:
            logger.error(f"Failed to get supported schemes: {e}")
            return []
    
    def generate_nonce(self) -> str:
        """Generate a random 32-byte nonce for EIP-3009 authorization."""
        return "0x" + secrets.token_hex(32)
    
    async def create_unsigned_payment_payload(
        self,
        payment_requirements: X402PaymentRequirements,
        amount_usdc: float
    ) -> Dict[str, Any]:
        """
        Create the unsigned EIP-712 payload for the frontend to sign.
        Returns the data needed for eth_signTypedData_v4.
        """
        try:
            # Convert USDC amount to atomic units (6 decimals)
            amount_atomic = int(amount_usdc * 1_000_000)
            
            # Generate unique nonce
            nonce = self.generate_nonce()
            
            # Calculate validity window (5 minutes)
            valid_after = 0  # Valid immediately
            valid_before = int(time.time()) + payment_requirements.maxTimeoutSeconds
            
            # Set up EIP-712 domain for USDC.e on Cronos
            domain = {
                "name": "Bridged USDC (Stargate)",
                "version": "1",
                "chainId": self.chain_id,
                "verifyingContract": payment_requirements.asset,
            }
            
            # Define EIP-712 typed data structure for EIP-3009
            types = {
                "EIP712Domain": [
                    {"name": "name", "type": "string"},
                    {"name": "version", "type": "string"},
                    {"name": "chainId", "type": "uint256"},
                    {"name": "verifyingContract", "type": "address"},
                ],
                "TransferWithAuthorization": [
                    {"name": "from", "type": "address"},
                    {"name": "to", "type": "address"},
                    {"name": "value", "type": "uint256"},
                    {"name": "validAfter", "type": "uint256"},
                    {"name": "validBefore", "type": "uint256"},
                    {"name": "nonce", "type": "bytes32"},
                ],
            }
            
            # Create the message
            # Note: 'from' must be filled by the frontend/user address
            message = {
                "to": payment_requirements.payTo,
                "value": amount_atomic,
                "validAfter": valid_after,
                "validBefore": valid_before,
                "nonce": nonce,
            }
            
            return {
                "domain": domain,
                "types": types,
                "primaryType": "TransferWithAuthorization",
                "message": message,
                # Metadata to reconstruct the header later
                "metadata": {
                    "scheme": payment_requirements.scheme,
                    "network": payment_requirements.network,
                    "asset": payment_requirements.asset,
                    "amount_atomic": str(amount_atomic)
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to create unsigned payload: {e}")
            raise

    async def create_payment_header(
        self,
        private_key: str,
        payment_requirements: X402PaymentRequirements,
        amount_usdc: float
    ) -> str:
        """Create a signed payment header for x402 payments."""
        try:
            # Create account from private key
            account = Account.from_key(private_key)
            
            # Convert USDC amount to atomic units (6 decimals)
            amount_atomic = int(amount_usdc * 1_000_000)
            
            # Generate unique nonce
            nonce = self.generate_nonce()
            
            # Calculate validity window (5 minutes)
            valid_after = 0  # Valid immediately
            valid_before = int(time.time()) + payment_requirements.maxTimeoutSeconds
            
            # Set up EIP-712 domain for USDC.e on Cronos
            domain = {
                "name": "Bridged USDC (Stargate)",
                "version": "1",
                "chainId": self.chain_id,
                "verifyingContract": payment_requirements.asset,
            }
            
            # Define EIP-712 typed data structure for EIP-3009
            types = {
                "TransferWithAuthorization": [
                    {"name": "from", "type": "address"},
                    {"name": "to", "type": "address"},
                    {"name": "value", "type": "uint256"},
                    {"name": "validAfter", "type": "uint256"},
                    {"name": "validBefore", "type": "uint256"},
                    {"name": "nonce", "type": "bytes32"},
                ],
            }
            
            # Create the message to sign
            message = {
                "from": account.address,
                "to": payment_requirements.payTo,
                "value": amount_atomic,
                "validAfter": valid_after,
                "validBefore": valid_before,
                "nonce": nonce,
            }
            
            # Sign using EIP-712
            structured_data = encode_typed_data({
                "domain": domain,
                "types": types,
                "message": message
            })
            signature = account.sign_message(structured_data).signature.hex()
            
            # Construct payment header
            payment_header = {
                "x402Version": 1,
                "scheme": payment_requirements.scheme,
                "network": payment_requirements.network,
                "payload": {
                    "from": account.address,
                    "to": payment_requirements.payTo,
                    "value": str(amount_atomic),
                    "validAfter": valid_after,
                    "validBefore": valid_before,
                    "nonce": nonce,
                    "signature": signature,
                    "asset": payment_requirements.asset,
                }
            }
            
            # Base64-encode
            header_json = json.dumps(payment_header)
            return base64.b64encode(header_json.encode()).decode()
            
        except Exception as e:
            logger.error(f"Failed to create payment header: {e}")
            raise

    def construct_payment_header_from_signature(
        self,
        signature: str,
        user_address: str,
        metadata: Dict[str, Any],
        message: Dict[str, Any]
    ) -> str:
        """Construct the final payment header using a provided signature."""
        try:
            payment_header = {
                "x402Version": 1,
                "scheme": metadata["scheme"],
                "network": metadata["network"],
                "payload": {
                    "from": user_address,
                    "to": message["to"],
                    "value": str(message["value"]),
                    "validAfter": message["validAfter"],
                    "validBefore": message["validBefore"],
                    "nonce": message["nonce"],
                    "signature": signature,
                    "asset": metadata["asset"],
                }
            }
            
            # Base64-encode
            header_json = json.dumps(payment_header)
            return base64.b64encode(header_json.encode()).decode()
            
        except Exception as e:
            logger.error(f"Failed to construct header from signature: {e}")
            raise
    
    async def verify_payment(
        self,
        payment_header: str,
        payment_requirements: X402PaymentRequirements
    ) -> Dict[str, Any]:
        """Verify payment header with facilitator before settlement."""
        try:
            payload = {
                "x402Version": 1,
                "paymentHeader": payment_header,
                "paymentRequirements": {
                    "scheme": payment_requirements.scheme,
                    "network": payment_requirements.network,
                    "payTo": payment_requirements.payTo,
                    "asset": payment_requirements.asset,
                    "maxAmountRequired": payment_requirements.maxAmountRequired,
                    "maxTimeoutSeconds": payment_requirements.maxTimeoutSeconds
                }
            }
            
            headers = {
                "Content-Type": "application/json",
                "X402-Version": "1"
            }
            
            response = await self.client.post(
                f"{self.facilitator_url}/verify",
                json=payload,
                headers=headers
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                return {
                    "isValid": False,
                    "invalidReason": f"Verification failed: {response.text}"
                }
                
        except Exception as e:
            logger.error(f"Payment verification failed: {e}")
            return {
                "isValid": False,
                "invalidReason": str(e)
            }
    
    async def settle_payment(
        self,
        payment_header: str,
        payment_requirements: X402PaymentRequirements
    ) -> X402PaymentResult:
        """Settle payment on-chain via facilitator."""
        try:
            payload = {
                "x402Version": 1,
                "paymentHeader": payment_header,
                "paymentRequirements": {
                    "scheme": payment_requirements.scheme,
                    "network": payment_requirements.network,
                    "payTo": payment_requirements.payTo,
                    "asset": payment_requirements.asset,
                    "maxAmountRequired": payment_requirements.maxAmountRequired,
                    "maxTimeoutSeconds": payment_requirements.maxTimeoutSeconds
                }
            }
            
            headers = {
                "Content-Type": "application/json",
                "X402-Version": "1"
            }
            
            response = await self.client.post(
                f"{self.facilitator_url}/settle",
                json=payload,
                headers=headers
            )
            
            if response.status_code == 200:
                data = response.json()
                return X402PaymentResult(
                    success=True,
                    txHash=data.get("txHash"),
                    blockNumber=data.get("blockNumber"),
                    timestamp=data.get("timestamp"),
                    from_address=data.get("from"),
                    to_address=data.get("to"),
                    value=data.get("value")
                )
            else:
                error_data = response.json() if response.headers.get("content-type", "").startswith("application/json") else {"error": response.text}
                return X402PaymentResult(
                    success=False,
                    error=error_data.get("error", f"Settlement failed with status {response.status_code}")
                )
                
        except Exception as e:
            logger.error(f"Payment settlement failed: {e}")
            return X402PaymentResult(
                success=False,
                error=str(e)
            )
    
    async def execute_agentic_payment(
        self,
        private_key: str,
        recipient_address: str,
        amount_usdc: float,
        metadata: Optional[Dict[str, Any]] = None
    ) -> X402PaymentResult:
        """Execute a complete AI-triggered payment using x402 protocol.
        
        Args:
            private_key: Private key for signing transactions
            recipient_address: Recipient wallet address
            amount_usdc: Amount in stablecoin (USDC for Cronos, MNEE for Ethereum)
            metadata: Optional payment metadata
        """
        try:
            logger.info(f"Executing x402 payment: {amount_usdc} {self.stablecoin_symbol} on {self.network_name}")
            
            # Create payment requirements
            payment_requirements = X402PaymentRequirements(
                scheme="exact",
                network=self.network,
                payTo=recipient_address,
                asset=self.stablecoin_contract,
                maxAmountRequired=str(int(amount_usdc * 1_000_000)),  # Convert to atomic units (6 decimals)
                maxTimeoutSeconds=300  # 5 minutes
            )
            
            # Create payment header
            payment_header = await self.create_payment_header(
                private_key, payment_requirements, amount_usdc
            )
            
            # Verify payment first
            verification = await self.verify_payment(payment_header, payment_requirements)
            if not verification.get("isValid", False):
                return X402PaymentResult(
                    success=False,
                    error=f"Payment verification failed: {verification.get('invalidReason', 'Unknown error')}"
                )
            
            # Settle payment on-chain
            result = await self.settle_payment(payment_header, payment_requirements)
            
            # Add metadata to result
            if metadata and result.success:
                logger.info(f"X402 payment executed with metadata: {metadata}")
            
            return result
                
        except Exception as e:
            logger.error(f"Agentic payment failed: {e}")
            return X402PaymentResult(
                success=False,
                error=str(e)
            )
    
    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()

# Convenience functions for common x402 operations
async def execute_ai_payment(
    private_key: str,
    recipient_address: str,
    amount_usdc: float,
    network: str = "cronos-testnet",
    metadata: Optional[Dict[str, Any]] = None
) -> X402PaymentResult:
    """Execute an AI-triggered payment on supported networks (Cronos or Ethereum).
    
    Args:
        private_key: Private key for signing
        recipient_address: Recipient address
        amount_usdc: Amount in stablecoin (USDC for Cronos, MNEE for Ethereum)
        network: Network name (cronos-mainnet, cronos-testnet, ethereum-mainnet)
        metadata: Optional payment metadata
    """
    adapter = X402Adapter(network)
    try:
        return await adapter.execute_agentic_payment(
            private_key, recipient_address, amount_usdc, metadata
        )
    finally:
        await adapter.close()

async def check_x402_service_health(network: str = "cronos-testnet") -> bool:
    """Check if x402 facilitator service is available."""
    adapter = X402Adapter(network)
    try:
        return await adapter.check_facilitator_health()
    finally:
        await adapter.close()
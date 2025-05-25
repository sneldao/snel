"""
Bridge command processing endpoint.
"""
import re
import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, Union
from decimal import Decimal

from app.services.brian.client import brian_client
from app.config.agent_config import AgentConfig

router = APIRouter(prefix="/bridge", tags=["bridge"])
logger = logging.getLogger(__name__)

class BridgeCommand(BaseModel):
    """Bridge command request model."""
    command: str = Field(description="Bridge command string")
    wallet_address: str = Field(description="User wallet address")
    chain_id: int = Field(description="Current chain ID")

class BridgeResponse(BaseModel):
    """Bridge command response model."""
    content: Union[str, Dict[str, Any]]
    agentType: str = "bridge"
    metadata: Optional[Dict[str, Any]] = Field(default=None)
    awaiting_confirmation: Optional[bool] = Field(default=False)
    status: str = "success"
    error: Optional[str] = Field(default=None)
    transaction: Optional[Dict[str, Any]] = Field(default=None)

def parse_bridge_command(command: str) -> Dict[str, Any]:
    """Parse a bridge command to extract parameters."""
    # Pattern: bridge 1 usdc to arbitrum
    # Pattern: bridge 0.5 eth from base to arbitrum

    # More flexible pattern to handle various formats
    pattern = r"bridge\s+([\d\.]+)\s+(\w+)(?:\s+from\s+(\w+))?\s+to\s+(\w+)"
    match = re.match(pattern, command.lower().strip())

    if not match:
        raise ValueError("Invalid bridge command format. Use: 'bridge [amount] [token] to [chain]' or 'bridge [amount] [token] from [chain] to [chain]'")

    amount = float(match.group(1))
    token = match.group(2).upper()
    from_chain = match.group(3)  # Optional
    to_chain = match.group(4).lower()

    return {
        "amount": amount,
        "token": token,
        "from_chain": from_chain,
        "to_chain": to_chain
    }

def get_chain_id_by_name(chain_name: str) -> Optional[int]:
    """Get chain ID by chain name."""
    chain_name_lower = chain_name.lower()

    # Map common chain names to IDs
    chain_mapping = {
        "ethereum": 1,
        "eth": 1,
        "mainnet": 1,
        "base": 8453,
        "arbitrum": 42161,
        "arb": 42161,
        "optimism": 10,
        "op": 10,
        "polygon": 137,
        "matic": 137,
        "avalanche": 43114,
        "avax": 43114,
        "bsc": 56,
        "binance": 56,
        "scroll": 534352,
        "zksync": 324,
        "linea": 59144,
        "mantle": 5000,
        "blast": 81457,
        "gnosis": 100
    }

    return chain_mapping.get(chain_name_lower)

@router.post("/process")
async def process_bridge_command(command: BridgeCommand) -> BridgeResponse:
    """Process a bridge command."""
    try:
        logger.info(f"Processing bridge command: {command.command}")
        logger.info(f"Wallet address: {command.wallet_address}")
        logger.info(f"Chain ID: {command.chain_id}")

        # Parse the command
        parsed = parse_bridge_command(command.command)

        # Get chain IDs
        from_chain_id = command.chain_id  # Current chain
        to_chain_id = get_chain_id_by_name(parsed["to_chain"])

        if not to_chain_id:
            return BridgeResponse(
                content={
                    "message": f"Unsupported destination chain: {parsed['to_chain']}",
                    "supported_chains": ["ethereum", "base", "arbitrum", "optimism", "polygon", "avalanche", "bsc"],
                    "type": "error"
                },
                status="error"
            )

        # Check if bridging is supported for these chains
        bridge_capability = AgentConfig.CAPABILITIES.get("cross_chain_bridging")
        if not bridge_capability:
            return BridgeResponse(
                content={
                    "message": "Bridge functionality is not available.",
                    "type": "error"
                },
                status="error"
            )

        if from_chain_id not in bridge_capability.supported_chains or to_chain_id not in bridge_capability.supported_chains:
            return BridgeResponse(
                content={
                    "message": f"Bridging not supported between these chains.",
                    "from_chain": AgentConfig.get_chain_name(from_chain_id),
                    "to_chain": AgentConfig.get_chain_name(to_chain_id),
                    "type": "error"
                },
                status="error"
            )

        # Use Brian API to get bridge transaction
        try:
            # Format prompt for Brian API
            from_chain_name = AgentConfig.get_chain_name(from_chain_id)
            to_chain_name = AgentConfig.get_chain_name(to_chain_id)

            prompt = f"bridge {parsed['amount']} {parsed['token']} from {from_chain_name} to {to_chain_name}"

            logger.info(f"Processing bridge: {prompt}")

            # Call Brian API for bridge transaction
            result = await brian_client.get_bridge_transaction(
                token=parsed['token'],
                amount=parsed['amount'],
                from_chain_id=from_chain_id,
                to_chain_id=to_chain_id,
                wallet_address=command.wallet_address
            )

            if result.get("error"):
                return BridgeResponse(
                    content={
                        "message": result.get("message", "Bridge transaction failed"),
                        "type": "error"
                    },
                    status="error",
                    metadata={"technical_details": result.get("technical_details")}
                )

            # Success - return transaction details with executable transaction data
            steps = result.get("steps", [])
            if not steps:
                return BridgeResponse(
                    content={
                        "message": "No transaction steps received from bridge service.",
                        "type": "error"
                    },
                    status="error"
                )

            # Get the first step for execution
            first_step = steps[0]

            # Format transaction data to match frontend expectations
            transaction_data = {
                "to": first_step.get("to"),
                "data": first_step.get("data"),
                "value": first_step.get("value"),
                "gasLimit": first_step.get("gasLimit"),
                "chainId": first_step.get("chainId"),
                "from": first_step.get("from"),
                "description": result.get("description", "Bridge transaction"),
                "steps": steps,  # Include all steps for multi-step transactions
                "solver": result.get("solver", ""),
                "protocol": result.get("protocol", {}),
                # Add additional fields that the frontend might expect
                "gas": first_step.get("gasLimit"),
                "blockNumber": first_step.get("blockNumber")
            }

            logger.info(f"Bridge transaction data prepared: {transaction_data}")

            return BridgeResponse(
                content={
                    "message": f"Ready to bridge {parsed['amount']} {parsed['token']} from {from_chain_name} to {to_chain_name}",
                    "amount": parsed['amount'],
                    "token": parsed['token'],
                    "from_chain": from_chain_name,
                    "to_chain": to_chain_name,
                    "estimated_time": "5-15 minutes",
                    "gas_cost_usd": result.get("gasCostUSD", ""),
                    "to_amount": result.get("toAmount", ""),
                    "protocol": result.get("protocol", {}).get("name", "Unknown"),
                    "type": "bridge_ready",
                    "requires_transaction": True
                },
                transaction=transaction_data,
                awaiting_confirmation=True,
                metadata={
                    "bridge_details": {
                        "from_chain_id": from_chain_id,
                        "to_chain_id": to_chain_id,
                        "amount": parsed['amount'],
                        "token": parsed['token'],
                        "transaction_ready": True
                    }
                }
            )

        except Exception as e:
            logger.exception("Error calling Brian API for bridge")
            return BridgeResponse(
                content={
                    "message": "Unable to prepare bridge transaction at the moment.",
                    "suggestion": "Please try again in a few moments or try a different amount.",
                    "type": "error"
                },
                status="error",
                metadata={"technical_details": str(e)}
            )

    except ValueError as e:
        return BridgeResponse(
            content={
                "message": str(e),
                "examples": [
                    "bridge 1 usdc to arbitrum",
                    "bridge 0.5 eth from base to optimism",
                    "bridge 100 usdt to polygon"
                ],
                "type": "error"
            },
            status="error"
        )
    except Exception as e:
        logger.exception("Error processing bridge command")
        return BridgeResponse(
            content={
                "message": "An unexpected error occurred while processing your bridge request.",
                "type": "error"
            },
            status="error",
            metadata={"technical_details": str(e)}
        )

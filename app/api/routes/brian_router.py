"""
Router for Brian API features.
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from typing import Dict, Any, List, Optional, Union
import logging
import re

from app.services.brian_service import brian_service
from app.services.token_service import TokenService
from app.services.redis_service import RedisService, get_redis_service
from app.models.commands import TransferCommand, BridgeCommand, BalanceCommand
from app.models.transaction import TransactionResponse

router = APIRouter(tags=["brian"])
logger = logging.getLogger(__name__)

# Request models
class TransferRequest(BaseModel):
    """Request to transfer tokens."""
    command: str
    wallet_address: str
    chain_id: int = 1

class BridgeRequest(BaseModel):
    """Request to bridge tokens across chains."""
    command: str
    wallet_address: str
    from_chain_id: int = 1
    to_chain_id: int = 8453  # Default to Base

class BalanceRequest(BaseModel):
    """Request to check token balances."""
    wallet_address: str
    chain_id: int = 1
    token_symbol: Optional[str] = None

# Helper functions
def parse_transfer_command(command: str) -> TransferCommand:
    """
    Parse a transfer command from natural language.
    
    Examples:
    - "send 10 USDC to 0x123..."
    - "transfer 5 ETH to papajams.eth"
    """
    # Basic regex pattern to extract amount, token, and recipient
    pattern = r"(?:send|transfer)\s+(\d+(?:\.\d+)?)\s+([A-Za-z0-9]+)\s+(?:to)\s+([A-Za-z0-9\.]+(?:\.[A-Za-z0-9]+)*)"
    match = re.search(pattern, command, re.IGNORECASE)
    
    if not match:
        raise ValueError("Invalid transfer command format. Expected: 'send/transfer [amount] [token] to [recipient]'")
    
    amount = float(match.group(1))
    token = match.group(2).upper()
    recipient = match.group(3)
    
    return TransferCommand(
        action="transfer",
        amount=amount,
        token=token,
        recipient=recipient,
        natural_command=command
    )

def parse_bridge_command(command: str) -> BridgeCommand:
    """
    Parse a bridge command from natural language.
    
    Examples:
    - "bridge 0.1 ETH from Scroll to Base"
    - "bridge 50 USDC from scroll to arbitrum"
    """
    # Basic regex pattern to extract amount, token, source chain, and destination chain
    pattern = r"bridge\s+(\d+(?:\.\d+)?)\s+([A-Za-z0-9]+)\s+(?:from)\s+([A-Za-z0-9]+)\s+(?:to)\s+([A-Za-z0-9]+)"
    match = re.search(pattern, command, re.IGNORECASE)
    
    if not match:
        raise ValueError("Invalid bridge command format. Expected: 'bridge [amount] [token] from [source chain] to [destination chain]'")
    
    amount = float(match.group(1))
    token = match.group(2).upper()
    from_chain = match.group(3).lower()
    to_chain = match.group(4).lower()
    
    # Map chain names to chain IDs
    chain_map = {
        "ethereum": 1,
        "eth": 1,
        "optimism": 10,
        "op": 10,
        "bsc": 56,
        "binance": 56,
        "polygon": 137,
        "matic": 137,
        "arbitrum": 42161,
        "arb": 42161,
        "base": 8453,
        "scroll": 534352,
        "avalanche": 43114,
        "avax": 43114
    }
    
    from_chain_id = chain_map.get(from_chain, 1)  # Default to Ethereum if not found
    to_chain_id = chain_map.get(to_chain, 8453)  # Default to Base if not found
    
    return BridgeCommand(
        action="bridge",
        amount=amount,
        token=token,
        from_chain_id=from_chain_id,
        to_chain_id=to_chain_id,
        natural_command=command
    )

def parse_balance_command(command: str) -> BalanceCommand:
    """
    Parse a balance command from natural language.
    
    Examples:
    - "check my USDC balance on Scroll"
    - "what's my ETH balance"
    - "show my balance"
    """
    # Check for specific token
    token_pattern = r"(?:check|show|what'?s|get)\s+(?:my|the)\s+([A-Za-z0-9]+)\s+balance"
    token_match = re.search(token_pattern, command, re.IGNORECASE)
    
    token = None
    if token_match:
        token = token_match.group(1).upper()
    
    # Check for specific chain
    chain_pattern = r"on\s+([A-Za-z0-9]+)"
    chain_match = re.search(chain_pattern, command, re.IGNORECASE)
    
    chain_id = None
    if chain_match:
        chain_name = chain_match.group(1).lower()
        # Map chain names to chain IDs
        chain_map = {
            "ethereum": 1,
            "eth": 1,
            "optimism": 10,
            "op": 10,
            "bsc": 56,
            "binance": 56,
            "polygon": 137,
            "matic": 137,
            "arbitrum": 42161,
            "arb": 42161,
            "base": 8453,
            "scroll": 534352,
            "avalanche": 43114,
            "avax": 43114
        }
        chain_id = chain_map.get(chain_name)
    
    return BalanceCommand(
        action="balance",
        token=token,
        chain_id=chain_id,
        natural_command=command
    )

# API endpoints
@router.post("/transfer", response_model=TransactionResponse)
async def process_transfer(
    request: TransferRequest,
    redis_service: RedisService = Depends(get_redis_service)
) -> Dict[str, Any]:
    """
    Process a token transfer command.
    """
    try:
        # Parse the transfer command
        transfer_command = parse_transfer_command(request.command)
        
        # Get the token symbol
        token_symbol = transfer_command.token
        if isinstance(token_symbol, dict):
            token_symbol = token_symbol.get("symbol", "")
        
        # Get the transaction data from Brian API
        tx_data = await brian_service.get_transfer_transaction(
            token_symbol=token_symbol,
            amount=transfer_command.amount,
            recipient_address=transfer_command.recipient,
            wallet_address=request.wallet_address,
            chain_id=request.chain_id
        )
        
        # Store the pending command
        await redis_service.store_pending_command(
            wallet_address=request.wallet_address,
            command=request.command
        )
        
        # Return the transaction data
        return TransactionResponse(
            to=tx_data["to"],
            data=tx_data["data"],
            value=tx_data["value"],
            chain_id=request.chain_id,
            method="transfer",
            gas_limit=tx_data["gas"],
            pending_command=request.command,
            metadata=tx_data["metadata"],
            agent_type="transfer"
        )
    except ValueError as e:
        logger.error(f"Error processing transfer command: {str(e)}")
        return TransactionResponse(
            error=str(e),
            status="error"
        )
    except Exception as e:
        logger.error(f"Unexpected error processing transfer command: {str(e)}")
        return TransactionResponse(
            error=f"Unexpected error: {str(e)}",
            status="error"
        )

@router.post("/bridge", response_model=TransactionResponse)
async def process_bridge(
    request: BridgeRequest,
    redis_service: RedisService = Depends(get_redis_service)
) -> Dict[str, Any]:
    """
    Process a token bridge command.
    """
    try:
        # Parse the bridge command
        bridge_command = parse_bridge_command(request.command)
        
        # Get the token symbol
        token_symbol = bridge_command.token
        if isinstance(token_symbol, dict):
            token_symbol = token_symbol.get("symbol", "")
        
        # Get the transaction data from Brian API
        tx_data = await brian_service.get_bridge_transaction(
            token_symbol=token_symbol,
            amount=bridge_command.amount,
            from_chain_id=bridge_command.from_chain_id,
            to_chain_id=bridge_command.to_chain_id,
            wallet_address=request.wallet_address
        )
        
        # Store the pending command
        await redis_service.store_pending_command(
            wallet_address=request.wallet_address,
            command=request.command
        )
        
        # Check if we have quotes
        if "all_quotes" in tx_data and tx_data["all_quotes"]:
            # Get the first non-approval quote
            main_quote = next((q for q in tx_data["all_quotes"] if not q.get("is_approval")), tx_data["all_quotes"][0])
            
            # Return the transaction data
            return TransactionResponse(
                to=main_quote["to"],
                data=main_quote["data"],
                value=main_quote["value"],
                chain_id=bridge_command.from_chain_id,
                method="bridge",
                gas_limit=main_quote["gas"],
                needs_approval=tx_data.get("needs_approval", False),
                token_to_approve=tx_data.get("token_to_approve"),
                spender=tx_data.get("spender"),
                pending_command=request.command,
                metadata=tx_data["metadata"],
                agent_type="bridge"
            )
        else:
            raise ValueError("No valid bridge quotes found")
    except ValueError as e:
        logger.error(f"Error processing bridge command: {str(e)}")
        return TransactionResponse(
            error=str(e),
            status="error"
        )
    except Exception as e:
        logger.error(f"Unexpected error processing bridge command: {str(e)}")
        return TransactionResponse(
            error=f"Unexpected error: {str(e)}",
            status="error"
        )

@router.post("/balance", response_model=Dict[str, Any])
async def check_balance(
    request: BalanceRequest
) -> Dict[str, Any]:
    """
    Check token balances.
    """
    try:
        # Get the balance information from Brian API
        balance_data = await brian_service.get_token_balances(
            wallet_address=request.wallet_address,
            chain_id=request.chain_id,
            token_symbol=request.token_symbol
        )
        
        # Return the balance information
        return {
            "content": balance_data["answer"],
            "wallet_address": request.wallet_address,
            "chain_id": request.chain_id,
            "token_symbol": request.token_symbol,
            "chain_name": balance_data["chain_name"],
            "status": "success"
        }
    except ValueError as e:
        logger.error(f"Error checking balance: {str(e)}")
        return {
            "error": str(e),
            "status": "error"
        }
    except Exception as e:
        logger.error(f"Unexpected error checking balance: {str(e)}")
        return {
            "error": f"Unexpected error: {str(e)}",
            "status": "error"
        }

@router.post("/process-command", response_model=Dict[str, Any])
async def process_brian_command(
    command: Dict[str, Any],
    redis_service: RedisService = Depends(get_redis_service)
) -> Dict[str, Any]:
    """
    Process a command using the Brian API.
    """
    try:
        content = command.get("content", "")
        wallet_address = command.get("wallet_address", "")
        chain_id = command.get("chain_id", 1)
        
        # Check if this is a transfer command
        if re.search(r"(?:send|transfer)\s+\d+(?:\.\d+)?\s+[A-Za-z0-9]+\s+(?:to)\s+[A-Za-z0-9\.]+", content, re.IGNORECASE):
            # Process as a transfer
            transfer_request = TransferRequest(
                command=content,
                wallet_address=wallet_address,
                chain_id=chain_id
            )
            return await process_transfer(transfer_request, redis_service)
        
        # Check if this is a bridge command
        elif re.search(r"bridge\s+\d+(?:\.\d+)?\s+[A-Za-z0-9]+\s+(?:from)\s+[A-Za-z0-9]+\s+(?:to)\s+[A-Za-z0-9]+", content, re.IGNORECASE):
            # Process as a bridge
            bridge_request = BridgeRequest(
                command=content,
                wallet_address=wallet_address,
                from_chain_id=chain_id
            )
            return await process_bridge(bridge_request, redis_service)
        
        # Check if this is a balance command
        elif re.search(r"(?:check|show|what'?s|get)\s+(?:my|the)\s+(?:[A-Za-z0-9]+\s+)?balance", content, re.IGNORECASE):
            # Extract token symbol if present
            token_match = re.search(r"(?:check|show|what'?s|get)\s+(?:my|the)\s+([A-Za-z0-9]+)\s+balance", content, re.IGNORECASE)
            token_symbol = token_match.group(1) if token_match else None
            
            # Process as a balance check
            balance_request = BalanceRequest(
                wallet_address=wallet_address,
                chain_id=chain_id,
                token_symbol=token_symbol
            )
            return await check_balance(balance_request)
        
        # Not a recognized Brian command
        return {
            "error": "Not a recognized Brian command",
            "status": "error"
        }
    except Exception as e:
        logger.error(f"Error processing Brian command: {str(e)}")
        return {
            "error": f"Error: {str(e)}",
            "status": "error"
        } 
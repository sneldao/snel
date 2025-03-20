"""
Router for Brian API features.
"""
import os
import json
import logging
import re
from typing import Dict, Any, Optional, List, Union

from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel

from app.services.brian_service import BrianAPIService as BrianService, brian_service
from app.services.token_service import TokenService
from app.services.redis_service import RedisService, get_redis_service
from app.models.commands import TransferCommand, BridgeCommand, BalanceCommand
from app.models.transaction import TransactionResponse

# Set up logging
logger = logging.getLogger(__name__)

# Create API router
router = APIRouter(prefix="/brian", tags=["brian"])

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
    - "bridge 1 USDC to scroll"
    - "bridge $10 of ETH to scroll"
    """
    # Check for $ format with "of" pattern first
    dollar_of_pattern = r"bridge\s+\$(\d+(?:\.\d+)?)\s+(?:of|worth\s+of)?\s+([A-Za-z0-9]+)\s+(?:to)\s+([A-Za-z0-9]+)"
    dollar_of_match = re.search(dollar_of_pattern, command, re.IGNORECASE)
    
    # Check for $ format without "of"
    dollar_pattern = r"bridge\s+\$(\d+(?:\.\d+)?)\s+([A-Za-z0-9]+)\s+(?:to)\s+([A-Za-z0-9]+)"
    dollar_match = re.search(dollar_pattern, command, re.IGNORECASE)
    
    # First check for full format with "from" and "to"
    full_pattern = r"bridge\s+(\d+(?:\.\d+)?)\s+([A-Za-z0-9]+)\s+(?:from)\s+([A-Za-z0-9]+)\s+(?:to)\s+([A-Za-z0-9]+)"
    full_match = re.search(full_pattern, command, re.IGNORECASE)
    
    # Check for simplified format with just "to"
    simple_pattern = r"bridge\s+(\d+(?:\.\d+)?)\s+([A-Za-z0-9]+)\s+(?:to)\s+([A-Za-z0-9]+)"
    simple_match = re.search(simple_pattern, command, re.IGNORECASE)
    
    if dollar_of_match:
        amount = float(dollar_of_match.group(1))
        token = dollar_of_match.group(2).upper()
        # For dollar formats, we'll use the current user's chain as the source
        # Will be set based on user's current chain in the calling function
        from_chain = None
        to_chain = dollar_of_match.group(3).lower()
    elif dollar_match:
        amount = float(dollar_match.group(1))
        token = dollar_match.group(2).upper()
        # For dollar formats, we'll use the current user's chain as the source
        from_chain = None
        to_chain = dollar_match.group(3).lower()
    elif full_match:
        amount = float(full_match.group(1))
        token = full_match.group(2).upper()
        from_chain = full_match.group(3).lower()
        to_chain = full_match.group(4).lower()
    elif simple_match:
        amount = float(simple_match.group(1))
        token = simple_match.group(2).upper()
        # For simple pattern, use the current chain as source
        # Will be set in the calling function
        from_chain = None
        to_chain = simple_match.group(3).lower()
    else:
        raise ValueError("Invalid bridge command format. Expected: 'bridge [amount] [token] from [source chain] to [destination chain]', 'bridge [amount] [token] to [destination chain]' or 'bridge $[amount] of [token] to [destination chain]'")
    
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
    
    # Use the provided from_chain_id if specified, otherwise it will be set in the bridging function
    from_chain_id = chain_map.get(from_chain, None) if from_chain else None
    to_chain_id = chain_map.get(to_chain, 8453)  # Default to Base only if destination not found
    
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

# Helper function to get the chain name
def get_chain_name(chain_id: int) -> str:
    """
    Get the name of a chain from its ID.
    
    Args:
        chain_id: The chain ID
        
    Returns:
        The chain name
    """
    chain_map = {
        1: "ethereum",
        10: "optimism",
        56: "binance",
        137: "polygon",
        42161: "arbitrum",
        8453: "base",
        534352: "scroll",
        43114: "avalanche"
    }
    
    return chain_map.get(chain_id, f"chain_{chain_id}")

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
        try:
            logger.info(f"Storing command in Redis: {request.command}")
            await redis_service.store_pending_command(
                wallet_address=request.wallet_address,
                command=request.command,
                is_brian_operation=True
            )
            logger.info("Command stored successfully")
        except Exception as redis_error:
            logger.error(f"Error storing command in Redis: {str(redis_error)}")
            # Continue even if Redis fails
        
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
            agent_type="brian",
            is_brian_operation=True
        )
    except ValueError as e:
        logger.error(f"Error processing transfer command: {str(e)}")
        return TransactionResponse(
            error=str(e),
            status="error",
            is_brian_operation=True
        )
    except Exception as e:
        logger.error(f"Unexpected error processing transfer command: {str(e)}")
        return TransactionResponse(
            error=f"Unexpected error: {str(e)}",
            status="error",
            is_brian_operation=True
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
        
        # Set the from_chain_id if not provided in the command
        if bridge_command.from_chain_id is None:
            bridge_command.from_chain_id = request.from_chain_id
            logger.info(f"Setting bridge source chain to user's current chain: {request.from_chain_id}")
        
        # Get the token symbol
        token_symbol = bridge_command.token
        if isinstance(token_symbol, dict):
            token_symbol = token_symbol.get("symbol", "")
        
        # Get the transaction data from Brian API
        try:
            tx_data = await brian_service.get_bridge_transaction(
                token_symbol=token_symbol,
                amount=bridge_command.amount,
                from_chain_id=bridge_command.from_chain_id,
                to_chain_id=bridge_command.to_chain_id,
                wallet_address=request.wallet_address
            )
        except Exception as e:
            logger.error(f"Error getting bridge transaction: {e}")
            return TransactionResponse(
                error=f"Failed to get bridge transaction: {str(e)}",
                status="error",
                is_brian_operation=True
            )
        
        # Store the pending command
        try:
            logger.info(f"Storing command in Redis: {request.command}")
            await redis_service.store_pending_command(
                wallet_address=request.wallet_address,
                command=request.command,
                is_brian_operation=True
            )
            logger.info("Command stored successfully")
        except Exception as redis_error:
            logger.error(f"Error storing command in Redis: {str(redis_error)}")
            # Continue even if Redis fails
        
        # Check if we have quotes
        if "all_quotes" in tx_data and tx_data["all_quotes"]:
            # Get the first non-approval quote
            main_quote = next((q for q in tx_data["all_quotes"] if not q.get("is_approval")), tx_data["all_quotes"][0])
            
            # Get basic chain info
            from_chain_name = get_chain_name(bridge_command.from_chain_id)
            to_chain_name = get_chain_name(bridge_command.to_chain_id)
            
            # Enhance metadata with additional info
            enhanced_metadata = tx_data.get("metadata", {})
            enhanced_metadata.update({
                "token_symbol": token_symbol,
                "amount": bridge_command.amount, 
                "from_chain_id": bridge_command.from_chain_id,
                "to_chain_id": bridge_command.to_chain_id,
                "from_chain_name": from_chain_name,
                "to_chain_name": to_chain_name
            })
            
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
                metadata=enhanced_metadata,
                agent_type="brian",
                status="success",
                is_brian_operation=True,
                awaiting_confirmation=True  # Always require confirmation for bridge operations
            )
        else:
            return TransactionResponse(
                error="No valid bridge quotes found",
                status="error",
                is_brian_operation=True
            )
            
    except ValueError as e:
        logger.error(f"Error processing bridge command: {str(e)}")
        return TransactionResponse(
            error=str(e),
            status="error",
            is_brian_operation=True
        )
    except Exception as e:
        logger.error(f"Unexpected error processing bridge command: {str(e)}")
        return TransactionResponse(
            error=f"Unexpected error: {str(e)}",
            status="error",
            is_brian_operation=True
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
        
        # Log the incoming command for debugging
        logger.info(f"Processing Brian command: '{content}' with chain_id: {chain_id}")
        
        # Check if this is a confirmation
        normalized_content = content.lower().strip() if isinstance(content, str) else ""
        if normalized_content in ["yes", "y", "yeah", "yep", "ok", "okay", "sure", "confirm"]:
            logger.info("Detected confirmation command")
            # This will be handled by the commands_router.py file which calls brian_agent directly
            return {
                "message": "Processing your confirmation...",
                "status": "success",
                "is_pending_confirmation": True
            }
        
        # Check if this is a dollar amount transfer command
        if re.search(r"(?:transfer|send)\s+\$\d+(?:\.\d+)?\s+(?:of|worth\s+of)\s+[A-Za-z0-9]+\s+(?:to)\s+[A-Za-z0-9\.]+", content, re.IGNORECASE):
            logger.info("Detected dollar amount transfer command pattern")
            
            # We'll need a proper implementation for this, but for now, route to the general handler
            # This will be handled by brian_agent directly in the commands_router.py
            return {
                "message": "Processing dollar amount transfer...",
                "status": "success",
                "is_brian_operation": True,
                "is_dollar_amount": True
            }
        
        # Check if this is a transfer command
        if re.search(r"(?:send|transfer)\s+\d+(?:\.\d+)?\s+[A-Za-z0-9]+\s+(?:to)\s+[A-Za-z0-9\.]+", content, re.IGNORECASE):
            logger.info("Detected transfer command pattern")
            # Process as a transfer
            transfer_request = TransferRequest(
                command=content,
                wallet_address=wallet_address,
                chain_id=chain_id
            )
            result = await process_transfer(transfer_request, redis_service)
            # Add a marker to identify this as a Brian operation
            if isinstance(result, dict):
                result["is_brian_operation"] = True
            return result
        
        # Check if this is a bridge command - both full and simplified format
        elif (re.search(r"bridge\s+\d+(?:\.\d+)?\s+[A-Za-z0-9]+\s+(?:from)\s+[A-Za-z0-9]+\s+(?:to)\s+[A-Za-z0-9]+", content, re.IGNORECASE) or
              re.search(r"bridge\s+\d+(?:\.\d+)?\s+[A-Za-z0-9]+\s+(?:to)\s+[A-Za-z0-9]+", content, re.IGNORECASE) or
              re.search(r"bridge\s+\$\d+(?:\.\d+)?(?:\s+of|\s+worth\s+of)?\s+[A-Za-z0-9]+\s+(?:to)\s+[A-Za-z0-9]+", content, re.IGNORECASE)):
            logger.info("Detected bridge command pattern")
            # Process as a bridge
            try:
                bridge_command = parse_bridge_command(content)
                logger.info(f"Parsed bridge command: from chain {bridge_command.from_chain_id} to chain {bridge_command.to_chain_id}, token: {bridge_command.token}, amount: {bridge_command.amount}")
                
                bridge_request = BridgeRequest(
                    command=content,
                    wallet_address=wallet_address,
                    from_chain_id=bridge_command.from_chain_id if bridge_command.from_chain_id else chain_id
                )
                result = await process_bridge(bridge_request, redis_service)
                
                # Mark this as a Brian operation
                if isinstance(result, dict):
                    result["is_brian_operation"] = True
                    
                    # Store as pending command for confirmation
                    try:
                        await redis_service.store_pending_command(
                            wallet_address,
                            content,
                            is_brian_operation=True
                        )
                        logger.info(f"Stored bridge command as pending for {wallet_address}")
                    except Exception as redis_err:
                        logger.error(f"Failed to store bridge command in Redis: {redis_err}")
                
                return result
            except ValueError as e:
                logger.error(f"Error parsing bridge command: {e}")
                return {
                    "error": f"Invalid bridge command: {str(e)}",
                    "status": "error",
                    "is_brian_operation": True
                }
        
        # Check if this is a balance command
        elif re.search(r"(?:check|show|what'?s|get)\s+(?:my|the)\s+(?:[A-Za-z0-9]+\s+)?balance", content, re.IGNORECASE):
            logger.info("Detected balance command pattern")
            # Extract token symbol if present
            token_match = re.search(r"(?:check|show|what'?s|get)\s+(?:my|the)\s+([A-Za-z0-9]+)\s+balance", content, re.IGNORECASE)
            token_symbol = token_match.group(1) if token_match else None
            
            # Process as a balance check
            balance_request = BalanceRequest(
                wallet_address=wallet_address,
                chain_id=chain_id,
                token_symbol=token_symbol
            )
            result = await check_balance(balance_request)
            # Add a marker to identify this as a Brian operation
            if isinstance(result, dict):
                result["is_brian_operation"] = True
            return result
        
        # Not a recognized Brian command
        logger.warning(f"Command not recognized as Brian API command: '{content}'")
        return {
            "error": "Not a recognized Brian command. Please try a transfer, bridge, or balance command.",
            "status": "error",
            "is_brian_operation": True
        }
    except Exception as e:
        logger.error(f"Error processing Brian command: {str(e)}", exc_info=True)
        return {
            "error": f"Error: {str(e)}",
            "status": "error",
            "is_brian_operation": True
        }

@router.post("/execute-bridge")
async def execute_bridge(bridge_command: BridgeCommand, wallet_address: Optional[str] = None, chain_id: Optional[int] = None):
    """
    Execute a cross-chain bridge transaction using the Brian API.
    
    Args:
        bridge_command: The bridge command
        wallet_address: The wallet address
        chain_id: The current chain ID
        
    Returns:
        Dictionary with transaction data
    """
    try:
        # Create token service
        token_service = TokenService()
        
        # If from_chain_id is None, use the provided chain_id or default to Ethereum
        if bridge_command.from_chain_id is None:
            bridge_command.from_chain_id = chain_id if chain_id is not None else 1
            logger.info(f"Setting bridge source chain to user's current chain: {bridge_command.from_chain_id}")
        
        # Get the token symbol
        token_symbol = bridge_command.token
        if isinstance(token_symbol, dict):
            token_symbol = token_symbol.get("symbol", "")
            
        # Look up token info
        token_info = await token_service.lookup_token(token_symbol, bridge_command.from_chain_id)
        if not token_info or not token_info[0]:
            raise HTTPException(
                status_code=400,
                detail=f"Could not find token information for {token_symbol} on chain {bridge_command.from_chain_id}"
            )
        
        # Extract token info
        token_address, token_symbol, token_name, token_metadata = token_info
        
        # Construct the bridge prompt for the Brian API
        from_chain_name = get_chain_name(bridge_command.from_chain_id)
        to_chain_name = get_chain_name(bridge_command.to_chain_id)
        
        prompt = f"bridge {bridge_command.amount} {token_symbol} from {from_chain_name} to {to_chain_name}"
        logger.info(f"Sending bridge prompt to Brian API: {prompt}")
        
        # Create an instance of BrianService
        api_key = os.getenv("BRIAN_API_KEY")
        if not api_key:
            raise HTTPException(status_code=500, detail="Brian API key not configured")
        
        brian_service_instance = BrianService(api_key=api_key)
        
        # Call the Brian API
        brian_response = await brian_service_instance._make_api_request(
            "POST",
            "agent/transaction",
            json={
                "prompt": prompt,
                "address": wallet_address or "0x0000000000000000000000000000000000000000",
                "chainId": str(bridge_command.from_chain_id)
            }
        )
        logger.info(f"Brian API response: {json.dumps(brian_response, indent=2)}")
        
        if not brian_response or not brian_response.get("result"):
            raise HTTPException(
                status_code=400,
                detail=f"Failed to get bridge data for {token_symbol} from {from_chain_name} to {to_chain_name}"
            )
        
        result = brian_response["result"][0]
        
        if not result or not result.get("data"):
            raise HTTPException(
                status_code=400,
                detail=f"No valid bridge data received for {token_symbol} from {from_chain_name} to {to_chain_name}"
            )
        
        # Extract transaction data
        tx_data = result["data"]
        
        # Format the response
        steps = tx_data.get("steps", [])
        
        if not steps:
            raise HTTPException(
                status_code=400,
                detail="No transaction steps found in bridge data"
            )
        
        # Extract the first step (usually approval)
        first_step = steps[0]
        
        # Return formatted transaction data
        return {
            "transaction": {
                "to": first_step["to"],
                "data": first_step["data"],
                "value": first_step.get("value", "0"),
                "chainId": bridge_command.from_chain_id,
                "gasLimit": first_step.get("gasLimit", "500000"),
            },
            "description": tx_data.get("description", f"Bridge {bridge_command.amount} {token_symbol} from {from_chain_name} to {to_chain_name}"),
            "steps": steps,
            "fromChain": {
                "id": bridge_command.from_chain_id,
                "name": from_chain_name
            },
            "toChain": {
                "id": bridge_command.to_chain_id,
                "name": to_chain_name
            },
            "solver": result.get("solver", "Bungee"),
            "token": token_symbol,
            "amount": bridge_command.amount,
            "fromAmount": tx_data.get("fromAmount"),
            "toAmount": tx_data.get("toAmount"),
            "toAmountMin": tx_data.get("toAmountMin"),
            "fromToken": tx_data.get("fromToken", {}),
            "toToken": tx_data.get("toToken", {}),
            "all_steps": steps
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error executing bridge: {str(e)}", exc_info=True)
"""
Router for Brian API features.
"""
import os
import json
import logging
import re
from typing import Dict, Any, Optional, List, Union

from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel

from app.services.brian_service import BrianAPIService as BrianService, brian_service
from app.services.token_service import TokenService
from app.services.redis_service import RedisService, get_redis_service
from app.models.commands import TransferCommand, BridgeCommand, BalanceCommand
from app.models.transaction import TransactionResponse

# Set up logging
logger = logging.getLogger(__name__)

# Create API router
router = APIRouter(prefix="/brian", tags=["brian"])

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
    - "bridge 1 USDC to scroll"
    - "bridge $10 of ETH to scroll"
    """
    # Check for $ format with "of" pattern first
    dollar_of_pattern = r"bridge\s+\$(\d+(?:\.\d+)?)\s+(?:of|worth\s+of)?\s+([A-Za-z0-9]+)\s+(?:to)\s+([A-Za-z0-9]+)"
    dollar_of_match = re.search(dollar_of_pattern, command, re.IGNORECASE)
    
    # Check for $ format without "of"
    dollar_pattern = r"bridge\s+\$(\d+(?:\.\d+)?)\s+([A-Za-z0-9]+)\s+(?:to)\s+([A-Za-z0-9]+)"
    dollar_match = re.search(dollar_pattern, command, re.IGNORECASE)
    
    # First check for full format with "from" and "to"
    full_pattern = r"bridge\s+(\d+(?:\.\d+)?)\s+([A-Za-z0-9]+)\s+(?:from)\s+([A-Za-z0-9]+)\s+(?:to)\s+([A-Za-z0-9]+)"
    full_match = re.search(full_pattern, command, re.IGNORECASE)
    
    # Check for simplified format with just "to"
    simple_pattern = r"bridge\s+(\d+(?:\.\d+)?)\s+([A-Za-z0-9]+)\s+(?:to)\s+([A-Za-z0-9]+)"
    simple_match = re.search(simple_pattern, command, re.IGNORECASE)
    
    if dollar_of_match:
        amount = float(dollar_of_match.group(1))
        token = dollar_of_match.group(2).upper()
        # For dollar formats, we'll use the current user's chain as the source
        # Will be set based on user's current chain in the calling function
        from_chain = None
        to_chain = dollar_of_match.group(3).lower()
    elif dollar_match:
        amount = float(dollar_match.group(1))
        token = dollar_match.group(2).upper()
        # For dollar formats, we'll use the current user's chain as the source
        from_chain = None
        to_chain = dollar_match.group(3).lower()
    elif full_match:
        amount = float(full_match.group(1))
        token = full_match.group(2).upper()
        from_chain = full_match.group(3).lower()
        to_chain = full_match.group(4).lower()
    elif simple_match:
        amount = float(simple_match.group(1))
        token = simple_match.group(2).upper()
        # For simple pattern, use the current chain as source
        # Will be set in the calling function
        from_chain = None
        to_chain = simple_match.group(3).lower()
    else:
        raise ValueError("Invalid bridge command format. Expected: 'bridge [amount] [token] from [source chain] to [destination chain]', 'bridge [amount] [token] to [destination chain]' or 'bridge $[amount] of [token] to [destination chain]'")
    
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
    
    # Use the provided from_chain_id if specified, otherwise it will be set in the bridging function
    from_chain_id = chain_map.get(from_chain, None) if from_chain else None
    to_chain_id = chain_map.get(to_chain, 8453)  # Default to Base only if destination not found
    
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

# Helper function to get the chain name
def get_chain_name(chain_id: int) -> str:
    """
    Get the name of a chain from its ID.
    
    Args:
        chain_id: The chain ID
        
    Returns:
        The chain name
    """
    chain_map = {
        1: "ethereum",
        10: "optimism",
        56: "binance",
        137: "polygon",
        42161: "arbitrum",
        8453: "base",
        534352: "scroll",
        43114: "avalanche"
    }
    
    return chain_map.get(chain_id, f"chain_{chain_id}")

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
        try:
            logger.info(f"Storing command in Redis: {request.command}")
            await redis_service.store_pending_command(
                wallet_address=request.wallet_address,
                command=request.command,
                is_brian_operation=True
            )
            logger.info("Command stored successfully")
        except Exception as redis_error:
            logger.error(f"Error storing command in Redis: {str(redis_error)}")
            # Continue even if Redis fails
        
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
            agent_type="brian",
            is_brian_operation=True
        )
    except ValueError as e:
        logger.error(f"Error processing transfer command: {str(e)}")
        return TransactionResponse(
            error=str(e),
            status="error",
            is_brian_operation=True
        )
    except Exception as e:
        logger.error(f"Unexpected error processing transfer command: {str(e)}")
        return TransactionResponse(
            error=f"Unexpected error: {str(e)}",
            status="error",
            is_brian_operation=True
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
        try:
            tx_data = await brian_service.get_bridge_transaction(
                token_symbol=token_symbol,
                amount=bridge_command.amount,
                from_chain_id=bridge_command.from_chain_id,
                to_chain_id=bridge_command.to_chain_id,
                wallet_address=request.wallet_address
            )
        except Exception as e:
            logger.error(f"Error getting bridge transaction: {e}")
            return TransactionResponse(
                error=f"Failed to get bridge transaction: {str(e)}",
                status="error",
                is_brian_operation=True
            )
        
        # Store the pending command
        try:
            logger.info(f"Storing command in Redis: {request.command}")
            await redis_service.store_pending_command(
                wallet_address=request.wallet_address,
                command=request.command,
                is_brian_operation=True
            )
            logger.info("Command stored successfully")
        except Exception as redis_error:
            logger.error(f"Error storing command in Redis: {str(redis_error)}")
            # Continue even if Redis fails
        
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
                metadata=tx_data.get("metadata", {}),
                agent_type="brian",
                status="success",
                is_brian_operation=True
            )
        else:
            return TransactionResponse(
                error="No valid bridge quotes found",
                status="error",
                is_brian_operation=True
            )
            
    except ValueError as e:
        logger.error(f"Error processing bridge command: {str(e)}")
        return TransactionResponse(
            error=str(e),
            status="error",
            is_brian_operation=True
        )
    except Exception as e:
        logger.error(f"Unexpected error processing bridge command: {str(e)}")
        return TransactionResponse(
            error=f"Unexpected error: {str(e)}",
            status="error",
            is_brian_operation=True
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
        
        # Log the incoming command for debugging
        logger.info(f"Processing Brian command: '{content}' with chain_id: {chain_id}")
        
        # Check if this is a transfer command
        if re.search(r"(?:send|transfer)\s+\d+(?:\.\d+)?\s+[A-Za-z0-9]+\s+(?:to)\s+[A-Za-z0-9\.]+", content, re.IGNORECASE):
            logger.info("Detected transfer command pattern")
            # Process as a transfer
            transfer_request = TransferRequest(
                command=content,
                wallet_address=wallet_address,
                chain_id=chain_id
            )
            result = await process_transfer(transfer_request, redis_service)
            # Add a marker to identify this as a Brian operation
            if isinstance(result, dict):
                result["is_brian_operation"] = True
            return result
        
        # Check if this is a bridge command - both full and simplified format
        elif (re.search(r"bridge\s+\d+(?:\.\d+)?\s+[A-Za-z0-9]+\s+(?:from)\s+[A-Za-z0-9]+\s+(?:to)\s+[A-Za-z0-9]+", content, re.IGNORECASE) or
              re.search(r"bridge\s+\d+(?:\.\d+)?\s+[A-Za-z0-9]+\s+(?:to)\s+[A-Za-z0-9]+", content, re.IGNORECASE) or
              re.search(r"bridge\s+\$\d+(?:\.\d+)?(?:\s+of|\s+worth\s+of)?\s+[A-Za-z0-9]+\s+(?:to)\s+[A-Za-z0-9]+", content, re.IGNORECASE)):
            logger.info("Detected bridge command pattern")
            # Process as a bridge
            try:
                bridge_command = parse_bridge_command(content)
                logger.info(f"Parsed bridge command: from chain {bridge_command.from_chain_id} to chain {bridge_command.to_chain_id}, token: {bridge_command.token}, amount: {bridge_command.amount}")
                
                bridge_request = BridgeRequest(
                    command=content,
                    wallet_address=wallet_address,
                    from_chain_id=bridge_command.from_chain_id
                )
                result = await process_bridge(bridge_request, redis_service)
                # Add a marker to identify this as a Brian operation
                if isinstance(result, dict):
                    result["is_brian_operation"] = True
                return result
            except ValueError as e:
                logger.error(f"Error parsing bridge command: {e}")
                return {
                    "error": f"Invalid bridge command: {str(e)}",
                    "status": "error",
                    "is_brian_operation": True
                }
        
        # Check if this is a balance command
        elif re.search(r"(?:check|show|what'?s|get)\s+(?:my|the)\s+(?:[A-Za-z0-9]+\s+)?balance", content, re.IGNORECASE):
            logger.info("Detected balance command pattern")
            # Extract token symbol if present
            token_match = re.search(r"(?:check|show|what'?s|get)\s+(?:my|the)\s+([A-Za-z0-9]+)\s+balance", content, re.IGNORECASE)
            token_symbol = token_match.group(1) if token_match else None
            
            # Process as a balance check
            balance_request = BalanceRequest(
                wallet_address=wallet_address,
                chain_id=chain_id,
                token_symbol=token_symbol
            )
            result = await check_balance(balance_request)
            # Add a marker to identify this as a Brian operation
            if isinstance(result, dict):
                result["is_brian_operation"] = True
            return result
        
        # Not a recognized Brian command
        logger.warning(f"Command not recognized as Brian API command: '{content}'")
        return {
            "error": "Not a recognized Brian command. Please try a transfer, bridge, or balance command.",
            "status": "error",
            "is_brian_operation": True
        }
    except Exception as e:
        logger.error(f"Error processing Brian command: {str(e)}", exc_info=True)
        return {
            "error": f"Error: {str(e)}",
            "status": "error",
            "is_brian_operation": True
        }

@router.post("/execute-bridge")
async def execute_bridge(bridge_command: BridgeCommand, wallet_address: Optional[str] = None, chain_id: Optional[int] = None):
    """
    Execute a cross-chain bridge transaction using the Brian API.
    
    Args:
        bridge_command: The bridge command
        wallet_address: The wallet address
        chain_id: The current chain ID
        
    Returns:
        Dictionary with transaction data
    """
    try:
        # Create token service
        token_service = TokenService()
        
        # If from_chain_id is None, use the provided chain_id or default to Ethereum
        if bridge_command.from_chain_id is None:
            bridge_command.from_chain_id = chain_id if chain_id is not None else 1
            logger.info(f"Setting bridge source chain to user's current chain: {bridge_command.from_chain_id}")
        
        # Get the token symbol
        token_symbol = bridge_command.token
        if isinstance(token_symbol, dict):
            token_symbol = token_symbol.get("symbol", "")
            
        # Look up token info
        token_info = await token_service.lookup_token(token_symbol, bridge_command.from_chain_id)
        if not token_info or not token_info[0]:
            raise HTTPException(
                status_code=400,
                detail=f"Could not find token information for {token_symbol} on chain {bridge_command.from_chain_id}"
            )
        
        # Extract token info
        token_address, token_symbol, token_name, token_metadata = token_info
        
        # Construct the bridge prompt for the Brian API
        from_chain_name = get_chain_name(bridge_command.from_chain_id)
        to_chain_name = get_chain_name(bridge_command.to_chain_id)
        
        prompt = f"bridge {bridge_command.amount} {token_symbol} from {from_chain_name} to {to_chain_name}"
        logger.info(f"Sending bridge prompt to Brian API: {prompt}")
        
        # Create an instance of BrianService
        api_key = os.getenv("BRIAN_API_KEY")
        if not api_key:
            raise HTTPException(status_code=500, detail="Brian API key not configured")
        
        brian_service_instance = BrianService(api_key=api_key)
        
        # Call the Brian API
        brian_response = await brian_service_instance._make_api_request(
            "POST",
            "agent/transaction",
            json={
                "prompt": prompt,
                "address": wallet_address or "0x0000000000000000000000000000000000000000",
                "chainId": str(bridge_command.from_chain_id)
            }
        )
        logger.info(f"Brian API response: {json.dumps(brian_response, indent=2)}")
        
        if not brian_response or not brian_response.get("result"):
            raise HTTPException(
                status_code=400,
                detail=f"Failed to get bridge data for {token_symbol} from {from_chain_name} to {to_chain_name}"
            )
        
        result = brian_response["result"][0]
        
        if not result or not result.get("data"):
            raise HTTPException(
                status_code=400,
                detail=f"No valid bridge data received for {token_symbol} from {from_chain_name} to {to_chain_name}"
            )
        
        # Extract transaction data
        tx_data = result["data"]
        
        # Format the response
        steps = tx_data.get("steps", [])
        
        if not steps:
            raise HTTPException(
                status_code=400,
                detail="No transaction steps found in bridge data"
            )
        
        # Extract the first step (usually approval)
        first_step = steps[0]
        
        # Return formatted transaction data
        return {
            "transaction": {
                "to": first_step["to"],
                "data": first_step["data"],
                "value": first_step.get("value", "0"),
                "chainId": bridge_command.from_chain_id,
                "gasLimit": first_step.get("gasLimit", "500000"),
            },
            "description": tx_data.get("description", f"Bridge {bridge_command.amount} {token_symbol} from {from_chain_name} to {to_chain_name}"),
            "steps": steps,
            "fromChain": {
                "id": bridge_command.from_chain_id,
                "name": from_chain_name
            },
            "toChain": {
                "id": bridge_command.to_chain_id,
                "name": to_chain_name
            },
            "solver": result.get("solver", "Bungee"),
            "token": token_symbol,
            "amount": bridge_command.amount,
            "fromAmount": tx_data.get("fromAmount"),
            "toAmount": tx_data.get("toAmount"),
            "toAmountMin": tx_data.get("toAmountMin"),
            "fromToken": tx_data.get("fromToken", {}),
            "toToken": tx_data.get("toToken", {}),
            "all_steps": steps
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error executing bridge: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to execute bridge: {str(e)}") 
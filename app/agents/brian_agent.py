"""
Agent for Brian API features including token transfers, cross-chain bridging, and balance checking.
"""
import logging
import re
import json
import uuid
import time
from typing import Dict, Any, Optional, List, Union, Tuple
from pydantic import BaseModel

from app.agents.base import PointlessAgent, AgentMessage
from app.services.brian_service import brian_service
from app.services.token_service import TokenService
from app.services.redis_service import RedisService, get_redis_service
from app.models.commands import TransferCommand, BridgeCommand, BalanceCommand
from app.services.prices import get_token_price

logger = logging.getLogger(__name__)

# Constants
CONFIRMATION_EXPIRY = 60 * 10  # 10 minutes in seconds

class BrianAgent(PointlessAgent):
    """Agent for Brian API features."""
    token_service: Optional[TokenService] = None
    redis_service: Optional[RedisService] = None
    
    def __init__(self, token_service: Optional[TokenService] = None, redis_service: Optional[RedisService] = None, provider = None, api_key: Optional[str] = None):
        """Initialize the Brian agent."""
        prompt = """You are a helpful assistant that processes Web3 commands using the Brian API.
        You can handle token transfers, cross-chain bridging, and balance checking.
        Extract the relevant information from user queries and format it for the Brian API."""
        
        super().__init__(
            prompt=prompt,
            model="gpt-4-turbo-preview",
            temperature=0.7,
            provider=provider,
            api_key=api_key
        )
        
        self.token_service = token_service or TokenService()
        self.redis_service = redis_service or RedisService()
    
    async def process_transfer_command(self, command: str, chain_id: int = 1, wallet_address: Optional[str] = None) -> Dict[str, Any]:
        """
        Process a token transfer command.
        
        Args:
            command: The transfer command (e.g., "send 10 USDC to 0x123...")
            chain_id: The chain ID
            wallet_address: The sender's wallet address
            
        Returns:
            Dictionary with transaction data
        """
        try:
            # Parse the transfer command
            transfer_command = self._parse_transfer_command(command)
            
            # Get the token symbol
            token_symbol = transfer_command.token
            if isinstance(token_symbol, dict):
                token_symbol = token_symbol.get("symbol", "")
            
            # Look up token info
            token_info = await self.token_service.lookup_token(token_symbol, chain_id)
            if not token_info or not token_info[0]:
                return AgentMessage(
                    error=f"Could not find token information for {token_symbol}",
                    metadata={"token": token_symbol}
                ).model_dump()
            
            # Extract token info
            token_address, token_symbol, token_name, token_metadata = token_info
            
            # Get the transaction data from Brian API
            tx_data = await brian_service.get_transfer_transaction(
                token_symbol=token_symbol,
                amount=transfer_command.amount,
                recipient_address=transfer_command.recipient,
                wallet_address=wallet_address,
                chain_id=chain_id
            )
            
            # Format the response for the frontend to execute
            transaction_data = {
                "to": tx_data["to"],
                "data": tx_data["data"],
                "value": tx_data.get("value", "0"),
                "chainId": chain_id,
                "gasLimit": tx_data.get("gas", "300000"),
                "method": "transfer"
            }
            
            return {
                "content": {
                    "type": "transaction",
                    "message": f"Ready to transfer {transfer_command.amount} {token_symbol} to {transfer_command.recipient}",
                    "transaction": transaction_data
                },
                "metadata": {
                    "token_symbol": token_symbol,
                    "token_name": token_name,
                    "token_address": token_address,
                    "amount": transfer_command.amount,
                    "recipient": transfer_command.recipient,
                    "chain_id": chain_id,
                    "chain_name": self._get_chain_name(chain_id)
                },
                "agent_type": "brian",
                "is_brian_operation": True,
                "awaitingConfirmation": True,
                "transaction": transaction_data
            }
            
        except Exception as e:
            logger.error(f"Error processing transfer command: {str(e)}")
            return AgentMessage(
                error=f"Failed to process transfer command: {str(e)}",
                metadata={"command": command}
            ).model_dump()
    
    async def process_bridge_command(
        self, 
        command: str, 
        chain_id: int = 1, 
        wallet_address: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process a bridge command.
        
        Args:
            command: The bridge command to process
            chain_id: The current chain ID the user is on
            wallet_address: The wallet address
            
        Returns:
            Dictionary with response data
        """
        try:
            # Parse the bridge command
            bridge_command = self._parse_bridge_command(command)
            
            # If from_chain_id is None, use the provided chain_id
            if bridge_command.from_chain_id is None:
                bridge_command.from_chain_id = chain_id
                logger.info(f"Using user's current chain ID for bridge source: {chain_id}")
            
            # Get source token info
            token_service = self.token_service
            token_info = await token_service.lookup_token(
                bridge_command.token, 
                bridge_command.from_chain_id
            )
            
            if not token_info or not token_info[0]:
                logger.error(f"Token {bridge_command.token} not found on chain {bridge_command.from_chain_id}")
                return AgentMessage(
                    error=f"Token {bridge_command.token} not found on chain {bridge_command.from_chain_id}",
                    metadata={"command": command}
                ).model_dump()
                
            # Extract token address
            token_address, token_symbol, token_name, token_metadata = token_info
            
            # Log token info
            logger.info(f"Found token: {token_symbol} ({token_name}) at address {token_address} on chain {bridge_command.from_chain_id}")
            
            # Construct the Brian API prompt based on the input
            from_chain_name = self._get_chain_name(bridge_command.from_chain_id)
            to_chain_name = self._get_chain_name(bridge_command.to_chain_id)
            
            prompt = f"bridge {bridge_command.amount} {bridge_command.token} from {from_chain_name} to {to_chain_name}"
            logger.info(f"Sending bridge prompt to Brian API: {prompt}")
            
            # Call the Brian API
            try:
                brian_response = await brian_service._make_api_request(
                    "POST",
                    "agent/transaction",
                    json={
                        "prompt": prompt,
                        "address": wallet_address or "0x0000000000000000000000000000000000000000",
                        "chainId": str(bridge_command.from_chain_id)
                    }
                )
                logger.info(f"Brian API bridge response: {json.dumps(brian_response, indent=2)}")
            except Exception as api_err:
                logger.error(f"Error calling Brian API: {api_err}", exc_info=True)
                return AgentMessage(
                    error=f"Failed to get bridge data from Brian API: {str(api_err)}",
                    metadata={"command": command}
                ).model_dump()
            
            if not brian_response or not brian_response.get("result"):
                logger.error("No result field in Brian API response")
                return AgentMessage(
                    error=f"Failed to get bridge data for {bridge_command.token} from {from_chain_name} to {to_chain_name}",
                    metadata={"command": command}
                ).model_dump()
            
            result = brian_response["result"][0]
            
            if not result or not result.get("data"):
                logger.error("No data field in Brian API result")
                return AgentMessage(
                    error=f"No valid bridge data received for {bridge_command.token} from {from_chain_name} to {to_chain_name}",
                    metadata={"command": command}
                ).model_dump()
            
            # Extract transaction data
            tx_data = result["data"]
            
            # Get token price for displaying USD value
            token_price, timestamp = await self.token_service.get_token_price(
                bridge_command.token, 
                "usd",
                bridge_command.from_chain_id
            )
            
            # Create a unique ID for this bridge request
            bridge_id = f"bridge_{str(uuid.uuid4())}"
            
            # Store the bridge info in Redis for confirmation
            try:
                if self.redis_service and wallet_address:
                    await self.redis_service.set_with_expiry(
                        bridge_id, 
                        json.dumps({
                            "command": bridge_command.model_dump(),
                            "tx_data": tx_data,
                            "wallet_address": wallet_address,
                            "timestamp": int(time.time())
                        }),
                        CONFIRMATION_EXPIRY
                    )
                    logger.info(f"Stored bridge request in Redis with ID {bridge_id}")
                    
                    # Also store as the pending command
                    await self.redis_service.store_pending_command(
                        wallet_address=wallet_address,
                        command=command,
                        is_brian_operation=True
                    )
                    logger.info(f"Stored bridge command as pending command for {wallet_address}")
            except Exception as redis_err:
                logger.error(f"Error storing bridge info in Redis: {redis_err}")
                # Continue even if Redis storage fails
            
            # Calculate USD amount if price is available
            usd_value = ""
            usd_amount = None
            if token_price:
                usd_amount = bridge_command.amount * token_price
                usd_value = f" (approximately ${usd_amount:.2f})"
                logger.info(f"Token price: ${token_price}, total value: ${usd_amount}")
            
            # Format the response
            message = f"Ready to bridge {bridge_command.amount} {bridge_command.token}{usd_value} from {from_chain_name} to {to_chain_name} using {result.get('solver', 'Bungee')}."
            
            # Get the steps array for execution
            steps = tx_data.get("steps", [])
            if not steps:
                logger.error("No steps found in transaction data")
                return AgentMessage(
                    error=f"No transaction steps found for bridging {bridge_command.token}",
                    metadata={"command": command}
                ).model_dump()
            
            # Get the first step (approval or bridging)
            first_step = steps[0]
            
            # Check if approval is needed
            is_approval = "approve" in first_step.get("data", "").lower()
            
            # Create transaction data for frontend execution
            transaction_data = {
                "to": first_step["to"],
                "data": first_step["data"],
                "value": first_step.get("value", "0"),
                "chainId": bridge_command.from_chain_id,
                "gasLimit": first_step.get("gasLimit", "500000"),
                "method": "bridge"
            }
            
            return {
                "content": {
                    "type": "brian_confirmation",
                    "message": message,
                    "bridge_id": bridge_id,
                    "data": {
                        "from_chain": {
                            "id": bridge_command.from_chain_id,
                            "name": from_chain_name
                        },
                        "to_chain": {
                            "id": bridge_command.to_chain_id,
                            "name": to_chain_name
                        },
                        "token": bridge_command.token,
                        "amount": bridge_command.amount,
                        "solver": result.get("solver", "Bungee"),
                        "tx_steps": steps,
                        "from_amount": tx_data.get("fromAmount"),
                        "to_amount": tx_data.get("toAmount"),
                        "to_amount_min": tx_data.get("toAmountMin"),
                        "from_token": tx_data.get("fromToken", {}),
                        "to_token": tx_data.get("toToken", {})
                    }
                },
                "metadata": {
                    "token_symbol": bridge_command.token,
                    "amount": bridge_command.amount,
                    "from_chain_id": bridge_command.from_chain_id,
                    "to_chain_id": bridge_command.to_chain_id,
                    "from_chain_name": from_chain_name,
                    "to_chain_name": to_chain_name,
                    "dollar_amount": usd_amount
                },
                "transaction": transaction_data,
                "agent_type": "brian",
                "is_brian_operation": True,
                "awaitingConfirmation": True
            }
            
        except Exception as e:
            logger.error(f"Error processing bridge command: {str(e)}", exc_info=True)
            return AgentMessage(
                error=f"Failed to process bridge command: {str(e)}",
                metadata={"command": command}
            ).model_dump()
    
    async def process_balance_command(self, command: str, chain_id: int = 1, wallet_address: Optional[str] = None) -> Dict[str, Any]:
        """
        Process a balance check command.
        
        Args:
            command: The balance command (e.g., "check my USDC balance on Scroll")
            chain_id: The chain ID
            wallet_address: The wallet address
            
        Returns:
            Dictionary with balance information
        """
        try:
            # Parse the balance command
            balance_command = self._parse_balance_command(command)
            
            # Use the chain ID from the command if provided
            if balance_command.chain_id:
                chain_id = balance_command.chain_id
            
            # Get the token symbol
            token_symbol = balance_command.token
            
            # Get the balance information from Brian API
            balance_data = await brian_service.get_token_balances(
                wallet_address=wallet_address,
                chain_id=chain_id,
                token_symbol=token_symbol
            )
            
            # Format the response
            chain_name = self._get_chain_name(chain_id)
            
            return {
                "content": {
                    "type": "message",
                    "message": balance_data["answer"]
                },
                "metadata": {
                    "wallet_address": wallet_address,
                    "chain_id": chain_id,
                    "chain_name": chain_name,
                    "token_symbol": token_symbol
                },
                "agent_type": "brian",
                "transaction": None  # Balance check doesn't require a transaction
            }
            
        except Exception as e:
            logger.error(f"Error processing balance command: {str(e)}")
            return AgentMessage(
                error=f"Failed to process balance command: {str(e)}",
                metadata={"command": command}
            ).model_dump()
    
    async def process_brian_command(
        self, 
        command: str, 
        chain_id: int = 1, 
        wallet_address: Optional[str] = None,
        user_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process a Brian API command (transfer, bridge, or balance).
        
        Args:
            command: The command to process
            chain_id: The chain ID
            wallet_address: The wallet address
            user_name: The user's display name
            
        Returns:
            Dictionary with response data
        """
        try:
            # Log the incoming command for debugging
            logger.info(f"Processing Brian command: '{command}' with chain_id: {chain_id}")
            
            # Check if this is a confirmation of a previous command
            normalized_command = command.lower().strip()
            
            if normalized_command in ["yes", "y", "yeah", "yep", "ok", "okay", "sure", "confirm"]:
                logger.info("Detected Brian confirmation command")
                # Retrieve and execute the pending command
                return await self.process_brian_confirmation(
                    chain_id=chain_id,
                    wallet_address=wallet_address,
                    user_name=user_name
                )
            
            # Personalize the response with the user's name if available
            name_prefix = f"{user_name}'s" if user_name and user_name != "User" else "Your"
            
            # Normalize command for consistent detection
            normalized_command = command.lower().strip()
            
            # Check if this is a dollar amount transfer command
            if (re.search(r"(?:transfer|send)\s+\$\d+(?:\.\d+)?\s+(?:of|worth\s+of)\s+[A-Za-z0-9]+\s+(?:to)\s+[A-Za-z0-9\.]+", normalized_command, re.IGNORECASE)):
                logger.info("Detected dollar amount transfer command pattern")
                result = await self.process_dollar_transfer_command(command, chain_id, wallet_address)
                
                # Personalize the message if we have a user name
                if user_name and user_name != "User" and "content" in result and isinstance(result["content"], dict):
                    result["content"]["message"] = result["content"]["message"].replace("Ready to transfer", f"Ready to transfer {name_prefix}")
                
                return result
            
            # Special case for dollar amount bridge commands
            if (normalized_command.startswith("bridge $") and 
                (" of " in normalized_command or " worth of " in normalized_command) and 
                " to " in normalized_command):
                logger.info("Detected dollar amount bridge command pattern")
                result = await self.process_bridge_command(command, chain_id, wallet_address)
                
                # Personalize the message if we have a user name
                if user_name and user_name != "User" and "content" in result and isinstance(result["content"], dict):
                    result["content"]["message"] = result["content"]["message"].replace("Ready to bridge", f"Ready to bridge {name_prefix}")
                
                return result
            
            # Check if this is a transfer command
            if re.search(r"(?:send|transfer)\s+\d+(?:\.\d+)?\s+[A-Za-z0-9]+\s+(?:to)\s+[A-Za-z0-9\.]+", command, re.IGNORECASE):
                logger.info("Detected transfer command pattern")
                result = await self.process_transfer_command(command, chain_id, wallet_address)
                
                # Personalize the message if we have a user name
                if user_name and user_name != "User" and "content" in result and isinstance(result["content"], dict):
                    result["content"]["message"] = result["content"]["message"].replace("Ready to transfer", f"Ready to transfer {name_prefix}")
                
                return result
            
            # Check if this is a bridge command (both formats)
            elif (re.search(r"bridge\s+\d+(?:\.\d+)?\s+[A-Za-z0-9]+\s+(?:from)\s+[A-Za-z0-9]+\s+(?:to)\s+[A-Za-z0-9]+", command, re.IGNORECASE) or
                  re.search(r"bridge\s+\d+(?:\.\d+)?\s+[A-Za-z0-9]+\s+(?:to)\s+[A-Za-z0-9]+", command, re.IGNORECASE) or
                  re.search(r"bridge\s+\$\d+(?:\.\d+)?\s+(?:of|worth\s+of)?\s+[A-Za-z0-9]+\s+(?:to)\s+[A-Za-z0-9]+", command, re.IGNORECASE)):
                logger.info("Detected bridge command pattern")
                result = await self.process_bridge_command(command, chain_id, wallet_address)
                
                # Personalize the message if we have a user name
                if user_name and user_name != "User" and "content" in result and isinstance(result["content"], dict):
                    result["content"]["message"] = result["content"]["message"].replace("Ready to bridge", f"Ready to bridge {name_prefix}")
                
                return result
            
            # Check if this is a balance command
            elif re.search(r"(?:check|show|what'?s|get)\s+(?:my|the)\s+(?:[A-Za-z0-9]+\s+)?balance", command, re.IGNORECASE):
                logger.info("Detected balance command pattern")
                result = await self.process_balance_command(command, chain_id, wallet_address)
                
                # Personalize the message if we have a user name
                if user_name and user_name != "User" and "content" in result and isinstance(result["content"], str):
                    result["content"] = result["content"].replace("Your balance", f"{name_prefix} balance")
                
                return result
            
            # If not a recognized command, return an error
            logger.warning(f"Command not recognized as Brian API command: '{command}'")
            return AgentMessage(
                error="Not a recognized Brian API command. Please try a transfer, bridge, or balance command.",
                metadata={"command": command}
            ).model_dump()
            
        except Exception as e:
            logger.error(f"Error processing Brian command: {str(e)}", exc_info=True)
            return AgentMessage(
                error=f"Failed to process Brian command: {str(e)}",
                metadata={"command": command}
            ).model_dump()
    
    async def process_brian_confirmation(
        self,
        chain_id: int = 1,
        wallet_address: Optional[str] = None,
        user_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process a confirmation for a pending Brian operation.
        
        Args:
            chain_id: The chain ID
            wallet_address: The wallet address
            user_name: The user's display name
            
        Returns:
            Dictionary with response data including transaction details
        """
        try:
            if not wallet_address:
                return AgentMessage(
                    error="Wallet address is required for confirmation",
                    metadata={}
                ).model_dump()
                
            # Get the pending command from Redis
            if not self.redis_service:
                logger.error("Redis service not available")
                return AgentMessage(
                    error="Unable to retrieve pending command",
                    metadata={}
                ).model_dump()
                
            pending_data = await self.redis_service.get_pending_command(wallet_address)
            
            if not pending_data:
                logger.warning(f"No pending command found for {wallet_address}")
                return {
                    "content": {
                        "type": "message",
                        "message": "No pending transaction found to confirm. Please try your command again."
                    },
                    "error": "No pending command found",
                    "metadata": {},
                    "agent_type": "brian"
                }
                
            # Extract the command from the pending data
            if isinstance(pending_data, dict):
                pending_command = pending_data.get("command", "")
            else:
                pending_command = str(pending_data)
                
            logger.info(f"Retrieved pending command for confirmation: {pending_command}")
            
            # Process the pending command (bridge or transfer)
            # First check if it's a bridge command
            if re.search(r"bridge\s+\d+(?:\.\d+)?\s+[A-Za-z0-9]+\s+(?:from)\s+[A-Za-z0-9]+\s+(?:to)\s+[A-Za-z0-9]+", pending_command, re.IGNORECASE) or re.search(r"bridge\s+\d+(?:\.\d+)?\s+[A-Za-z0-9]+\s+(?:to)\s+[A-Za-z0-9]+", pending_command, re.IGNORECASE) or re.search(r"bridge\s+\$\d+(?:\.\d+)?(?:\s+of|\s+worth\s+of)?\s+[A-Za-z0-9]+\s+(?:to)\s+[A-Za-z0-9]+", pending_command, re.IGNORECASE):
                logger.info("Processing pending bridge command")
                
                # Parse the bridge command
                bridge_command = self._parse_bridge_command(pending_command)
                
                # If from_chain_id is None, use the current chain_id
                if bridge_command.from_chain_id is None:
                    bridge_command.from_chain_id = chain_id
                    logger.info(f"Setting bridge source chain to user's current chain: {chain_id}")
                    
                # Get the transaction data from Brian API
                logger.info(f"Getting bridge transaction for {bridge_command.token}, amount {bridge_command.amount} from chain {bridge_command.from_chain_id} to {bridge_command.to_chain_id}")
                tx_data = await brian_service.get_bridge_transaction(
                    token_symbol=bridge_command.token,
                    amount=bridge_command.amount,
                    from_chain_id=bridge_command.from_chain_id,
                    to_chain_id=bridge_command.to_chain_id,
                    wallet_address=wallet_address
                )
                
                logger.info(f"Bridge transaction data: {json.dumps(tx_data, default=str)}")
                
                # We need to handle two cases here:
                # 1. If the token needs approval, the first step is the approval
                # 2. If the token doesn't need approval, or is already approved, we can use the bridge step
                
                # Check if we have quotes
                if "all_quotes" not in tx_data or not tx_data["all_quotes"]:
                    return AgentMessage(
                        error="No transaction quotes found in bridge data",
                        metadata={"command": pending_command}
                    ).model_dump()
                
                # Check if we need approval
                needs_approval = tx_data.get("needs_approval", False)
                
                # Select the appropriate transaction
                main_quote = None
                if needs_approval:
                    # Find approval step
                    for quote in tx_data["all_quotes"]:
                        if quote.get("is_approval"):
                            main_quote = quote
                            break
                
                # If no approval step found or not needed, use the first non-approval step
                if main_quote is None:
                    for quote in tx_data["all_quotes"]:
                        if not quote.get("is_approval"):
                            main_quote = quote
                            break
                
                # If still no quote found, use the first one
                if main_quote is None and tx_data["all_quotes"]:
                    main_quote = tx_data["all_quotes"][0]
                    
                if main_quote is None:
                    return AgentMessage(
                        error="No valid transaction found in bridge data",
                        metadata={}
                    ).model_dump()
                
                # Clear the pending command as it's being executed
                await self.redis_service.clear_pending_command(wallet_address)
                
                # Format the transaction for execution
                from_chain_name = self._get_chain_name(bridge_command.from_chain_id)
                to_chain_name = self._get_chain_name(bridge_command.to_chain_id)
                
                # Format message based on whether this is approval or execution
                message = (
                    f"Executing approval for bridging {bridge_command.amount} {bridge_command.token}" 
                    if main_quote.get("is_approval") 
                    else f"Executing bridge of {bridge_command.amount} {bridge_command.token} from {from_chain_name} to {to_chain_name}"
                )
                
                # Ensure gas limit is properly set - accept either "gas" or "gasLimit" field
                gas_limit = main_quote.get("gas", main_quote.get("gasLimit", "500000"))
                
                # Convert value to string if it's not already
                value = main_quote.get("value", "0")
                if not isinstance(value, str):
                    value = str(value)
                
                # Create the transaction data to be executed
                transaction_data = {
                    "to": main_quote["to"],
                    "data": main_quote["data"],
                    "value": value,
                    "chainId": int(bridge_command.from_chain_id),  # Ensure chainId is an integer
                    "gasLimit": gas_limit,
                    "method": "bridge"
                }
                
                # Enhance metadata with additional info
                metadata = {
                    "token_symbol": bridge_command.token,
                    "amount": bridge_command.amount, 
                    "from_chain_id": bridge_command.from_chain_id,
                    "to_chain_id": bridge_command.to_chain_id,
                    "from_chain_name": from_chain_name,
                    "to_chain_name": to_chain_name
                }
                
                logger.info(f"Final transaction for execution: {json.dumps(transaction_data, default=str)}")
                
                # Return with transaction data for immediate execution
                return {
                    "content": {
                        "type": "message",
                        "message": message,
                    },
                    "transaction": transaction_data,
                    "metadata": metadata,
                    "agent_type": "brian",
                    "is_brian_operation": True
                }
                
            # Check if it's a transfer command
            elif re.search(r"(?:send|transfer)\s+\d+(?:\.\d+)?\s+[A-Za-z0-9]+\s+(?:to)\s+[A-Za-z0-9\.]+", pending_command, re.IGNORECASE):
                logger.info("Processing pending transfer command")
                
                # Parse the transfer command
                transfer_command = self._parse_transfer_command(pending_command)
                
                # Get the transaction data from Brian API
                tx_data = await brian_service.get_transfer_transaction(
                    token_symbol=transfer_command.token,
                    amount=transfer_command.amount,
                    recipient_address=transfer_command.recipient,
                    wallet_address=wallet_address,
                    chain_id=chain_id
                )
                
                # Clear the pending command as it's being executed
                await self.redis_service.clear_pending_command(wallet_address)
                
                # Return with transaction data for immediate execution
                return {
                    "content": {
                        "type": "message",
                        "message": f"Executing transfer of {transfer_command.amount} {transfer_command.token} to {transfer_command.recipient}",
                    },
                    "transaction": {
                        "to": tx_data["to"],
                        "data": tx_data["data"],
                        "value": tx_data.get("value", "0"),
                        "chainId": chain_id,
                        "gasLimit": tx_data.get("gas", "300000"),
                        "method": "transfer"
                    },
                    "metadata": tx_data.get("metadata", {}),
                    "agent_type": "brian",
                    "is_brian_operation": True
                }
            
            # Check if it's a dollar amount transfer command
            elif re.search(r"(?:transfer|send)\s+\$\d+(?:\.\d+)?\s+(?:of|worth\s+of)\s+[A-Za-z0-9]+\s+(?:to)\s+[A-Za-z0-9\.]+", pending_command, re.IGNORECASE):
                logger.info("Processing pending dollar amount transfer command")
                
                # Process through the dollar transfer method
                result = await self.process_dollar_transfer_command(
                    command=pending_command,
                    chain_id=chain_id,
                    wallet_address=wallet_address
                )
                
                # Clear the pending command as it's being executed
                await self.redis_service.clear_pending_command(wallet_address)
                
                # If result contains transaction data, ensure it's in the right format for execution
                if "transaction" in result:
                    result["content"]["type"] = "message"
                    result["content"]["message"] = f"Executing transfer of {result['metadata']['amount']} {result['metadata']['token_symbol']} to {result['metadata']['recipient']}"
                
                return result
                
            # Not a recognized command type
            return AgentMessage(
                error=f"Pending command type not recognized: {pending_command}",
                metadata={"pending_command": pending_command}
            ).model_dump()
            
        except Exception as e:
            logger.error(f"Error processing Brian confirmation: {str(e)}", exc_info=True)
            return AgentMessage(
                error=f"Error processing confirmation: {str(e)}",
                metadata={}
            ).model_dump()
    
    def _parse_transfer_command(self, command: str) -> TransferCommand:
        """
        Parse a transfer command from natural language.
        
        Examples:
        - "send 10 USDC to 0x123..."
        - "transfer 0.1 ETH to papajams.eth"
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
    
    def _parse_bridge_command(self, command: str) -> BridgeCommand:
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
            # The actual chain_id will be passed from the process_bridge_command method
            from_chain = None  # Will be determined by the caller's current chain_id
            to_chain = dollar_of_match.group(3).lower()
        elif dollar_match:
            amount = float(dollar_match.group(1))
            token = dollar_match.group(2).upper()
            # For dollar formats, we'll use the current user's chain as the source
            from_chain = None  # Will be determined by the caller's current chain_id
            to_chain = dollar_match.group(3).lower()
        elif full_match:
            amount = float(full_match.group(1))
            token = full_match.group(2).upper()
            from_chain = full_match.group(3).lower()
            to_chain = full_match.group(4).lower()
        elif simple_match:
            amount = float(simple_match.group(1))
            token = simple_match.group(2).upper()
            # For the simple pattern, use the caller's current chain
            from_chain = None  # Will be determined by the caller's current chain_id
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
        
        # If from_chain is None, the calling function will set it based on user's current chain
        from_chain_id = chain_map.get(from_chain, None) if from_chain else None
        to_chain_id = chain_map.get(to_chain, 8453)  # Default to Base if destination not found
        
        return BridgeCommand(
            action="bridge",
            amount=amount,
            token=token,
            from_chain_id=from_chain_id,
            to_chain_id=to_chain_id,
            natural_command=command
        )
    
    def _parse_balance_command(self, command: str) -> BalanceCommand:
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
    
    def _get_chain_name(self, chain_id: int) -> str:
        """Get a human-readable chain name from a chain ID."""
        chain_names = {
            1: "Ethereum",
            10: "Optimism",
            56: "BNB Chain",
            137: "Polygon",
            42161: "Arbitrum",
            8453: "Base",
            534352: "Scroll",
            43114: "Avalanche"
        }
        return chain_names.get(chain_id, f"Chain {chain_id}")

    async def process_dollar_transfer_command(self, command: str, chain_id: int = 1, wallet_address: Optional[str] = None) -> Dict[str, Any]:
        """
        Process a dollar-based token transfer command (e.g., "send $10 of ETH to 0x123...")
        
        Args:
            command: The transfer command
            chain_id: The chain ID
            wallet_address: The sender's wallet address
            
        Returns:
            Dictionary with transaction data
        """
        try:
            # Parse the dollar transfer command
            dollar_amount, token_symbol, recipient = self._parse_dollar_transfer_command(command)
            
            # Look up token info
            token_service = self.token_service
            token_info = await token_service.lookup_token(token_symbol, chain_id)
            
            if not token_info or not token_info[0]:
                return AgentMessage(
                    error=f"Could not find token information for {token_symbol}",
                    metadata={"token": token_symbol}
                ).model_dump()
                
            # Extract token info
            token_address, token_symbol, token_name, token_metadata = token_info
            
            # Convert dollar amount to token amount
            token_amount = await self._convert_usd_to_token_amount(dollar_amount, token_symbol, chain_id)
            
            if token_amount is None:
                return AgentMessage(
                    error=f"Could not determine price for {token_symbol} to convert ${dollar_amount}",
                    metadata={"token": token_symbol, "dollar_amount": dollar_amount}
                ).model_dump()
            
            logger.info(f"Converted ${dollar_amount} to {token_amount} {token_symbol}")
            
            # Get the transaction data from Brian API
            tx_data = await brian_service.get_transfer_transaction(
                token_symbol=token_symbol,
                amount=token_amount,
                recipient_address=recipient,
                wallet_address=wallet_address,
                chain_id=chain_id
            )
            
            # Format the response for the frontend to execute
            transaction_data = {
                "to": tx_data["to"],
                "data": tx_data["data"],
                "value": tx_data.get("value", "0"),
                "chainId": chain_id,
                "gasLimit": tx_data.get("gas", "300000"),
                "method": "transfer"
            }
            
            return {
                "content": {
                    "type": "transaction",
                    "message": f"Ready to transfer {token_amount} {token_symbol} (${dollar_amount}) to {recipient}",
                    "transaction": transaction_data
                },
                "metadata": {
                    "token_symbol": token_symbol,
                    "token_name": token_name,
                    "token_address": token_address,
                    "amount": token_amount,
                    "dollar_amount": dollar_amount,
                    "recipient": recipient,
                    "chain_id": chain_id,
                    "chain_name": self._get_chain_name(chain_id)
                },
                "agent_type": "brian",
                "is_brian_operation": True,
                "awaitingConfirmation": True,
                "transaction": transaction_data
            }
            
        except Exception as e:
            logger.error(f"Error processing dollar transfer command: {str(e)}")
            return AgentMessage(
                error=f"Failed to process transfer command: {str(e)}",
                metadata={"command": command}
            ).model_dump()

    def _parse_dollar_transfer_command(self, command: str) -> Tuple[float, str, str]:
        """
        Parse a dollar-based transfer command from natural language.
        
        Examples:
        - "send $10 of USDC to 0x123..."
        - "transfer $0.1 of ETH to papajams.eth"
        
        Returns:
            Tuple of (dollar_amount, token_symbol, recipient)
        """
        # Pattern for dollar amount transfers
        pattern = r"(?:send|transfer)\s+\$(\d+(?:\.\d+)?)\s+(?:of|worth\s+of)\s+([A-Za-z0-9]+)\s+(?:to)\s+([A-Za-z0-9\.]+(?:\.[A-Za-z0-9]+)*)"
        match = re.search(pattern, command, re.IGNORECASE)
        
        if not match:
            raise ValueError("Invalid dollar transfer command format. Expected: 'send/transfer $[amount] of [token] to [recipient]'")
        
        dollar_amount = float(match.group(1))
        token_symbol = match.group(2).upper()
        recipient = match.group(3)
        
        return dollar_amount, token_symbol, recipient

    async def _convert_usd_to_token_amount(self, usd_amount: float, token_symbol: str, chain_id: int) -> Optional[float]:
        """
        Convert a USD amount to a token amount based on current price.
        
        Args:
            usd_amount: The amount in USD
            token_symbol: The token symbol
            chain_id: The chain ID
            
        Returns:
            The equivalent token amount, or None if conversion failed
        """
        try:
            # Get token info
            token_info = await self.token_service.lookup_token(token_symbol, chain_id)
            if not token_info or not token_info[0]:
                logger.error(f"Could not find token info for {token_symbol} on chain {chain_id}")
                return None
                
            token_address, token_symbol, token_name, _ = token_info
                
            # Get the token price
            token_price, _ = await get_token_price(token_symbol, token_address, chain_id)
            
            if not token_price or token_price <= 0:
                logger.error(f"Invalid price for {token_symbol}: {token_price}")
                return None
                
            # Calculate the token amount
            token_amount = usd_amount / token_price
            
            # Round to 6 decimal places for better display
            token_amount = round(token_amount, 6)
            
            return token_amount
            
        except Exception as e:
            logger.error(f"Error converting USD to token amount: {e}")
            return None 
"""
Agent for Brian API features including token transfers, cross-chain bridging, and balance checking.
"""
import logging
import re
from typing import Dict, Any, Optional, List, Union
from pydantic import BaseModel

from app.agents.base import PointlessAgent, AgentMessage
from app.services.brian_service import brian_service
from app.services.token_service import TokenService
from app.models.commands import TransferCommand, BridgeCommand, BalanceCommand

logger = logging.getLogger(__name__)

class BrianAgent(PointlessAgent):
    """Agent for Brian API features."""
    token_service: Optional[TokenService] = None
    
    def __init__(self, token_service: Optional[TokenService] = None, provider = None):
        """Initialize the Brian agent."""
        prompt = """You are a helpful assistant that processes Web3 commands using the Brian API.
        You can handle token transfers, cross-chain bridging, and balance checking.
        Extract the relevant information from user queries and format it for the Brian API."""
        
        super().__init__(
            prompt=prompt,
            model="gpt-4-turbo-preview",
            temperature=0.7,
            provider=provider
        )
        
        self.token_service = token_service or TokenService()
    
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
                "transaction": transaction_data
            }
            
        except Exception as e:
            logger.error(f"Error processing transfer command: {str(e)}")
            return AgentMessage(
                error=f"Failed to process transfer command: {str(e)}",
                metadata={"command": command}
            ).model_dump()
    
    async def process_bridge_command(self, command: str, chain_id: int = 1, wallet_address: Optional[str] = None) -> Dict[str, Any]:
        """
        Process a cross-chain bridge command.
        
        Args:
            command: The bridge command (e.g., "bridge 0.1 ETH from Scroll to Base")
            chain_id: The source chain ID
            wallet_address: The wallet address
            
        Returns:
            Dictionary with transaction data
        """
        try:
            # Parse the bridge command
            bridge_command = self._parse_bridge_command(command)
            
            # Get the token symbol
            token_symbol = bridge_command.token
            if isinstance(token_symbol, dict):
                token_symbol = token_symbol.get("symbol", "")
            
            # Look up token info
            token_info = await self.token_service.lookup_token(token_symbol, bridge_command.from_chain_id)
            if not token_info or not token_info[0]:
                return AgentMessage(
                    error=f"Could not find token information for {token_symbol} on {self._get_chain_name(bridge_command.from_chain_id)}",
                    metadata={"token": token_symbol}
                ).model_dump()
            
            # Extract token info
            token_address, token_symbol, token_name, token_metadata = token_info
            
            # Get the transaction data from Brian API
            tx_data = await brian_service.get_bridge_transaction(
                token_symbol=token_symbol,
                amount=bridge_command.amount,
                from_chain_id=bridge_command.from_chain_id,
                to_chain_id=bridge_command.to_chain_id,
                wallet_address=wallet_address
            )
            
            # Format the response
            from_chain_name = self._get_chain_name(bridge_command.from_chain_id)
            to_chain_name = self._get_chain_name(bridge_command.to_chain_id)
            
            # Check if approval is needed
            needs_approval = tx_data.get("needs_approval", False)
            approval_message = ""
            if needs_approval:
                approval_message = f"\n\nThis will require two transactions:\n1. First to approve {token_symbol} spending\n2. Then to execute the bridge"
            
            # Get the first transaction to execute (either approval or bridge)
            first_tx = None
            if "all_quotes" in tx_data and tx_data["all_quotes"]:
                first_tx = tx_data["all_quotes"][0]
            
            if not first_tx:
                return AgentMessage(
                    error=f"No valid transaction data found for bridging {token_symbol}",
                    metadata={"token": token_symbol}
                ).model_dump()
            
            # Format the transaction for the frontend
            return {
                "content": {
                    "type": "transaction",
                    "message": f"Ready to bridge {bridge_command.amount} {token_symbol} from {from_chain_name} to {to_chain_name}.{approval_message}",
                    "transaction": {
                        "to": first_tx["to"],
                        "data": first_tx["data"],
                        "value": first_tx.get("value", "0"),
                        "chainId": bridge_command.from_chain_id,
                        "gasLimit": first_tx.get("gas", "500000"),
                        "method": "bridge"
                    }
                },
                "metadata": {
                    "token_symbol": token_symbol,
                    "token_name": token_name,
                    "token_address": token_address,
                    "amount": bridge_command.amount,
                    "from_chain_id": bridge_command.from_chain_id,
                    "to_chain_id": bridge_command.to_chain_id,
                    "from_chain_name": from_chain_name,
                    "to_chain_name": to_chain_name,
                    "needs_approval": needs_approval,
                    "all_quotes": tx_data.get("all_quotes", []),
                    "token_to_approve": tx_data.get("token_to_approve"),
                    "spender": tx_data.get("spender")
                },
                "agent_type": "brian",
                "transaction": {
                    "to": first_tx["to"],
                    "data": first_tx["data"],
                    "value": first_tx.get("value", "0"),
                    "chainId": bridge_command.from_chain_id,
                    "gasLimit": first_tx.get("gas", "500000"),
                    "method": "bridge"
                }
            }
            
        except Exception as e:
            logger.error(f"Error processing bridge command: {str(e)}")
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
            # Personalize the response with the user's name if available
            name_prefix = f"{user_name}'s" if user_name and user_name != "User" else "Your"
            
            # Check if this is a transfer command
            if re.search(r"(?:send|transfer)\s+\d+(?:\.\d+)?\s+[A-Za-z0-9]+\s+(?:to)\s+[A-Za-z0-9\.]+", command, re.IGNORECASE):
                result = await self.process_transfer_command(command, chain_id, wallet_address)
                
                # Personalize the message if we have a user name
                if user_name and user_name != "User" and "content" in result and isinstance(result["content"], dict):
                    result["content"]["message"] = result["content"]["message"].replace("Ready to transfer", f"Ready to transfer {name_prefix}")
                
                return result
            
            # Check if this is a bridge command
            elif re.search(r"bridge\s+\d+(?:\.\d+)?\s+[A-Za-z0-9]+\s+(?:from)\s+[A-Za-z0-9]+\s+(?:to)\s+[A-Za-z0-9]+", command, re.IGNORECASE):
                result = await self.process_bridge_command(command, chain_id, wallet_address)
                
                # Personalize the message if we have a user name
                if user_name and user_name != "User" and "content" in result and isinstance(result["content"], dict):
                    result["content"]["message"] = result["content"]["message"].replace("Ready to bridge", f"Ready to bridge {name_prefix}")
                
                return result
            
            # Check if this is a balance command
            elif re.search(r"(?:check|show|what'?s|get)\s+(?:my|the)\s+(?:[A-Za-z0-9]+\s+)?balance", command, re.IGNORECASE):
                result = await self.process_balance_command(command, chain_id, wallet_address)
                
                # Personalize the message if we have a user name
                if user_name and user_name != "User" and "content" in result and isinstance(result["content"], str):
                    result["content"] = result["content"].replace("Your balance", f"{name_prefix} balance")
                
                return result
            
            # If not a recognized command, return an error
            return AgentMessage(
                error="Not a recognized Brian API command. Please try a transfer, bridge, or balance command.",
                metadata={"command": command}
            ).model_dump()
            
        except Exception as e:
            logger.error(f"Error processing Brian command: {str(e)}")
            return AgentMessage(
                error=f"Failed to process Brian command: {str(e)}",
                metadata={"command": command}
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
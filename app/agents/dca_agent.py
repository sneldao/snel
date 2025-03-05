import re
import logging
from typing import Dict, Any, List, Optional, Tuple, Union
from pydantic import BaseModel, Field
from datetime import datetime, timedelta

from app.agents.base import PointlessAgent
from app.services.token_service import TokenService
from app.services.redis_service import RedisService

logger = logging.getLogger(__name__)

class DCAResponse:
    """
    Helper class to parse and format DCA commands.
    """
    
    @staticmethod
    def parse_command(command: str) -> Dict[str, Any]:
        """
        Parse a DCA command string into its components.
        
        Args:
            command: The command string
            
        Returns:
            Dictionary with parsed values
        """
        try:
            # Clean and normalize the command
            command = command.lower().strip()

            # Remove any prefixes
            for prefix in ["dca ", "dollar cost average ", "please ", "can you ", "set up ", "setup "]:
                if command.startswith(prefix):
                    command = command[len(prefix):]
            
            # Check for dollar sign format: "$5 of eth into usdc for 2 days"
            dollar_match = re.search(r"\$([0-9.]+)\s+(?:of\s+)?([a-z0-9]+)\s+(?:into|for|to)\s+([a-z0-9]+)(?:\s+(?:for|over)\s+(\d+)\s+days)?", command)
            if dollar_match:
                amount = float(dollar_match.group(1))
                token_in = dollar_match.group(2).upper()
                token_out = dollar_match.group(3).upper()
                duration = int(dollar_match.group(4)) if dollar_match.group(4) else 30
                
                return {
                    "amount": amount,
                    "token_in": token_in,
                    "token_out": token_out,
                    "frequency": "daily",
                    "duration": duration,
                    "amount_is_usd": True
                }

            # Check for standard pattern
            m = re.search(r"([0-9.]+)\s+([a-z0-9]+)(?:\s+(?:per|a|every|each)\s+(?:day|week|month))?(?:\s+(?:for|over)\s+(\d+)\s+days)?\s+(?:into|for|to)\s+([a-z0-9]+)(?:\s+(?:for|over)\s+(\d+)\s+days)?", command)

            if not m:
                return {"error": "Invalid DCA format. Please use 'dca [amount] [token] per [day/week/month] into [token]' or 'dca $[amount] of [token] into [token] for [days] days'."}

            amount = float(m.group(1))
            token_in = m.group(2).upper()
            token_out = m.group(4).upper()  # Group 4 because group 3 might be the duration
            
            # Check for duration in two possible positions
            duration = None
            if m.group(3):  # Duration before "into"
                duration = int(m.group(3))
            elif m.group(5):  # Duration after "into"
                duration = int(m.group(5))
            
            # Default to 30 days if no duration specified
            if duration is None:
                duration = 30

            # Also check for duration in the full command
            if duration == 30:  # Only if we're still using the default
                duration_match = re.search(r"(?:for|over)\s+(\d+)\s+days", command)
                if duration_match:
                    duration = int(duration_match.group(1))

            # Check if frequency is specified
            freq_match = re.search(r"(?:per|a|every|each)\s+(day|week|month)", command)
            frequency = freq_match.group(1) if freq_match else "day"
            # Convert frequency to proper format
            if frequency == "day":
                frequency = "daily"
            elif frequency == "week":
                frequency = "weekly"
            elif frequency == "month":
                frequency = "monthly"

            return {
                "amount": amount,
                "token_in": token_in,
                "token_out": token_out,
                "frequency": frequency,
                "duration": duration,
                "amount_is_usd": "$" in command
            }

        except Exception as e:
            logger.error(f"Error parsing DCA command: {e}")
            return {"error": f"Failed to parse DCA command: {str(e)}"}
    
    @staticmethod
    def format_response(parsed: Dict[str, Any], token_in_info: Dict[str, Any], token_out_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Format a response for a parsed DCA command.
        
        Args:
            parsed: The parsed command
            token_in_info: Information about the input token
            token_out_info: Information about the output token
            
        Returns:
            Formatted response
        """
        # Calculate the end date
        end_date = (datetime.now() + timedelta(days=parsed["duration"])).strftime("%-d %B %Y")
        
        # Format response
        return {
            "type": "dca_confirmation",
            "message": f"I'll set up a Dollar Cost Average (DCA) order to swap {parsed['amount']} {parsed['token_in']} for {parsed['token_out']} every {parsed['frequency'].replace('ly', '')} for {parsed['duration']} days.\n\nDCA (Dollar Cost Averaging) helps reduce the impact of volatility by spreading out your purchases over time.\n\nYour order will run until {end_date}.",
            "from_token": {
                "symbol": token_in_info["symbol"],
                "name": token_in_info.get("name", token_in_info["symbol"]),
                "address": token_in_info["address"],
                "verified": True,
                "source": token_in_info.get("source", "unknown")
            },
            "to_token": {
                "symbol": token_out_info["symbol"],
                "name": token_out_info.get("name", token_out_info["symbol"]),
                "address": token_out_info["address"],
                "verified": True,
                "source": token_out_info.get("source", "unknown")
            },
            "amount": parsed["amount"],
            "frequency": parsed["frequency"],
            "duration": parsed["duration"],
            "warning": "Important: Please note that the DCA API is in beta. Always monitor your DCA orders regularly."
        }

class DCAAgent(PointlessAgent):
    """
    Agent for handling DCA commands.
    """
    token_service: Optional[TokenService] = None
    redis_service: Optional[RedisService] = None
    dca_service: Any = None  # Add this field to avoid the error
    
    def __init__(self, token_service: Optional[TokenService] = None, redis_service: Optional[RedisService] = None):
        super().__init__(
            prompt="You are a DCA (Dollar Cost Average) Agent that helps users set up recurring cryptocurrency purchases.",
            model="gpt-4-turbo-preview"
        )
        self.token_service = token_service
        self.redis_service = redis_service
        logger.info("DCA Agent initialized")
    
    async def _lookup_token(self, symbol: str, chain_id: int) -> Optional[Dict[str, Any]]:
        """
        Look up a token by symbol.
        
        Args:
            symbol: The token symbol
            chain_id: The chain ID
            
        Returns:
            Token information if found
        """
        if not self.token_service:
            return None
            
        logger.info(f"Looking up token: {symbol}")
        try:
            result = await self.token_service.lookup_token(symbol, chain_id)
            
            if not result:
                return None
                
            # Handle different return formats
            if isinstance(result, tuple):
                if len(result) == 3:
                    address, symbol, name = result
                    return {
                        "address": address,
                        "symbol": symbol,
                        "name": name,
                        "source": "openocean"
                    }
                elif len(result) == 4:
                    address, symbol, name, metadata = result
                    return {
                        "address": address,
                        "symbol": symbol,
                        "name": name,
                        "source": metadata.get("source", "openocean"),
                        "verified": metadata.get("verified", True)
                    }
            
            # If result is already a dictionary
            if isinstance(result, dict):
                return result
            
            # Fallback
            logger.warning(f"Unexpected token lookup result format: {type(result)}")
            return None
            
        except Exception as e:
            logger.error(f"Error looking up token {symbol}: {e}")
            return None
    
    async def _store_dca_state(self, wallet_address: str, chain_id: int, parsed_command: Dict[str, Any]) -> bool:
        """
        Store DCA state in Redis.
        
        Args:
            wallet_address: The user's wallet address
            chain_id: The blockchain chain ID
            parsed_command: The parsed DCA command
            
        Returns:
            True if successful, False otherwise
        """
        if not self.redis_service:
            logger.warning("Redis service not available for storing DCA state")
            return False
            
        try:
            key = f"dca_state:{wallet_address}"
            state = {
                "wallet_address": wallet_address,
                "chain_id": chain_id,
                "token_in": parsed_command["token_in"],
                "token_out": parsed_command["token_out"],
                "amount": parsed_command["amount"],
                "frequency": parsed_command["frequency"],
                "duration": parsed_command["duration"],
                "timestamp": datetime.now().isoformat()
            }
            
            await self.redis_service.set(key, state, expire=300)  # 5 minutes expiration
            return True
        except Exception as e:
            logger.error(f"Error storing DCA state: {e}")
            return False
    
    async def _get_dca_state(self, wallet_address: str) -> Optional[Dict[str, Any]]:
        """
        Get DCA state from Redis.
        
        Args:
            wallet_address: The user's wallet address
            
        Returns:
            DCA state if found, None otherwise
        """
        if not self.redis_service:
            logger.warning("Redis service not available for getting DCA state")
            return None
            
        try:
            key = f"dca_state:{wallet_address}"
            return await self.redis_service.get(key)
        except Exception as e:
            logger.error(f"Error getting DCA state: {e}")
            return None
    
    async def _clear_dca_state(self, wallet_address: str) -> bool:
        """
        Clear DCA state from Redis.
        
        Args:
            wallet_address: The user's wallet address
            
        Returns:
            True if successful, False otherwise
        """
        if not self.redis_service:
            logger.warning("Redis service not available for clearing DCA state")
            return False
            
        try:
            key = f"dca_state:{wallet_address}"
            await self.redis_service.delete(key)
            return True
        except Exception as e:
            logger.error(f"Error clearing DCA state: {e}")
            return False
    
    async def parse_dca_command(self, command: str) -> Dict[str, Any]:
        """
        Parse a DCA command string into its components.
        
        Args:
            command: The command string
            
        Returns:
            Dictionary with parsed values
        """
        return DCAResponse.parse_command(command)
        
    async def process_dca_command(self, command: str, chain_id: Optional[int] = None, wallet_address: Optional[str] = None) -> Dict[str, Any]:
        """
        Process a DCA command.
        
        Args:
            command: The command string
            chain_id: The blockchain chain ID
            wallet_address: The user's wallet address
            
        Returns:
            Response dictionary
        """
        try:
            # Parse the command
            parsed = await self.parse_dca_command(command)
            if "error" in parsed:
                return {"error": parsed["error"]}
                
            # Check if wallet address is provided
            if not wallet_address:
                return {"error": "Wallet address is required for DCA commands"}
                
            # Look up tokens
            token_in_info = await self._lookup_token(parsed["token_in"], chain_id or 1)
            if not token_in_info:
                return {"error": f"Could not find token {parsed['token_in']}"}
                
            token_out_info = await self._lookup_token(parsed["token_out"], chain_id or 1)
            if not token_out_info:
                return {"error": f"Could not find token {parsed['token_out']}"}
                
            # Store DCA state
            await self._store_dca_state(wallet_address, chain_id or 1, parsed)
                
            # Format response
            response = DCAResponse.format_response(parsed, token_in_info, token_out_info)
            
            return {
                "content": response,
                "metadata": {
                    "command": command,
                    "chain_id": chain_id or 1,
                    "wallet_address": wallet_address,
                    "token_in_info": token_in_info,
                    "token_out_info": token_out_info,
                    "dca_details": parsed
                }
            }
            
        except Exception as e:
            logger.error(f"Error processing DCA command: {e}")
            return {"error": f"Failed to process DCA command: {str(e)}"} 
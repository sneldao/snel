import re
import logging
from typing import Dict, Any, List, Optional, Tuple, Union
from pydantic import BaseModel, Field
from datetime import datetime, timedelta

from app.agents.base import PointlessAgent
from app.services.token_service import TokenService

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

            # Now parse the components
            # Format: "[amount] [token_in] [frequency] into [token_out]"

            # Check for basic pattern - improved to handle different formats
            m = re.search(r"([0-9.]+)\s+([a-z0-9]+)(?:\s+(?:per|a|every|each)\s+(?:day|week|month))?(?:\s+for\s+\d+\s+days)?\s+(?:into|for|to)\s+([a-z0-9]+)", command)

            if not m:
                return {"error": "Invalid DCA format. Please use 'dca [amount] [token] per [day/week/month] into [token]'."}

            amount = float(m.group(1))
            token_in = m.group(2).upper()
            token_out = m.group(3).upper()

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

            duration_match = re.search(r"for\s+(\d+)\s+days", command)
            duration = int(duration_match.group(1)) if duration_match else 30
            return {
                "amount": amount,
                "token_in": token_in,
                "token_out": token_out,
                "frequency": frequency,
                "duration": duration  # Now correctly parsed from command
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
            "warning": "Important: Please note that the OpenOcean DCA API is in beta. Always monitor your DCA orders regularly."
        }

class DCAAgent(PointlessAgent):
    """
    Agent for handling DCA commands.
    """
    token_service: Optional[TokenService] = None
    pending_commands: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    dca_service: Optional[TokenService] = None
    
    def __init__(self, token_service: Optional[TokenService] = None):
        super().__init__(
            prompt="You are a DCA (Dollar Cost Average) Agent that helps users set up recurring cryptocurrency purchases.",
            model="gpt-4-turbo-preview"
        )
        self.token_service = token_service
        self.dca_service = None  # Will be set after initialization to avoid circular imports
        self.pending_commands = {}  # Store parsed commands for confirmation
    
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
            
        logger.info(f"Looking up token_in: {symbol}")
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
    
    async def process_dca_command(
        self,
        command: str,
        chain_id: int = 1,
        wallet_address: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process a DCA command.
        
        Args:
            command: The DCA command to process
            chain_id: The blockchain chain ID
            wallet_address: The user's wallet address
            
        Returns:
            A dictionary with the DCA confirmation or error details
        """
        logger.info(f"Processing DCA command: {command}")

        try:
            # Check if this is a confirmation command (e.g., "yes", "confirm")
            if command.lower() in {
                "yes",
                "confirm",
                "proceed",
                "continue",
                "ok",
                "okay",
                "sure",
                "y",
            }:
                if not wallet_address:
                    return {
                        "type": "error",
                        "content": "Wallet address is required for DCA confirmation."
                    }

                # Check if there's a pending command for this wallet
                pending_key = f"dca:{wallet_address}:{chain_id}"
                if pending_key not in self.pending_commands:
                    return {
                        "type": "error",
                        "content": "No pending DCA order found. Please enter a new DCA command."
                    }

                # Get the previously parsed command
                parsed_command = self.pending_commands[pending_key]

                # Create the DCA order
                if not self.dca_service:
                    return {
                        "type": "error",
                        "content": "DCA service not initialized."
                    }

                try:
                    # Create the DCA order with OpenOcean API
                    result = await self.dca_service.create_dca_order(
                        wallet_address=wallet_address,
                        chain_id=chain_id,
                        token_in=parsed_command["token_in"],
                        token_out=parsed_command["token_out"],
                        amount=parsed_command["amount"],
                        frequency=parsed_command["frequency"],
                        duration=parsed_command["duration"]
                    )

                    if not result.get("success"):
                        return {
                            "type": "error",
                            "content": f"Failed to create DCA order: {result.get('error', 'Unknown error')}",
                            "status": "error"
                        }

                    # Clean up the pending command
                    del self.pending_commands[pending_key]

                    # Return a success response with the transaction
                    return {
                        "type": "dca_order_created",
                        "content": "I've initiated your DCA order! You'll be swapping the specified amount on your chosen schedule. You can monitor your DCA positions through your wallet's activity.",
                        "status": "success",
                        "metadata": {
                            "order_id": result.get("order_id"),
                            "details": result.get("details"),
                            **result.get("transaction", {})
                        }
                    }

                except Exception as e:
                    logger.error(f"Error creating DCA order: {e}")
                    return {
                        "type": "error",
                        "content": f"Failed to create DCA order: {str(e)}",
                        "status": "error"
                    }

            # If not a confirmation, parse the command as a new DCA request
            try:
                # Initialize token service if not already done
                if not self.token_service and wallet_address:
                    from app.services.token_service import TokenService
                    self.token_service = TokenService()

                # Parse the DCA command
                try:
                    parsed = DCAResponse.parse_command(command)
                    if not parsed:
                        return {
                            "type": "error",
                            "content": "Sorry, I couldn't understand your DCA command. Please use format like 'dca 1 ETH into BTC daily for 30 days'.",
                            "status": "error"
                        }

                    # Check if there's an error in the parsed command
                    if isinstance(parsed, dict) and "error" in parsed:
                        return {
                            "type": "error",
                            "content": parsed["error"],
                            "status": "error"
                        }

                    logger.info(f"Parsed DCA command: {parsed}")
                except Exception as parse_error:
                    logger.error(f"Error parsing DCA command: {parse_error}")
                    return {
                        "type": "error",
                        "content": f"Failed to parse your DCA command: {str(parse_error)}. Please try the format 'dca 1 ETH into BTC daily for 30 days'.",
                        "status": "error"
                    }

                if not wallet_address:
                    return {
                        "type": "error",
                        "content": "Wallet address is required for DCA setup.",
                        "status": "error"
                    }

                # Lookup token information
                token_in_info = await self._lookup_token(parsed["token_in"], chain_id)
                if not token_in_info:
                    return {
                        "type": "error",
                        "content": f"Sorry, I couldn't find the token {parsed['token_in']}.",
                        "status": "error"
                    }

                token_out_info = await self._lookup_token(parsed["token_out"], chain_id)
                if not token_out_info:
                    return {
                        "type": "error",
                        "content": f"Sorry, I couldn't find the token {parsed['token_out']}.",
                        "status": "error"
                    }

                # Format response for confirmation
                try:
                    response_data = DCAResponse.format_response(parsed, token_in_info, token_out_info)

                    # Store the command for confirmation
                    self.pending_commands[f"dca:{wallet_address}:{chain_id}"] = {
                        "token_in": token_in_info,
                        "token_out": token_out_info,
                        "amount": parsed["amount"],
                        "frequency": parsed["frequency"],
                        "duration": parsed["duration"]
                    }

                    # Return confirmation message
                    return response_data
                except Exception as format_error:
                    logger.error(f"Error formatting DCA response: {format_error}")
                    return {
                        "type": "error",
                        "content": f"Failed to format DCA response: {str(format_error)}",
                        "status": "error"
                    }

            except Exception as e:
                logger.error(f"Error processing DCA command: {e}")
                return {
                    "type": "error",
                    "content": f"Sorry, I encountered an error processing your DCA command: {str(e)}",
                    "status": "error"
                }

        except Exception as e:
            logger.error(f"Unexpected error in DCA agent: {e}")
            return {
                "type": "error",
                "content": f"An unexpected error occurred: {str(e)}",
                "status": "error"
            } 
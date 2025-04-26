from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Dict, Any, List, Callable, Awaitable, Optional
import logging
import re
from functools import wraps
from decimal import Decimal

# Import handlers for processing agent commands
from app.services.swap_service import fetch_swap_quote, build_swap_transaction
from app.agents.bridge_agent import process_bridge_command
from app.agents.balance_agent import process_balance_command
from app.agents.price_agent import process_price_command
from app.agents.transfer_agent import process_transfer_command
from app.agents.chat_agent import process_chat_command

# Set up logging
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/agent", tags=["agent"])

class AgentCommand(BaseModel):
    input: str
    wallet_address: str
    chain_id: int

class CommandHandler:
    """Base class for command handlers with pattern matching"""
    def __init__(self, patterns: List[str], handler_func: Callable[[AgentCommand], Awaitable[Dict[str, Any]]]):
        self.patterns = [re.compile(pattern, re.IGNORECASE) for pattern in patterns]
        self.handler_func = handler_func
    
    def matches(self, text: str) -> bool:
        """Check if any pattern matches the input text"""
        return any(pattern.search(text) for pattern in self.patterns)
    
    async def handle(self, cmd: AgentCommand) -> Dict[str, Any]:
        """Execute the handler function"""
        return await self.handler_func(cmd)

class AgentDispatcher:
    """Manages command handlers and dispatches commands"""
    def __init__(self):
        self.handlers: List[CommandHandler] = []
        self.fallback_handler: Optional[CommandHandler] = None
    
    def register_handler(self, patterns: List[str], handler_func: Callable[[AgentCommand], Awaitable[Dict[str, Any]]]):
        """Register a new command handler"""
        self.handlers.append(CommandHandler(patterns, handler_func))
        return handler_func  # Allow use as decorator
    
    def register_fallback(self, handler_func: Callable[[AgentCommand], Awaitable[Dict[str, Any]]]):
        """Register a fallback handler for when no patterns match"""
        self.fallback_handler = CommandHandler([".*"], handler_func)
        return handler_func  # Allow use as decorator
    
    async def dispatch(self, cmd: AgentCommand) -> Dict[str, Any]:
        """Find and execute the appropriate handler for a command"""
        cleaned_input = cmd.input.strip()
        
        # Try all registered handlers
        for handler in self.handlers:
            if handler.matches(cleaned_input):
                try:
                    return await handler.handle(cmd)
                except Exception as e:
                    logger.exception(f"Error in command handler: {str(e)}")
                    raise HTTPException(status_code=400, detail=f"Error processing command: {str(e)}")
        
        # Fall back to default handler if no matches
        if self.fallback_handler:
            try:
                return await self.fallback_handler.handle(cmd)
            except Exception as e:
                logger.exception(f"Error in fallback handler: {str(e)}")
                raise HTTPException(status_code=400, detail=f"Error processing command: {str(e)}")
        
        # No fallback registered
        raise HTTPException(status_code=400, detail="No handler found for command")

# Create the dispatcher instance
dispatcher = AgentDispatcher()

# Register handlers with their patterns and real handler functions
@dispatcher.register_handler(["swap", "exchange", "trade"])
async def handle_swap(cmd: AgentCommand) -> Dict[str, Any]:
    # Parse the swap command using regex
    m = re.match(r"swap\s+([\d\.]+)\s+(\S+)\s+to\s+(\S+)", cmd.input, re.IGNORECASE)
    if not m:
        return {"type": "error", "message": "Agent: Could not parse swap command. Try 'swap 1 ETH to USDC'."}
    
    amount, token_in, token_out = m.groups()
    try:
        quote = await fetch_swap_quote(from_token=token_in, to_token=token_out, amount=Decimal(amount), chain_id=cmd.chain_id)
        tx_data = await build_swap_transaction(quote, cmd.chain_id)
        return {
            "type": "swap_transaction",
            "quote": quote,
            "transaction": tx_data,
            "agent_hint": "You can now execute this swap, or ask to chain another action."
        }
    except Exception as e:
        return {"type": "error", "message": f"Swap failed: {str(e)}"}

@dispatcher.register_handler(["bridge", "transfer to", "send to .* chain"])
async def handle_bridge(cmd: AgentCommand) -> Dict[str, Any]:
    return await process_bridge_command(cmd)

@dispatcher.register_handler(["balance", "how much", "show my"])
async def handle_balance(cmd: AgentCommand) -> Dict[str, Any]:
    return await process_balance_command(cmd)

@dispatcher.register_handler(["price", "worth", "value"])
async def handle_price(cmd: AgentCommand) -> Dict[str, Any]:
    return await process_price_command(cmd)

@dispatcher.register_handler(["transfer", "send", "pay"])
async def handle_transfer(cmd: AgentCommand) -> Dict[str, Any]:
    return await process_transfer_command(cmd)

@dispatcher.register_fallback
async def handle_chat(cmd: AgentCommand) -> Dict[str, Any]:
    return await process_chat_command(cmd)


@router.post("/process")
async def process_agent_command(cmd: AgentCommand) -> Dict[str, Any]:
    """Main endpoint that dispatches user commands to appropriate handlers"""
    try:
        return await dispatcher.dispatch(cmd)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Unexpected error processing command: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

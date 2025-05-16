"""
Chat command processing endpoints.
"""
import os
import re
from openai import OpenAI
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any, Union
from decimal import Decimal
from app.services.brian.client import brian_client

router = APIRouter(prefix="/chat", tags=["chat"])

class ChatCommand(BaseModel):
    """Chat command request model."""
    command: str
    wallet_address: Optional[str] = None
    chain_id: Optional[int] = None
    user_name: Optional[str] = None
    openai_api_key: Optional[str] = None  # Accept user-supplied key

class ChatResponse(BaseModel):
    """Chat command response model."""
    content: Union[str, Dict[str, Any]]
    agent_type: Optional[str] = "default"
    metadata: Optional[Dict[str, Any]] = None
    awaiting_confirmation: Optional[bool] = False
    status: Optional[str] = "success"
    error: Optional[str] = None
    transaction: Optional[Dict[str, Any]] = None

@router.post("/process-command")
async def process_command(command: ChatCommand):
    """Process a chat command using OpenAI's GPT model."""
    try:
        # Prefer user-supplied key, fallback to env
        OPENAI_API_KEY = command.openai_api_key or os.getenv("OPENAI_API_KEY")
        if not OPENAI_API_KEY:
            return ChatResponse(
                content="No OpenAI API key configured. Please add your API key in the settings.",
                status="error",
                error="No OpenAI API key configured."
            )

        # Check for greeting messages
        greeting_responses = {
            "gm": "Good morning! How can I help you with crypto today?",
            "good morning": "Good morning! How can I help you with crypto today?",
            "hello": "Hello there! How can I assist you with crypto today?",
            "hi": "Hi! How can I help you with crypto today?",
            "hey": "Hey there! How can I assist you with crypto today?",
            "howdy": "Howdy! How can I help you with crypto today?",
            "sup": "Sup! How can I assist you with crypto today?",
            "yo": "Yo! How can I help you with crypto today?"
        }

        # Check if the command is a greeting
        cmd_lower = command.command.lower().strip()
        if cmd_lower in greeting_responses:
            return ChatResponse(
                content=greeting_responses[cmd_lower],
                agent_type="default",
                status="success"
            )

        # Check if this is a swap command
        swap_match = re.match(r"swap\s+([\d\.]+)\s+(\S+)\s+(to|for)\s+(\S+)", command.command, re.IGNORECASE)
        if swap_match:
            amount, from_token, _, to_token = swap_match.groups()

            # Check if this is Scroll chain (chain ID 534352)
            is_scroll_chain = command.chain_id == 534352

            # For Scroll chain, use Brian API directly
            if is_scroll_chain and command.wallet_address:
                try:
                    # Get swap transaction from Brian API
                    swap_data = await brian_client.get_swap_transaction(
                        from_token=from_token,
                        to_token=to_token,
                        amount=Decimal(amount),
                        chain_id=command.chain_id,
                        wallet_address=command.wallet_address
                    )

                    # Return transaction data for the frontend to execute
                    return ChatResponse(
                        content={
                            "type": "brian_confirmation",
                            "message": f"Ready to swap {amount} {from_token} to {to_token} on Scroll using Brian API",
                            "data": swap_data
                        },
                        agent_type="brian",
                        awaiting_confirmation=True,
                        transaction=swap_data.get("transaction"),
                        status="success"
                    )
                except Exception as e:
                    # If Brian API fails, suggest using the swap command
                    return ChatResponse(
                        content=f"I couldn't process your swap directly. Please try using the 'swap' command instead. Error: {str(e)}",
                        agent_type="default",
                        status="error"
                    )

            # For other chains, suggest using the swap command
            return ChatResponse(
                content=f"To swap {amount} {from_token} for {to_token}, please use the swap command directly by typing 'swap {amount} {from_token} for {to_token}'.",
                agent_type="default",
                status="success"
            )

        # For other commands, use OpenAI
        client = OpenAI(api_key=OPENAI_API_KEY)

        # Prepare context based on user info
        context = ""
        if command.wallet_address:
            context += f"User wallet: {command.wallet_address}\n"
        if command.chain_id:
            context += f"Current chain ID: {command.chain_id}\n"
        if command.user_name:
            context += f"User name: {command.user_name}\n"

        # Call OpenAI's API with the updated client
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are SNEL, a helpful crypto assistant. Provide concise, accurate information about cryptocurrencies, tokens, and blockchain technology."},
                {"role": "user", "content": f"{context}\nUser query: {command.command}"}
            ]
        )
        answer = response.choices[0].message.content

        return ChatResponse(
            content=answer,
            agent_type="default",
            status="success"
        )
    except Exception as e:
        return ChatResponse(
            content=f"Sorry, I encountered an error: {str(e)}",
            status="error",
            error=str(e)
        )

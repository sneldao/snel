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
from app.services.chat_history import chat_history_service
from app.api.v1.swap import process_swap_command, SwapCommand
import logging

router = APIRouter(prefix="/chat", tags=["chat"])

logger = logging.getLogger(__name__)

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
        # Check if this is a swap confirmation
        if command.command.lower().strip() == "yes":
            # Forward to swap endpoint
            try:
                swap_response = await process_swap_command(SwapCommand(
                    command=command.command,
                    wallet_address=command.wallet_address,
                    chain_id=command.chain_id
                ))
                
                # Check for errors in swap response
                if "error" in swap_response:
                    return ChatResponse(
                        content=swap_response["error"],
                        agent_type="swap",
                        awaiting_confirmation=False,
                        status="error",
                        metadata={
                            "technical_details": swap_response.get("technical_details", "Unknown error")
                        }
                    )
                
                response = ChatResponse(
                    content=swap_response["content"],
                    agent_type="swap",
                    awaiting_confirmation=False,
                    status="success",
                    metadata=swap_response.get("metadata")
                )
                
                chat_history_service.add_entry(
                    command.wallet_address,
                    command.user_name,
                    'swap',
                    command.command,
                    response.dict()
                )
                return response
                
            except Exception as e:
                # Log the technical error
                logger.exception("Error processing swap confirmation")
                return ChatResponse(
                    content="I encountered an issue while processing your swap. Please try again.",
                    agent_type="swap",
                    status="error",
                    metadata={"technical_details": str(e)}
                )

        # Prefer user-supplied key, fallback to env
        OPENAI_API_KEY = command.openai_api_key or os.getenv("OPENAI_API_KEY")
        if not OPENAI_API_KEY:
            return ChatResponse(
                content="I need an OpenAI API key to help you. Please add your API key in the settings.",
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
        if cmd_lower in greeting_responses and chat_history_service.should_respond_to_greeting(
            command.wallet_address, command.user_name, cmd_lower
        ):
            response = ChatResponse(
                content=greeting_responses[cmd_lower],
                agent_type="default",
                status="success"
            )
            chat_history_service.add_entry(
                command.wallet_address,
                command.user_name,
                'greeting',
                cmd_lower,
                response.dict()
            )
            return response

        # Check for swap command
        swap_match = re.match(r"swap\s+([\d\.]+)\s+(\S+)\s+(to|for)\s+(\S+)", command.command, re.IGNORECASE)
        if swap_match:
            # If no wallet address, return error
            if not command.wallet_address:
                return ChatResponse(
                    content="Please connect your wallet to perform swaps.",
                    agent_type="swap",
                    status="error"
                )
            
            # If no chain ID, return error
            if not command.chain_id:
                return ChatResponse(
                    content="Please connect to a supported network to perform swaps.",
                    agent_type="swap",
                    status="error"
                )

            # Forward to swap endpoint
            try:
                swap_response = await process_swap_command(SwapCommand(
                    command=command.command,
                    wallet_address=command.wallet_address,
                    chain_id=command.chain_id
                ))
                
                # Check for errors in swap response
                if "error" in swap_response:
                    return ChatResponse(
                        content=swap_response["error"],
                        agent_type="swap",
                        awaiting_confirmation=False,
                        status="error",
                        metadata={
                            "technical_details": swap_response.get("technical_details", "Unknown error")
                        }
                    )
                
                response = ChatResponse(
                    content=swap_response["content"],
                    agent_type="swap",
                    awaiting_confirmation=True,
                    status="success",
                    metadata=swap_response.get("metadata")
                )
                
                chat_history_service.add_entry(
                    command.wallet_address,
                    command.user_name,
                    'swap',
                    command.command,
                    response.dict()
                )
                return response
                
            except Exception as e:
                # Log the technical error
                logger.exception("Error processing swap command")
                return ChatResponse(
                    content="I encountered an issue while preparing your swap. Please try again.",
                    agent_type="swap",
                    status="error",
                    metadata={"technical_details": str(e)}
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
            
        # Add recent conversation history
        context += chat_history_service.get_recent_context(
            command.wallet_address,
            command.user_name
        )

        # Call OpenAI's API with the updated client
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are SNEL, a helpful crypto assistant. Provide concise, accurate information about cryptocurrencies, tokens, and blockchain technology."},
                {"role": "user", "content": f"{context}\nUser query: {command.command}"}
            ]
        )
        answer = response.choices[0].message.content
        
        chat_response = ChatResponse(
            content=answer,
            agent_type="default",
            status="success"
        )
        
        chat_history_service.add_entry(
            command.wallet_address,
            command.user_name,
            'general',
            command.command,
            chat_response.dict()
        )
        
        return chat_response
        
    except Exception as e:
        return ChatResponse(
            content=f"Sorry, I encountered an error: {str(e)}",
            status="error",
            error=str(e)
        )

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
from app.services.chat_history import chat_history_service
from app.api.v1.swap import process_swap_command, SwapCommand
from app.config.agent_config import AgentConfig, AgentMode
import logging

router = APIRouter(prefix="/chat", tags=["chat"])

logger = logging.getLogger(__name__)

def _build_enhanced_system_prompt(chain_id: Optional[int] = None, mode: AgentMode = AgentMode.DIRECT) -> str:
    """Build an enhanced system prompt with capability awareness."""

    # Get current chain context
    chain_context = ""
    available_capabilities = []
    available_protocols = []

    if chain_id and AgentConfig.is_chain_supported(chain_id):
        current_chain = AgentConfig.get_chain_name(chain_id)
        chain_context = f"\nUser is currently on: {current_chain}"

        # Get capabilities for this chain
        capabilities = AgentConfig.get_capabilities_for_chain(chain_id)
        available_capabilities = [cap.name for cap in capabilities]

        # Get protocols for this chain
        available_protocols = AgentConfig.get_supported_protocols_for_chain(chain_id)

    # Build supported chains list
    supported_chains_list = [
        f"{info['name']} ({chain_id})"
        for chain_id, info in list(AgentConfig.SUPPORTED_CHAINS.items())[:8]
    ]

    # Build capabilities description
    capabilities_text = ""
    for cap_name, capability in AgentConfig.CAPABILITIES.items():
        examples = " | ".join(capability.examples[:2])
        capabilities_text += f"• {capability.description}\n  Examples: {examples}\n"

    # Adjust response style based on mode
    if mode == AgentMode.CONVERSATIONAL:
        style_instructions = """
RESPONSE STYLE:
• Be helpful and conversational while staying focused
• Provide context when needed but keep it relevant
• Ask clarifying questions if user intent is unclear
• Explain what you're doing and why"""
    else:  # DIRECT mode (default)
        style_instructions = """
RESPONSE STYLE:
• Be direct and concise - avoid lengthy explanations unless asked
• Focus on actionable information and next steps
• For swap requests, confirm details and proceed to execution
• For general questions, provide brief, accurate answers
• Always mention relevant chains/protocols when applicable"""

    return f"""You are SNEL, a cross-chain crypto assistant specialized in DeFi operations. You help users execute swaps, bridges, and manage their crypto across multiple blockchains.{chain_context}

CORE CAPABILITIES:
{capabilities_text}
SUPPORTED NETWORKS:
• {', '.join(supported_chains_list)}... and 8 more chains
• Protocols: {', '.join(AgentConfig.PROTOCOL_CAPABILITIES.keys())}

{style_instructions}

IMPORTANT COMMANDS:
• Swaps: "swap [amount] [token] for [token]" or "swap $[amount] worth of [token] for [token]"
• Bridges: "bridge [amount] [token] from [chain] to [chain]"
• Balances: "show my [token] balance" or "check my portfolio"

For any operation, I'll confirm details before proceeding. I focus on execution, not explanation unless requested.

Remember: I'm built for efficient DeFi operations. Keep interactions focused and actionable."""

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

                # Check for error responses with detailed information
                if isinstance(swap_response, dict) and not swap_response.get("success", True):
                    error_details = swap_response.get("error_details", {})
                    error_message = error_details.get("error") or swap_response.get("message", "Unknown error")
                    protocols_tried = error_details.get("protocols_tried", [])
                    suggestion = error_details.get("suggestion", "Please try a different approach.")

                    # Format the error content with the detailed information
                    error_content = {
                        "message": error_message,
                        "protocols_tried": protocols_tried,
                        "suggestion": suggestion,
                        "type": "error"
                    }

                    if "technical_details" in error_details:
                        error_content["technical_details"] = error_details["technical_details"]

                    return ChatResponse(
                        content=error_content,
                        agent_type="swap",
                        awaiting_confirmation=False,
                        status="error",
                        metadata=error_details
                    )

                # Check for simple error field (for backward compatibility)
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

                # Create a content object for the response if it's not already a dict
                if isinstance(swap_response.get("content"), dict):
                    content = swap_response["content"]
                else:
                    # Create a default content object
                    content = {
                        "message": "Your swap has been processed successfully.",
                        "type": "swap_result"
                    }

                response = ChatResponse(
                    content=content,
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
                    response.model_dump()
                )
                return response

            except Exception as e:
                # Log the technical error
                logger.exception("Error processing swap confirmation")
                return ChatResponse(
                    content={
                        "message": "I encountered an issue while processing your swap. Please try again.",
                        "protocols_tried": [],
                        "suggestion": "This might be a temporary issue. Please try again in a few moments.",
                        "type": "error"
                    },
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
                response.model_dump()
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

                # Check for error responses with detailed information
                if isinstance(swap_response, dict) and not swap_response.get("success", True):
                    error_details = swap_response.get("error_details", {})
                    error_message = error_details.get("error") or swap_response.get("message", "Unknown error")
                    protocols_tried = error_details.get("protocols_tried", [])
                    suggestion = error_details.get("suggestion", "Please try a different approach.")

                    # Format the error content with the detailed information
                    error_content = {
                        "message": error_message,
                        "protocols_tried": protocols_tried,
                        "suggestion": suggestion,
                        "type": "error"
                    }

                    if "technical_details" in error_details:
                        error_content["technical_details"] = error_details["technical_details"]

                    return ChatResponse(
                        content=error_content,
                        agent_type="swap",
                        awaiting_confirmation=False,
                        status="error",
                        metadata=error_details
                    )

                # Check for simple error field (for backward compatibility)
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
                    response.model_dump()
                )
                return response

            except Exception as e:
                # Log the technical error
                logger.exception("Error processing swap command")
                return ChatResponse(
                    content={
                        "message": "I encountered an issue while preparing your swap. Please try again.",
                        "protocols_tried": [],
                        "suggestion": "This might be a temporary issue. Please try again in a few moments.",
                        "type": "error"
                    },
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

        # Enhanced system prompt with capability awareness
        system_prompt = _build_enhanced_system_prompt(command.chain_id)

        # Call OpenAI's API with the updated client
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_prompt},
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
            chat_response.model_dump()
        )

        return chat_response

    except Exception as e:
        return ChatResponse(
            content=f"Sorry, I encountered an error: {str(e)}",
            status="error",
            error=str(e)
        )

@router.get("/agent-info")
async def get_agent_info():
    """Get information about the agent's capabilities and configuration."""
    return {
        "agent_name": "SNEL",
        "version": "2.0",
        "capabilities": {
            name: {
                "description": cap.description,
                "supported_chains": len(cap.supported_chains),
                "examples": cap.examples[:2]
            }
            for name, cap in AgentConfig.CAPABILITIES.items()
        },
        "supported_chains": {
            str(chain_id): info["name"]
            for chain_id, info in AgentConfig.SUPPORTED_CHAINS.items()
        },
        "protocols": list(AgentConfig.PROTOCOL_CAPABILITIES.keys()),
        "response_modes": [mode.value for mode in AgentMode],
        "status": "operational"
    }

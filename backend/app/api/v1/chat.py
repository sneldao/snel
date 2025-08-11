"""
Unified chat command processing with dependency injection.
Clean, modular implementation without import chaos.
"""
import logging
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.services.chat_history import chat_history_service
from app.services.command_processor import CommandProcessor
from app.models.unified_models import ChatCommand, ChatResponse, TransactionStepCompletion
from app.config.agent_config import AgentConfig, AgentMode
from app.core.dependencies import get_command_processor
from app.core.exceptions import SNELException

router = APIRouter(prefix="/chat", tags=["chat"])
logger = logging.getLogger(__name__)

class ProtocolQuestionRequest(BaseModel):
    protocol_name: str
    question: str
    raw_content: str
    openai_api_key: str = None

class ProtocolQuestionResponse(BaseModel):
    success: bool
    answer: str = ""
    error: str = ""

@router.post("/process-command")
async def process_command(
    command: ChatCommand,
    command_processor: CommandProcessor = Depends(get_command_processor)
) -> ChatResponse:
    """Process a chat command using dependency injection."""
    try:
        # Create unified command using the new parser
        unified_command = CommandProcessor.create_unified_command(
            command=command.command,
            wallet_address=command.wallet_address,
            chain_id=command.chain_id,
            user_name=command.user_name,
            openai_api_key=command.openai_api_key
        )

        # Validate the command
        validation = CommandProcessor.validate_command(unified_command)
        if not validation.is_valid:
            return ChatResponse(
                content={
                    "message": validation.error_message,
                    "type": "error",
                    "missing_requirements": validation.missing_requirements
                },
                agent_type="error",
                status="error"
            )

        # Process the command using injected processor
        unified_response = await command_processor.process_command(unified_command)

        # Convert unified response to ChatResponse for backward compatibility
        content = unified_response.content
        if hasattr(content, 'model_dump'):
            # Convert Pydantic model to dict
            content = content.model_dump()
        elif hasattr(content, '__dict__'):
            # Convert object to dict
            content = content.__dict__

        chat_response = ChatResponse(
            content=content,
            agent_type=unified_response.agent_type.value if hasattr(unified_response.agent_type, 'value') else str(unified_response.agent_type),
            status=unified_response.status,
            awaiting_confirmation=unified_response.awaiting_confirmation,
            transaction=unified_response.transaction.model_dump() if unified_response.transaction else None,
            metadata=unified_response.metadata,
            error=unified_response.error
        )

        # Add to chat history
        chat_history_service.add_entry(
            command.wallet_address,
            command.user_name,
            unified_command.command_type.value,
            command.command,
            chat_response.model_dump()
        )

        return chat_response

    except SNELException as e:
        # Handle known SNEL exceptions with structured responses
        logger.warning(f"SNEL exception processing command: {e.message}")
        return ChatResponse(
            content={
                "message": e.message,
                "type": "error",
                "suggestions": e.suggestions,
                "details": e.details
            },
            status="error",
            error=e.message
        )
    except Exception as e:
        # Handle unexpected exceptions
        logger.exception(f"Unexpected error processing command: {command.command}")
        return ChatResponse(
            content={
                "message": "I encountered an unexpected error. Please try again.",
                "type": "error"
            },
            status="error",
            error=str(e)
        )

@router.post("/ask-protocol-question")
async def ask_protocol_question(request: ProtocolQuestionRequest) -> ProtocolQuestionResponse:
    """Ask a follow-up question about a protocol using previously scraped content."""
    try:
        from app.services.external.firecrawl_service import answer_protocol_question

        result = await answer_protocol_question(
            protocol_name=request.protocol_name,
            question=request.question,
            raw_content=request.raw_content,
            openai_api_key=request.openai_api_key
        )

        return ProtocolQuestionResponse(
            success=result.get("success", False),
            answer=result.get("answer", ""),
            error=result.get("error", "")
        )

    except Exception as e:
        logger.exception("Error processing protocol question")
        return ProtocolQuestionResponse(
            success=False,
            answer="",
            error=f"Failed to process question: {str(e)}"
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


@router.post("/complete-bridge-step")
async def complete_bridge_step(
    request: TransactionStepCompletion,
    command_processor: CommandProcessor = Depends(get_command_processor)
) -> ChatResponse:
    """
    Complete a bridge transaction step and get the next step.

    This endpoint handles multi-step bridge transactions by:
    1. Completing the current step (e.g., approval)
    2. Returning the next step (e.g., send_token)
    """
    try:
        logger.info(f"Bridge step completion for {request.wallet_address}, tx: {request.tx_hash}")

        # Create unified command for transaction step completion
        unified_command = CommandProcessor.create_unified_command(
            command="complete_transaction_step",  # Internal command
            wallet_address=request.wallet_address,
            chain_id=request.chain_id
        )

        # Override command type and add step completion details
        from app.models.unified_models import CommandType
        unified_command.command_type = CommandType.TRANSACTION_STEP_COMPLETE
        unified_command.details = {
            "wallet_address": request.wallet_address,
            "chain_id": request.chain_id,
            "tx_hash": request.tx_hash,
            "success": request.success
        }

        # Process through unified command processor
        unified_response = await command_processor.process_command(unified_command)

        # Extract content
        content = unified_response.content
        if hasattr(content, '__dict__'):
            content = content.__dict__

        # Convert to ChatResponse format
        return ChatResponse(
            content=content,
            agent_type=unified_response.agent_type.value if hasattr(unified_response.agent_type, 'value') else str(unified_response.agent_type),
            status=unified_response.status,
            awaiting_confirmation=unified_response.awaiting_confirmation,
            transaction=unified_response.transaction.model_dump() if unified_response.transaction else None,
            metadata=unified_response.metadata,
            error=unified_response.error
        )

    except Exception as e:
        logger.exception(f"Error in bridge step completion: {e}")
        return ChatResponse(
            content={
                "message": f"Bridge step completion failed: {str(e)}",
                "type": "error",
                "has_next_step": False
            },
            agent_type="error",
            status="error",
            error=str(e)
        )

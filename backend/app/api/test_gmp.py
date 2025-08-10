"""
Test endpoint for GMP command parsing.
Allows frontend to test real backend parsing.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, Optional

from app.services.enhanced_command_patterns import enhanced_patterns
from app.services.enhanced_crosschain_handler import enhanced_crosschain_handler
from app.models.unified_models import UnifiedCommand, CommandType

router = APIRouter(prefix="/test", tags=["test"])

class CommandTestRequest(BaseModel):
    command: str
    wallet_address: Optional[str] = "0x742d35Cc6634C0532925a3b8D4C9db96C4b4d8b6"

class CommandTestResponse(BaseModel):
    command: str
    detected_type: str
    extracted_params: Optional[Dict[str, Any]]
    is_gmp_operation: bool
    can_handle: bool
    success: bool

@router.post("/parse-command", response_model=CommandTestResponse)
async def test_command_parsing(request: CommandTestRequest):
    """Test command parsing and GMP detection."""
    try:
        # Test pattern detection
        command_type, params = enhanced_patterns.detect_command_type(request.command)
        
        # Test GMP handler capability
        test_command = UnifiedCommand(
            command=request.command,
            command_type=command_type,
            wallet_address=request.wallet_address,
            chain_id=1
        )
        
        can_handle = await enhanced_crosschain_handler.can_handle(test_command)
        is_gmp = command_type in [CommandType.CROSS_CHAIN_SWAP, CommandType.GMP_OPERATION]
        
        return CommandTestResponse(
            command=request.command,
            detected_type=command_type.value,
            extracted_params=params,
            is_gmp_operation=is_gmp,
            can_handle=can_handle,
            success=True
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/supported-chains")
async def get_supported_chains():
    """Get supported chains for GMP operations."""
    try:
        chains = await enhanced_crosschain_handler.get_supported_chains()
        operations = await enhanced_crosschain_handler.get_supported_operations()
        
        return {
            "supported_chains": chains,
            "supported_operations": operations,
            "success": True
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

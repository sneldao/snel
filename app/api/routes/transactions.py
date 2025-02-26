from fastapi import APIRouter, Depends, Request, HTTPException
import logging
from typing import Dict, Any

from app.models.commands import TransactionRequest, TransactionResponse
from app.api.routes.swap_router import execute_transaction as swap_router_execute

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api")

@router.post("/execute", response_model=TransactionResponse)
async def execute_transaction(
    tx_request: TransactionRequest,
    request: Request,
):
    """
    Legacy endpoint for executing transactions.
    This now delegates to the swap_router implementation.
    
    This endpoint is maintained for backward compatibility.
    """
    logger.info(f"Legacy transaction endpoint called, delegating to swap_router")
    return await swap_router_execute(tx_request, request)

@router.post("/execute-transaction")
async def execute_transaction_legacy(
    tx_request: TransactionRequest,
    request: Request,
):
    """
    Legacy endpoint for executing transactions.
    This now delegates to the swap_router implementation.
    
    This endpoint is maintained for backward compatibility.
    """
    logger.info(f"Legacy transaction endpoint called, delegating to swap_router")
    return await swap_router_execute(tx_request, request) 
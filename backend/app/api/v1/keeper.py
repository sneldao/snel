"""API endpoints for recurring payment keeper job management."""
import logging
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/keeper", tags=["keeper"])


@router.post("/run-check")
async def run_keeper_check():
    """
    Manually trigger a recurring payment keeper check.
    
    This endpoint:
    1. Checks all enabled recurring payment actions
    2. Identifies due payments
    3. Executes them automatically
    4. Returns summary of actions executed
    
    **Response Example**
    ```json
    {
      "timestamp": "2024-01-07T15:30:00",
      "duration_seconds": 2.34,
      "wallets_checked": 5,
      "actions_checked": 23,
      "actions_executed": 3,
      "actions_failed": 0,
      "success_rate": 100
    }
    ```
    """
    try:
        from app.domains.payment_actions.keeper import get_recurring_payment_keeper
        
        keeper = await get_recurring_payment_keeper()
        result = await keeper.run_check()
        
        return JSONResponse(
            status_code=200,
            content=result,
        )
    
    except Exception as e:
        logger.exception("Keeper check failed")
        return JSONResponse(
            status_code=500,
            content={
                "error": str(e),
                "status": "failed",
            },
        )


@router.get("/status/{wallet_address}/{action_id}")
async def get_action_execution_status(wallet_address: str, action_id: str):
    """
    Get execution history for a recurring payment action.
    
    **Response Example**
    ```json
    [
      {
        "action_id": "action_123",
        "wallet_address": "0x742d...",
        "status": "success",
        "ticket_id": "ticket_xyz",
        "timestamp": "2024-01-07T15:30:00"
      },
      {
        "action_id": "action_123",
        "wallet_address": "0x742d...",
        "status": "success",
        "ticket_id": "ticket_uvw",
        "timestamp": "2024-01-06T15:30:00"
      }
    ]
    ```
    """
    try:
        from app.domains.payment_actions.keeper import get_recurring_payment_keeper
        
        keeper = await get_recurring_payment_keeper()
        history = keeper.get_execution_log(action_id, limit=50)
        
        return JSONResponse(
            status_code=200,
            content=history,
        )
    
    except Exception as e:
        logger.exception("Status retrieval failed")
        return JSONResponse(
            status_code=500,
            content={
                "error": str(e),
            },
        )

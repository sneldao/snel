"""Webhook API endpoints for AI agents to trigger payment actions."""
import logging
import uuid
import json
from fastapi import APIRouter, HTTPException, Header, Request
from fastapi.responses import JSONResponse

from app.domains.payment_actions.webhooks import (
    WebhookRequest,
    WebhookEventType,
    WebhookValidator,
)
from app.services.webhook_service import get_webhook_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/webhooks", tags=["webhooks"])


@router.post("/execute-action")
async def webhook_execute_action(
    request: Request,
    x_webhook_signature: str = Header(None),
    x_agent_id: str = Header(None),
):
    """
    Webhook endpoint for AI agents to execute payment actions.
    
    **Signature Verification (Optional)**
    
    Sign your request payload with HMAC-SHA256 using your agent secret:
    ```
    signature = HMAC_SHA256(json_body, agent_secret)
    ```
    
    Include as header: `X-Webhook-Signature: {signature}`
    
    **Request Example**
    ```json
    {
      "event_type": "execute_action",
      "payload": {
        "action_id": "action_123",
        "wallet_address": "0x742d...",
        "override_amount": "50",
        "metadata": {
          "source": "ai_agent_v1"
        }
      }
    }
    ```
    
    **Response Example**
    ```json
    {
      "success": true,
      "request_id": "webhook_abc123",
      "message": "Action executed",
      "result": {
        "action_id": "action_123",
        "status": "submitted",
        "ticket_id": "ticket_xyz789"
      }
    }
    ```
    """
    try:
        # Generate request ID for tracking
        request_id = str(uuid.uuid4())
        
        # Parse request body
        body = await request.body()
        payload = json.loads(body)
        
        # Verify signature if provided (for production agents)
        # In dev, you can skip this by not sending X-Webhook-Signature
        agent_secret = None  # Would load from DB based on X-Agent-ID in production
        
        # Create webhook request
        webhook_req = WebhookRequest(
            event_type=WebhookEventType.EXECUTE_ACTION,
            payload=payload.get("payload", {}),
            request_id=request_id,
            signature=x_webhook_signature,
        )
        
        # Process webhook
        webhook_service = await get_webhook_service()
        response = await webhook_service.handle_webhook(webhook_req, agent_secret)
        
        return JSONResponse(
            status_code=200 if response.success else 400,
            content=response.dict(),
        )
    
    except json.JSONDecodeError:
        logger.error(f"Invalid JSON in webhook request")
        return JSONResponse(
            status_code=400,
            content={
                "success": False,
                "request_id": request_id if 'request_id' in locals() else "unknown",
                "error": "Invalid JSON payload",
            },
        )
    
    except Exception as e:
        logger.exception("Webhook endpoint error")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "request_id": request_id if 'request_id' in locals() else "unknown",
                "error": str(e),
            },
        )


@router.post("/execute-batch")
async def webhook_execute_batch(
    request: Request,
    x_webhook_signature: str = Header(None),
    x_agent_id: str = Header(None),
):
    """
    Webhook endpoint for AI agents to execute batch payments.
    
    **Request Example - Send 10 MNEE split between 2 creators**
    ```json
    {
      "event_type": "execute_batch",
      "payload": {
        "wallet_address": "0x742d...",
        "token": "MNEE",
        "chain_id": 1,
        "amount": "10",
        "recipients": [
          {
            "address": "0xabc1...",
            "percentage": 60,
            "label": "Creator A"
          },
          {
            "address": "0xdef2...",
            "percentage": 40,
            "label": "Creator B"
          }
        ]
      }
    }
    ```
    
    **Response Example**
    ```json
    {
      "success": true,
      "request_id": "webhook_abc123",
      "message": "Batch payment processed (2 recipients)",
      "result": {
        "total_recipients": 2,
        "successful": 2,
        "results": [
          {
            "recipient": "0xabc1...",
            "amount": "6",
            "status": "submitted",
            "ticket_id": "ticket_xyz"
          },
          {
            "recipient": "0xdef2...",
            "amount": "4",
            "status": "submitted",
            "ticket_id": "ticket_uvw"
          }
        ]
      }
    }
    ```
    """
    try:
        request_id = str(uuid.uuid4())
        body = await request.body()
        payload = json.loads(body)
        
        webhook_req = WebhookRequest(
            event_type=WebhookEventType.EXECUTE_BATCH,
            payload=payload.get("payload", {}),
            request_id=request_id,
            signature=x_webhook_signature,
        )
        
        webhook_service = await get_webhook_service()
        response = await webhook_service.handle_webhook(webhook_req)
        
        return JSONResponse(
            status_code=200 if response.success else 400,
            content=response.dict(),
        )
    
    except Exception as e:
        logger.exception("Batch webhook error")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "request_id": request_id if 'request_id' in locals() else "unknown",
                "error": str(e),
            },
        )


@router.post("/create-action")
async def webhook_create_action(
    request: Request,
    x_webhook_signature: str = Header(None),
    x_agent_id: str = Header(None),
):
    """
    Webhook endpoint for AI agents to create payment actions programmatically.
    
    **Request Example**
    ```json
    {
      "event_type": "create_action",
      "payload": {
        "wallet_address": "0x742d...",
        "name": "Daily Bot Payments",
        "action_type": "recurring",
        "recipient_address": "0xabc1...",
        "amount": "1.5",
        "token": "MNEE",
        "chain_id": 1,
        "schedule": {
          "frequency": "daily"
        },
        "is_pinned": true
      }
    }
    ```
    """
    try:
        request_id = str(uuid.uuid4())
        body = await request.body()
        payload = json.loads(body)
        
        webhook_req = WebhookRequest(
            event_type=WebhookEventType.CREATE_ACTION,
            payload=payload.get("payload", {}),
            request_id=request_id,
            signature=x_webhook_signature,
        )
        
        webhook_service = await get_webhook_service()
        response = await webhook_service.handle_webhook(webhook_req)
        
        return JSONResponse(
            status_code=200 if response.success else 400,
            content=response.dict(),
        )
    
    except Exception as e:
        logger.exception("Create action webhook error")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "request_id": request_id if 'request_id' in locals() else "unknown",
                "error": str(e),
            },
        )


@router.get("/history/{wallet_address}")
async def get_webhook_history(
    wallet_address: str,
    limit: int = 100,
):
    """
    Get execution history for a wallet.
    
    **Response Example**
    ```json
    [
      {
        "request_id": "webhook_abc123",
        "event_type": "execute_action",
        "wallet_address": "0x742d...",
        "action_id": "action_123",
        "ticket_id": "ticket_xyz",
        "status": "submitted",
        "created_at": "2024-01-07T15:30:00",
        "completed_at": "2024-01-07T15:30:05"
      }
    ]
    ```
    """
    try:
        webhook_service = await get_webhook_service()
        history = webhook_service.get_execution_history(wallet_address, limit)
        return JSONResponse(
            status_code=200,
            content=history,
        )
    
    except Exception as e:
        logger.exception("History retrieval error")
        return JSONResponse(
            status_code=500,
            content={"error": str(e)},
        )

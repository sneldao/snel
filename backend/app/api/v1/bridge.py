"""
Bridge status tracking endpoints.

Provides real-time status updates for cross-chain bridge operations,
particularly for Axelar GMP transactions.
"""

import logging
from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any, Optional
import redis

from app.core.dependencies import get_redis_client

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/bridge", tags=["bridge"])


# Response models
class BridgeStep:
    """Represents a single step in the bridge transaction."""
    def __init__(
        self,
        step_number: int,
        name: str,
        status: str,
        description: str,
        tx_hash: Optional[str] = None,
        confirmed_at: Optional[str] = None,
    ):
        self.step_number = step_number
        self.name = name
        self.status = status
        self.description = description
        self.tx_hash = tx_hash
        self.confirmed_at = confirmed_at

    def to_dict(self) -> Dict[str, Any]:
        return {
            "step_number": self.step_number,
            "name": self.name,
            "status": self.status,
            "description": self.description,
            "tx_hash": self.tx_hash,
            "confirmed_at": self.confirmed_at,
        }


class BridgeStatusResponse:
    """Bridge status response structure."""
    def __init__(
        self,
        bridge_id: str,
        status: str,
        current_step: int,
        total_steps: int,
        steps: list,
        source_tx_hash: Optional[str] = None,
        destination_tx_hash: Optional[str] = None,
        timestamp: Optional[str] = None,
        error: Optional[str] = None,
    ):
        self.bridge_id = bridge_id
        self.status = status
        self.current_step = current_step
        self.total_steps = total_steps
        self.steps = steps
        self.source_tx_hash = source_tx_hash
        self.destination_tx_hash = destination_tx_hash
        self.timestamp = timestamp
        self.error = error

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "bridge_status",
            "bridge_id": self.bridge_id,
            "status": self.status,
            "current_step": self.current_step,
            "total_steps": self.total_steps,
            "steps": [step.to_dict() if isinstance(step, BridgeStep) else step for step in self.steps],
            "source_tx_hash": self.source_tx_hash,
            "destination_tx_hash": self.destination_tx_hash,
            "timestamp": self.timestamp,
            "error": self.error,
        }


@router.get("/status/{bridge_id}")
async def get_bridge_status(
    bridge_id: str,
    redis_client: redis.Redis = Depends(get_redis_client),
) -> Dict[str, Any]:
    """
    Get real-time status of a bridge transaction.
    
    Fetches cached bridge status from Redis or Axelar API.
    Status updates are pushed from transaction handlers.
    
    Args:
        bridge_id: Unique bridge transaction ID
        redis_client: Redis client for status caching
        
    Returns:
        BridgeStatusResponse with current progress
        
    Raises:
        HTTPException: If bridge not found or status unavailable
    """
    try:
        # Try to get cached status from Redis
        cache_key = f"bridge_status:{bridge_id}"
        cached_status = redis_client.get(cache_key)

        if cached_status:
            import json
            return json.loads(cached_status)

        # If not cached, return initial/pending status
        # In production, would query Axelar API here
        logger.warning(f"Bridge status not found in cache: {bridge_id}")
        
        response = BridgeStatusResponse(
            bridge_id=bridge_id,
            status="initiated",
            current_step=1,
            total_steps=3,
            steps=[
                BridgeStep(
                    step_number=1,
                    name="Source Chain Confirmation",
                    status="pending",
                    description="Confirming transaction on source chain",
                ).to_dict(),
                BridgeStep(
                    step_number=2,
                    name="Axelar Gateway Relay",
                    status="pending",
                    description="Relaying transaction through Axelar",
                ).to_dict(),
                BridgeStep(
                    step_number=3,
                    name="Destination Chain Confirmation",
                    status="pending",
                    description="Confirming receipt on destination chain",
                ).to_dict(),
            ],
            timestamp=None,
            error=None,
        )
        
        return response.to_dict()

    except Exception as e:
        logger.exception(f"Error fetching bridge status: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch bridge status: {str(e)}",
        )


@router.post("/status/{bridge_id}/update")
async def update_bridge_status(
    bridge_id: str,
    status_data: Dict[str, Any],
    redis_client: redis.Redis = Depends(get_redis_client),
) -> Dict[str, str]:
    """
    Update bridge status (internal use).
    
    Called by transaction handlers to push status updates.
    Stores in Redis for real-time polling.
    
    Args:
        bridge_id: Bridge transaction ID
        status_data: Status update data
        redis_client: Redis client for caching
        
    Returns:
        Confirmation of update
    """
    try:
        import json
        from datetime import datetime, timedelta

        cache_key = f"bridge_status:{bridge_id}"
        
        # Store with 1-hour TTL
        redis_client.setex(
            cache_key,
            3600,
            json.dumps(status_data),
        )
        
        logger.info(f"Bridge status updated: {bridge_id} -> {status_data.get('status')}")
        
        return {"status": "updated", "bridge_id": bridge_id}

    except Exception as e:
        logger.exception(f"Error updating bridge status: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update bridge status: {str(e)}",
        )

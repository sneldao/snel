"""
Transaction flow service for managing multi-step transactions.
"""
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from enum import Enum
import json
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class TransactionStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress" 
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class StepType(Enum):
    APPROVAL = "approval"
    SWAP = "swap"
    BRIDGE = "bridge"
    OTHER = "other"

@dataclass
class TransactionStep:
    """Represents a single transaction step."""
    step_number: int
    step_type: StepType
    to: str
    data: str
    value: str = "0"
    gas_limit: str = "500000"
    description: str = ""
    status: TransactionStatus = TransactionStatus.PENDING
    tx_hash: Optional[str] = None
    error: Optional[str] = None
    created_at: datetime = None
    completed_at: Optional[datetime] = None
    metadata: Optional[dict] = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow()

@dataclass 
class TransactionFlow:
    """Represents a complete multi-step transaction flow."""
    flow_id: str
    wallet_address: str
    chain_id: int
    operation_type: str  # "swap", "bridge", etc.
    steps: List[TransactionStep]
    current_step: int = 0
    status: TransactionStatus = TransactionStatus.PENDING
    created_at: datetime = None
    updated_at: datetime = None
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow()
        if self.updated_at is None:
            self.updated_at = datetime.utcnow()
        if self.metadata is None:
            self.metadata = {}

class TransactionFlowService:
    """Service for managing multi-step transaction flows."""
    
    def __init__(self):
        # In-memory storage (could be replaced with Redis/DB)
        self._flows: Dict[str, TransactionFlow] = {}
        self._user_flows: Dict[str, str] = {}  # wallet_address -> flow_id
        
    def create_flow(
        self,
        wallet_address: str,
        chain_id: int,
        operation_type: str,
        steps_data: List[Dict[str, Any]],
        metadata: Optional[Dict[str, Any]] = None
    ) -> TransactionFlow:
        """Create a new transaction flow from steps data."""
        
        # Generate flow ID
        flow_id = f"{wallet_address}_{operation_type}_{int(datetime.utcnow().timestamp())}"
        
        # Convert steps data to TransactionStep objects
        steps = []
        for i, step_data in enumerate(steps_data):
            step_type = self._detect_step_type(step_data.get("data", ""))
            description = self._generate_step_description(step_type, i + 1, len(steps_data))
            
            step = TransactionStep(
                step_number=i + 1,
                step_type=step_type,
                to=step_data.get("to", ""),
                data=step_data.get("data", ""),
                value=step_data.get("value", "0"),
                gas_limit=step_data.get("gasLimit", "500000"),
                description=description,
                metadata=step_data.get("metadata")
            )
            steps.append(step)
        
        # Create flow
        flow = TransactionFlow(
            flow_id=flow_id,
            wallet_address=wallet_address,
            chain_id=chain_id,
            operation_type=operation_type,
            steps=steps,
            metadata=metadata or {}
        )
        
        # Store flow
        self._flows[flow_id] = flow
        self._user_flows[wallet_address] = flow_id
        
        logger.info(f"Created transaction flow {flow_id} with {len(steps)} steps")
        return flow
    
    def get_current_flow(self, wallet_address: str) -> Optional[TransactionFlow]:
        """Get the current active flow for a user."""
        flow_id = self._user_flows.get(wallet_address)
        if not flow_id:
            return None
        return self._flows.get(flow_id)
    
    def get_next_step(self, wallet_address: str) -> Optional[TransactionStep]:
        """Get the next step to execute for a user."""
        flow = self.get_current_flow(wallet_address)
        if not flow or flow.current_step >= len(flow.steps):
            return None
        
        return flow.steps[flow.current_step]
    
    def complete_step(
        self,
        wallet_address: str,
        tx_hash: str,
        success: bool = True,
        error: Optional[str] = None
    ) -> bool:
        """Mark the current step as completed and advance to next."""
        flow = self.get_current_flow(wallet_address)
        if not flow or flow.current_step >= len(flow.steps):
            return False
        
        # Update current step
        current_step = flow.steps[flow.current_step]
        current_step.tx_hash = tx_hash
        current_step.completed_at = datetime.utcnow()
        current_step.status = TransactionStatus.COMPLETED if success else TransactionStatus.FAILED
        
        if error:
            current_step.error = error
        
        if success:
            # Advance to next step
            flow.current_step += 1
            
            # Check if flow is complete
            if flow.current_step >= len(flow.steps):
                flow.status = TransactionStatus.COMPLETED
                logger.info(f"Transaction flow {flow.flow_id} completed successfully")
            else:
                flow.status = TransactionStatus.IN_PROGRESS
        else:
            # Mark flow as failed
            flow.status = TransactionStatus.FAILED
            logger.error(f"Transaction flow {flow.flow_id} failed at step {flow.current_step + 1}: {error}")
        
        flow.updated_at = datetime.utcnow()
        return True
    
    def cancel_flow(self, wallet_address: str) -> bool:
        """Cancel the current flow for a user."""
        flow = self.get_current_flow(wallet_address)
        if not flow:
            return False
        
        flow.status = TransactionStatus.CANCELLED
        flow.updated_at = datetime.utcnow()
        
        # Remove from active flows
        if wallet_address in self._user_flows:
            del self._user_flows[wallet_address]
        
        logger.info(f"Transaction flow {flow.flow_id} cancelled")
        return True
    
    def get_flow_status(self, wallet_address: str) -> Optional[Dict[str, Any]]:
        """Get the current status of a user's transaction flow."""
        flow = self.get_current_flow(wallet_address)
        if not flow:
            return None
        
        return {
            "flow_id": flow.flow_id,
            "status": flow.status.value,
            "current_step": flow.current_step + 1,
            "total_steps": len(flow.steps),
            "operation_type": flow.operation_type,
            "steps": [
                {
                    "step_number": step.step_number,
                    "step_type": step.step_type.value,
                    "description": step.description,
                    "status": step.status.value,
                    "tx_hash": step.tx_hash,
                    "error": step.error
                }
                for step in flow.steps
            ],
            "metadata": flow.metadata
        }
    
    def cleanup_old_flows(self, max_age_hours: int = 24):
        """Clean up old completed/failed flows."""
        cutoff_time = datetime.utcnow() - timedelta(hours=max_age_hours)
        
        flows_to_remove = []
        for flow_id, flow in self._flows.items():
            if (flow.status in [TransactionStatus.COMPLETED, TransactionStatus.FAILED, TransactionStatus.CANCELLED] 
                and flow.updated_at < cutoff_time):
                flows_to_remove.append(flow_id)
        
        for flow_id in flows_to_remove:
            flow = self._flows[flow_id]
            del self._flows[flow_id]
            
            # Remove from user flows if it's the current one
            if self._user_flows.get(flow.wallet_address) == flow_id:
                del self._user_flows[flow.wallet_address]
        
        if flows_to_remove:
            logger.info(f"Cleaned up {len(flows_to_remove)} old transaction flows")
    
    def _detect_step_type(self, tx_data: str) -> StepType:
        """Detect the type of transaction step based on function signature."""
        if not tx_data or len(tx_data) < 10:
            return StepType.OTHER
        
        function_sig = tx_data[:10].lower()
        
        # Common function signatures
        if function_sig == "0x095ea7b3":  # approve(address,uint256)
            return StepType.APPROVAL
        elif function_sig in ["0x38ed1739", "0x7ff36ab5", "0x18cbafe5", "0x8803dbee"]:
            return StepType.SWAP
        elif function_sig == "0x26ef699d":  # sendToken (Axelar bridge)
            return StepType.BRIDGE
        else:
            # For complex transactions, assume it's a swap if data is substantial
            return StepType.SWAP if len(tx_data) > 100 else StepType.OTHER
    
    def _generate_step_description(self, step_type: StepType, step_num: int, total_steps: int) -> str:
        """Generate a user-friendly description for a transaction step."""
        if step_type == StepType.APPROVAL:
            return f"Step {step_num}/{total_steps}: Approve token spending"
        elif step_type == StepType.SWAP:
            if total_steps > 1:
                return f"Step {step_num}/{total_steps}: Execute token swap"
            else:
                return "Execute token swap"
        elif step_type == StepType.BRIDGE:
            return f"Step {step_num}/{total_steps}: Bridge tokens across chains"
        else:
            return f"Step {step_num}/{total_steps}: Execute transaction"

# Global instance
transaction_flow_service = TransactionFlowService()

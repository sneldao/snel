from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional

class TransactionRequest(BaseModel):
    """
    Model for transaction request data coming from the frontend.
    """
    wallet_address: str
    chain_id: int = 1
    command: Optional[str] = None
    skip_approval: bool = False
    get_quotes: bool = False
    signature: Optional[str] = None
    signed_message: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    selected_quote: Optional[Dict[str, Any]] = None

class TransactionResponse(BaseModel):
    """
    Model for transaction response data going to the frontend.
    """
    to: Optional[str] = None
    data: Optional[str] = None
    value: Optional[str] = None
    chain_id: int
    method: Optional[str] = None
    gas_limit: Optional[str] = None
    gas_price: Optional[str] = None
    max_fee_per_gas: Optional[str] = None
    max_priority_fee_per_gas: Optional[str] = None
    error: Optional[str] = None
    error_code: Optional[str] = None
    needs_approval: Optional[bool] = None
    token_to_approve: Optional[str] = None
    spender: Optional[str] = None
    pending_command: Optional[str] = None
    status: Optional[str] = None
    requires_selection: Optional[bool] = None
    all_quotes: Optional[List[Dict[str, Any]]] = None
    quotes_count: Optional[int] = None
    selected_quote: Optional[Dict[str, Any]] = None
    awaitingConfirmation: Optional[bool] = None
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict) 
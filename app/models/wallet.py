from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List, Union

class ChainInfo(BaseModel):
    """Information about a blockchain network"""
    id: str
    name: str
    chainId: int
    rpcUrl: str
    isDefault: bool = False

class AuthParams(BaseModel):
    """Authentication parameters for wallet creation"""
    projectId: str
    clientKey: str
    appId: str
    userId: str
    chainId: int
    authType: str = "telegram"

class WalletInfo(BaseModel):
    """Information about a user's wallet"""
    has_wallet: bool = False
    address: Optional[str] = None
    chain: Optional[str] = None
    chain_info: Optional[ChainInfo] = None
    auth_params: Optional[AuthParams] = None

class WalletCreationResponse(BaseModel):
    """Response from wallet creation operation"""
    success: bool
    message: str
    auth_params: Optional[AuthParams] = None
    chain: Optional[str] = None
    chain_info: Optional[Dict[str, Any]] = None

class WalletInfoResponse(BaseModel):
    """Response from wallet info retrieval"""
    success: bool
    message: str
    has_wallet: bool = False
    auth_params: Optional[Dict[str, Any]] = None
    chain: Optional[str] = None
    chain_info: Optional[Dict[str, Any]] = None

class ChainSwitchResponse(BaseModel):
    """Response from chain switch operation"""
    success: bool
    message: str
    chain: Optional[str] = None
    chain_info: Optional[Dict[str, Any]] = None

class Transaction(BaseModel):
    """Transaction data for sending assets"""
    from_address: str
    to_address: str
    amount: str
    token_address: Optional[str] = None  # None for native token
    chain_id: int

class TransactionResponse(BaseModel):
    """Response from transaction submission"""
    success: bool
    message: str
    transaction_hash: Optional[str] = None
    block_explorer_url: Optional[str] = None

class WalletCommand(BaseModel):
    """Wallet command from messaging platforms"""
    command: str
    args: List[str] = []
    user_id: str
    platform: str
    wallet_address: Optional[str] = None 
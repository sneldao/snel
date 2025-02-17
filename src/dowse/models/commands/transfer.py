from pydantic import BaseModel


class TransferArgs(BaseModel):
    token_symbol: str | None
    token_address: str
    amount: int

    recipient: str
    sender: str

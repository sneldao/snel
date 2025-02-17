from typing import Annotated

from pydantic import BaseModel
from typing_extensions import Doc


class TransferArgs(BaseModel):
    token_symbol: Annotated[str | None, Doc("The symbol of the token to transfer")]
    token_address: Annotated[str, Doc("The address of the token to transfer")]
    amount: Annotated[int, Doc("The amount of the token to transfer")]

    recipient: Annotated[str, Doc("The recipient of the transfer")]
    sender: Annotated[str, Doc("The sender of the transfer")]

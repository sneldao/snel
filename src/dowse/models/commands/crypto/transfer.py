from typing import Annotated

from pydantic import BaseModel
from typing_extensions import Doc


class TransferArgs(BaseModel):
    token_address: Annotated[str, Doc("The address of the token to transfer")]
    amount: Annotated[int, Doc("The amount of the token to transfer")]

    recipient: Annotated[
        str, Doc("The twitter handle or address of the recipient of the transfer")
    ]

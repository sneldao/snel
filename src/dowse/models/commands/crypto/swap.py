from typing import Annotated

from pydantic import BaseModel
from typing_extensions import Doc


class SwapArgs(BaseModel):
    token_in_address: Annotated[str, Doc("The address of the token to swap from")]
    token_out_address: Annotated[str, Doc("The address of the token to swap to")]
    amount_in: Annotated[int, Doc("The amount of tokens to swap")]
    amount_out: Annotated[int, Doc("The amount of tokens to receive")]

    recipient: Annotated[str, Doc("The twitter handle or address of the recipient")]

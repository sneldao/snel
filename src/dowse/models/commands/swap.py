from typing import Annotated

from pydantic import BaseModel
from typing_extensions import Doc


class SwapArgs(BaseModel):
    token_in_symbol: Annotated[str, Doc("The symbol of the token to swap from")]
    token_out_symbol: Annotated[str, Doc("The symbol of the token to swap to")]
    token_in_address: Annotated[str, Doc("The address of the token to swap from")]
    token_out_address: Annotated[str, Doc("The address of the token to swap to")]
    amount_in: Annotated[int, Doc("The amount of tokens to swap")]
    amount_out: Annotated[int, Doc("The amount of tokens to receive")]
    slippage: Annotated[float, Doc("The slippage tolerance")]

    sender: Annotated[str, Doc("The sender of the transaction")]
    recipient: Annotated[str, Doc("The recipient of the transaction")]

from eth_rpc.networks import Base
from eth_typeshed.erc20 import ERC20

from dowse.logger import logger


async def convert_token_amount_to_wei(amount: str, token_address: str) -> str:
    """
    convert a decimal token amount to wei
    """
    token = ERC20[Base](address=token_address)
    decimals = await token.decimals().get()
    return str(int(float(amount) * 10**decimals))


def convert_decimal_eth_to_wei(amount: str) -> str:
    """
    convert a decimal ETH amount to a string ETH amount.

    For example, an amount like 0.00123 ETH should be converted to 1230000000000000
    """
    result = str(int(float(amount) * 1e18)) + " ETH"
    logger.debug("Tool Call: convert_decimal_eth_to_wei (%s) -> '%s'", amount, result)
    return result

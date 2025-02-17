from eth_typeshed.erc20 import ERC20


async def convert_token_amount_to_wei(amount: str, token_address: str) -> str:
    """
    convert a decimal token amount to wei
    """
    token = ERC20(address=token_address)
    decimals = await token.decimals()
    return str(int(float(amount) * 10**decimals))

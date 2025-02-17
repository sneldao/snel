from eth_rpc import PrivateKeyWallet
from eth_rpc.types import primitives
from eth_typeshed import ERC20
from eth_typeshed.erc20 import TransferRequest
from eth_typing import HexAddress, HexStr


async def transfer_erc20(
    token_address: HexAddress,
    amount: int,
    recipient: HexAddress,
    wallet: PrivateKeyWallet,
) -> HexStr:
    contract = ERC20(address=token_address)
    tx_hash = await contract.transfer(
        TransferRequest(
            recipient=primitives.address(recipient),
            amount=primitives.uint256(amount),
        )
    ).execute(wallet)
    return tx_hash


async def transfer_eth(
    amount: int,
    recipient: HexAddress,
    wallet: PrivateKeyWallet,
) -> HexStr:
    tx_hash = await wallet.transfer(recipient, amount)
    return tx_hash

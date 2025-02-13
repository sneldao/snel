import math
from typing import Annotated

from eth_rpc import ContractFunc, ProtocolBase
from eth_rpc.networks import Base
from eth_rpc.types import METHOD, Name, primitives
from eth_rpc.utils import to_checksum
from eth_typing import ChecksumAddress


def number_to_bytes(number):
    if number < 2**32:
        hex_string = f"{hex(number)[2:]:0>8}"
    else:
        nibble_count = int(math.log(number, 256)) + 1
        hex_string = "{:0{}x}".format(number, nibble_count * 2)
    return bytes.fromhex(hex_string)[:32]


class XSource(ProtocolBase):
    lookup_address: Annotated[
        ContractFunc[primitives.bytes32, primitives.address],
        Name("lookupAddress"),
    ] = METHOD


async def get_user_address(
    twitter_id: int,
) -> ChecksumAddress:
    twitter_id_bytes = number_to_bytes(twitter_id)
    xsource = XSource[Base](address="0x12854780b007d717ebc4905e906253fc549254a9")
    return to_checksum(await xsource.lookup_address(twitter_id_bytes).get())

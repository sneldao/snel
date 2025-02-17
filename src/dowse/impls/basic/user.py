from eth_typing import HexAddress

from dowse.interfaces import UserManagerT
from dowse.tools import get_user_address_helper


class BasicUserManager(UserManagerT):
    async def get_user_address(self, user_id: str) -> HexAddress:
        user_address = await self.load_user_address(user_id)
        if user_address is None:
            user_address = await self.create_user_address(user_id)
        return user_address

    @staticmethod
    async def create_user_address(user_id: str) -> HexAddress:
        raise ValueError("Not needed, addresses are deterministic")

    @staticmethod
    async def load_user_address(user_id: str) -> HexAddress | None:
        return await get_user_address_helper(user_id)

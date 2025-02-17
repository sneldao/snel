from abc import ABC, abstractmethod

from eth_typing import HexAddress
from pydantic import BaseModel


class UserManagerT(ABC, BaseModel):
    @abstractmethod
    async def get_user_address(self, user_id: str) -> HexAddress:
        user_address = await self.load_user_address(user_id)
        if user_address is None:
            user_address = await self.create_user_address(user_id)
        return user_address

    @abstractmethod
    async def create_user_address(self, user_id: str) -> HexAddress:
        pass

    @abstractmethod
    async def load_user_address(self, user_id: str) -> HexAddress | None:
        pass

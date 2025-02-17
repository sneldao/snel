from abc import ABC, abstractmethod

from pydantic import BaseModel


class ContextT(ABC, BaseModel):
    @abstractmethod
    async def load_extra_context(self) -> str:
        """Load extra context for the LLM"""

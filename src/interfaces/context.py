from abc import ABC, abstractmethod


class ContextT(ABC):
    @abstractmethod
    async def load_extra_context(self) -> str:
        """Load extra context for the LLM"""

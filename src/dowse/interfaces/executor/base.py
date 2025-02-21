from abc import ABC, abstractmethod
from typing import Generic, TypeVar

from pydantic import BaseModel, Field

from dowse.models.message import AgentMessage

from ..effects import Effect

T = TypeVar("T", bound=BaseModel | str | None)
OutputType = TypeVar("OutputType", bound=BaseModel | str | None)


class ExecutorT(ABC, Generic[T, OutputType]):
    effects: list[Effect[T, OutputType]] = Field(default_factory=list)

    @abstractmethod
    async def execute(
        self,
        input_: T,
        persist: bool = False,
    ) -> AgentMessage[OutputType]:
        """
        Map the input to the output type
        """

    @abstractmethod
    async def after_execution(self, input_: T, output: OutputType) -> None:
        """A function that is called after the execution completes.
        Can also be overridden by subclasses to add post-execution behavior.

        Args:
            input_: The original input that was executed
            output: The output from the execution
        """

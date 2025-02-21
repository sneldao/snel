from typing import TYPE_CHECKING, Awaitable, Generic, Self, TypeVar

from pydantic import BaseModel

from dowse.models.message import AgentMessage

from ..effects import Effect
from .base import ExecutorT

if TYPE_CHECKING:
    from .chain import ChainExecutor

T = TypeVar("T", bound=BaseModel | str | None)
OutputType = TypeVar("OutputType", bound=BaseModel | str | None)
U = TypeVar("U", bound=BaseModel | str | None)


class Executor(ExecutorT[T, OutputType], BaseModel, Generic[T, OutputType]):
    async def execute(
        self,
        input_: T,
        persist: bool = False,
    ) -> AgentMessage[OutputType]:
        # NOTE: pydantic does not allow ABCs as parameter type args so we need to raise an error
        raise NotImplementedError("Subclasses must implement this method")

    async def after_execution(self, input_: T, output: OutputType) -> None:
        """A function that is called after the execution completes.
        Can also be overridden by subclasses to add post-execution behavior.

        Args:
            input_: The original input that was executed
            output: The output from the execution
        """
        for effect in self.effects:
            maybe_coro = effect.execute(input_, output)
            if isinstance(maybe_coro, Awaitable):
                await maybe_coro

    def __rshift__(
        self,
        other: "Executor[OutputType, U]",
    ) -> "ChainExecutor[T, OutputType, U]":
        from .chain import ChainExecutor

        return ChainExecutor(left_executor=self, right_executor=other)

    def add_effect(self, effect: Effect[T, OutputType]) -> Self:
        self.effects.append(effect)
        return self

    def add_effects(self, effects: list[Effect[T, OutputType]]) -> Self:
        self.effects.extend(effects)
        return self

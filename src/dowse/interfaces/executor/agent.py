import logging
from typing import Awaitable, Callable, Generic, Self, Type, TypeVar

from emp_agents import AgentBase
from emp_agents.models import Message, Provider
from emp_agents.providers import OpenAIModelType, OpenAIProvider
from emp_agents.utils import count_tokens
from pydantic import BaseModel, Field, PrivateAttr

from dowse.models.message import AgentMessage

from ..loaders import Loaders
from .executor import Executor

logger = logging.getLogger("dowse")

T = TypeVar("T", bound=BaseModel)
OutputType = TypeVar("OutputType", bound=BaseModel | str | None)


class AgentExecutor(
    Executor[T, OutputType],
    Loaders,
    Generic[T, OutputType],
):
    provider: Provider = Field(
        default_factory=lambda: OpenAIProvider(default_model=OpenAIModelType.gpt4o)
    )
    tools: list[Callable] = Field(default_factory=list)
    examples: list[list[Message]] = Field(default_factory=list)

    _agent: AgentBase | None = PrivateAttr(default=None)

    def set_provider(self, provider: Provider) -> Self:
        self.provider = provider
        return self

    async def load_tools(self, input_: T) -> list[Callable]:
        """This can be overriden by subclasses to provide tools dynamically"""
        return self.tools

    async def after_execution(self, input_: T, output: OutputType) -> None:
        """A function that is called after the execution completes.
        Can be overridden by subclasses to add post-execution behavior.

        Args:
            input_: The original input that was executed
            output: The output from the execution
        """
        for effect in self.effects:
            maybe_coro = effect.execute(input_, output)
            if isinstance(maybe_coro, Awaitable):
                await maybe_coro

    async def execute(
        self,
        input_: T,
        persist: bool = False,
    ) -> AgentMessage[OutputType]:
        response_format: Type[OutputType] = self._extract_response_format()

        if response_format is None:
            return AgentMessage[response_format](  # type: ignore[valid-type]
                content="",
                error_message=None,
            )

        if not self.prompt:
            raise ValueError("Prompt is required")

        if (not persist) or (self._agent is None):
            self._agent = AgentBase(
                prompt=self.prompt,
                provider=self.provider,
                tools=await self.load_tools(input_),
                sync_tools=True,
            )

        for example_lst in self.examples:
            self._agent.add_messages(example_lst)

        try:
            response: OutputType = await self._agent.answer(
                input_.model_dump_json(),
                response_format=response_format,  # type: ignore[arg-type]
            )  # type: ignore[assignment]
        except Exception as e:
            return AgentMessage[OutputType](
                content=None,
                error_message=str(e),
            )
        await self.after_execution(input_, response)

        return AgentMessage[OutputType](
            content=response,
            error_message=None,
        )

    async def ask(self, question: str) -> str:
        """Ask the current agent a question about the execution"""
        if self._agent is None:
            raise ValueError("Agent is not initialized")
        return await self._agent.answer(question)

    def reset_agent(self):
        """Reset the agent to its initial state"""
        self._agent.reset()

    def _extract_response_format(self) -> type[OutputType]:
        if type(self).__base__ is AgentExecutor:
            return type(self).__pydantic_generic_metadata__["args"][1]
        return type(self).__bases__[0].__pydantic_generic_metadata__["args"][1]  # type: ignore[attr-defined]

    def __repr__(self):
        return f"{self.__class__.__name__}"

    __str__ = __repr__

    def token_count(self) -> int:
        if self.prompt is None:
            return 0
        return count_tokens(self.prompt)

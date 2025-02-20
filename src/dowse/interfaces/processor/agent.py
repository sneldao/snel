import logging
from typing import Any, Callable, Generic, TypeVar

from emp_agents import AgentBase
from emp_agents.models import Provider
from emp_agents.providers import OpenAIModelType, OpenAIProvider
from pydantic import BaseModel, Field, ValidationError

from dowse.interfaces.loaders import Loaders
from dowse.models.message import AgentMessage

from .base import Processor

logger = logging.getLogger("dowse")

T = TypeVar("T", bound=BaseModel)
U = TypeVar("U", bound=BaseModel)


class AgenticProcessor(Processor[T, AgentMessage[U]], Loaders, Generic[T, U]):
    provider: Provider = OpenAIProvider(
        default_model=OpenAIModelType.gpt4o,
    )
    prompt: str | None = None
    tools: list[Callable] = Field(default_factory=list)

    def model_post_init(self, __context: Any) -> None:
        super().model_post_init(__context)
        # Override the examples and prompt from the class variables
        if not self.examples:
            self.examples = self._examples
        if self._prompt is not None:
            self.prompt = self._prompt

    async def to_string(self, command: T) -> str:
        """This can be overriden by subclasses to modify the command before formatting"""
        return command.model_dump_json()

    async def get_tools(self, command: T) -> list[Callable]:
        """This can be overriden by subclasses to provide tools dynamically"""
        return self.tools

    async def process(self, command: T) -> AgentMessage[U]:
        command_string = await self.to_string(command)
        tools = await self.get_tools(command)
        try:
            processed_result = await self._process(command_string, tools)
            return AgentMessage[U](content=processed_result, error_message=None)  # type: ignore[arg-type]
        except Exception as e:
            return AgentMessage[U](content=None, error_message=str(e))  # type: ignore[arg-type]

    async def _process(
        self,
        command: str,
        tools: list[Callable],
    ) -> U:
        if not self.prompt:
            raise ValueError("Prompt is required")
        agent = AgentBase(
            prompt=self.prompt,
            provider=self.provider,
            tools=tools,
        )

        for example in self.examples:
            agent.add_messages(example)

        response_content_type = self._extract_response_format()
        response_format = response_content_type

        response = await agent.answer(command, response_format=response_format)
        try:
            return response_content_type.model_validate_json(response)  # type: ignore[valid-type]
        except ValidationError as e:
            logger.error("Error serialization output: %s", e)
            raise e

    def _extract_response_format(self) -> type[U]:
        if type(self).__base__ is Processor:
            return type(self).__pydantic_generic_metadata__["args"][1]
        return type(self).__bases__[0].__pydantic_generic_metadata__["args"][1]  # type: ignore[attr-defined]

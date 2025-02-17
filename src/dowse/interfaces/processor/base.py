from abc import ABC
from typing import Any, Callable, Generic, TypeVar

from emp_agents import AgentBase
from emp_agents.models import Provider
from emp_agents.providers import OpenAIModelType, OpenAIProvider
from pydantic import BaseModel, Field

from dowse.interfaces.example_loader import ExampleLoader
from dowse.interfaces.prompt_loader import PromptLoader
from dowse.models.message import AgentMessage

T = TypeVar("T", bound=BaseModel)
U = TypeVar("U", bound=BaseModel)


class Processor(ABC, ExampleLoader, PromptLoader, Generic[T, U]):
    provider: Provider = OpenAIProvider(
        default_model=OpenAIModelType.gpt4o,
    )
    prompt: str = "Transform the input into the response format"
    tools: list[Callable] = Field(default_factory=list)

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        cls.load_prompt()
        cls.load_examples()

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

    async def format(self, command: T) -> AgentMessage[U]:
        command_string = await self.to_string(command)
        tools = await self.get_tools(command)
        return await self._format(command_string, tools)

    async def _format(self, command: str, tools: list[Callable]) -> AgentMessage[U]:
        agent = AgentBase(
            prompt=self.prompt,
            provider=self.provider,
            tools=tools,
        )

        for example in self.examples:
            agent.add_messages(example)

        response_content_type = self._extract_response_format()
        response_format = AgentMessage[response_content_type]  # type: ignore[valid-type]
        response_format.__name__ = "AgentMessage"

        response = await agent.answer(command, response_format=response_format)

        return AgentMessage[response_content_type].model_validate_json(response)  # type: ignore[valid-type]

    def _extract_response_format(self) -> type[U]:
        if type(self).__base__ is Processor:
            return type(self).__pydantic_generic_metadata__["args"][1]
        return type(self).__bases__[0].__pydantic_generic_metadata__["args"][1]  # type: ignore[attr-defined]

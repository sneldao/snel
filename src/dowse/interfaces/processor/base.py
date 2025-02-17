from abc import ABC
from typing import Callable, Generic, TypeVar

from emp_agents import AgentBase
from emp_agents.models import Provider
from emp_agents.providers import OpenAIModelType, OpenAIProvider
from pydantic import BaseModel, Field

from dowse.interfaces.prompt_loader import PromptLoader
from dowse.models.message import AgentMessage

T = TypeVar("T", bound=BaseModel)
U = TypeVar("U")


class Processor(PromptLoader, ABC, Generic[T, U]):
    provider: Provider = OpenAIProvider(
        default_model=OpenAIModelType.gpt4o,
    )
    prompt: str = "Transform the input into the response format"
    tools: list[Callable] = Field(default_factory=list)

    async def to_string(self, command: T) -> str:
        """This can be overriden by subclasses to modify the command before formatting"""
        return command.model_dump_json()

    async def get_tools(self, command: T) -> list[Callable]:
        """This can be overriden by subclasses to provide tools dynamically"""
        return self.tools

    async def format(self, command: T) -> AgentMessage[U]:
        command_string = await self.to_string(command)
        return await self._format(command_string)

    async def _format(self, command: str) -> AgentMessage[U]:
        agent = AgentBase(
            prompt=self.prompt,
            provider=self.provider,
            tools=await self.get_tools(command),
        )

        response_content_type = self._extract_response_format()
        response_format = AgentMessage[response_content_type]
        response_format.__name__ = "AgentMessage"

        response = await agent.answer(command, response_format=response_format)

        return AgentMessage[response_content_type].model_validate_json(response)

    def _extract_response_format(self) -> type[U]:
        if type(self).__base__ is Processor:
            return type(self).__pydantic_generic_metadata__["args"][1]
        return type(self).__bases__[0].__pydantic_generic_metadata__["args"][1]

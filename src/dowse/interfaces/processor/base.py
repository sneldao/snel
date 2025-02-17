from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Callable, Generic, TypeVar

from emp_agents import AgentBase
from emp_agents.models import Provider
from emp_agents.providers import OpenAIModelType, OpenAIProvider
from pydantic import BaseModel, Field

from dowse.models.message import AgentMessage

T = TypeVar("T")
U = TypeVar("U", bound=AgentMessage)


class Processor(BaseModel, ABC, Generic[T, U]):
    provider: Provider = OpenAIProvider(
        default_model=OpenAIModelType.gpt4o,
    )
    prompt: str | None = None
    tools: list[Callable] = Field(default_factory=list)

    def model_post_init(self, __context: Any) -> None:
        import inspect

        stack = inspect.stack()

        caller_frame = None
        for frame_info in stack:
            filename = frame_info.filename
            if "pydantic" not in filename and filename != __file__:
                caller_frame = frame_info
                break

        self._path = Path(caller_frame.filename).parent

        prompt_path = self._path / "PROMPT.txt"
        if prompt_path.exists():
            self.prompt = prompt_path.read_text()

    async def get_tools(self, command: T) -> list[Callable]:
        """This can be overriden by subclasses to provide tools dynamically"""
        return self.tools

    @abstractmethod
    async def to_string(self, command: T) -> str:
        """This can be overriden by subclasses to modify the command before formatting"""

    async def format(self, command: T) -> AgentMessage[U]:
        command_string = await self.to_string(command)
        return await self._format(command_string)

    async def _format(self, command: T) -> AgentMessage[U]:
        agent = AgentBase(
            prompt=self.prompt,
            provider=self.provider,
            tools=await self.get_tools(command),
        )

        response_content_type = (
            type(self).__bases__[0].__pydantic_generic_metadata__["args"][1]
        )
        # (_, response_content_type) = type(self).__pydantic_generic_metadata__["args"]
        response_format = AgentMessage[response_content_type]
        response_format.__name__ = "AgentMessage"

        response = await agent.answer(command, response_format=response_format)

        return AgentMessage[response_content_type].model_validate_json(response)

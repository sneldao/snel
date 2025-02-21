from typing import Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class AgentMessage(BaseModel, Generic[T]):
    content: T | None = Field(
        description="The content of the message.  If the agent is unable to complete the task, set this to None",
    )
    error_message: str | None = Field(
        description="An optional error message.  Only provide this if content is None",
    )

    @property
    def is_error(self) -> bool:
        return self.error_message is not None

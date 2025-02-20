import logging
from typing import Generic, TypeVar

from pydantic import BaseModel, Field

from dowse.exceptions import PreprocessorError
from dowse.models.message import AgentMessage

from ..loaders import Loaders
from .agent import Processor

T = TypeVar("T")
U = TypeVar("U", bound=BaseModel)

logger = logging.getLogger("dowse")


class PreProcess(Loaders, Generic[T, U]):
    processors: list[Processor] = Field(default_factory=list)

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)

    async def run_processors(self, input_: T) -> AgentMessage[U]:
        processed_data = input_
        if not self.processors:
            return AgentMessage(content=processed_data, error_message=None)  # type: ignore[arg-type]

        for processor in self.processors:
            logger.debug("Running preprocessor: %s", processed_data)
            processed_data: AgentMessage = await processor.process(processed_data)  # type: ignore[no-redef]
            logger.debug("Preprocessor result: %s", processed_data)
            if processed_data.error_message is not None:  # type: ignore[attr-defined]
                raise PreprocessorError(processed_data.error_message)  # type: ignore[attr-defined]
        return processed_data  # type: ignore

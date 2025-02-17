import logging
from typing import Generic, TypeVar

from pydantic import BaseModel

from dowse.exceptions import PreprocessorError
from dowse.models.message import AgentMessage

from .base import Processor

T = TypeVar("T")
U = TypeVar("U", bound=AgentMessage)

logger = logging.getLogger("dowse")


class PreProcess(BaseModel, Generic[T, U]):
    preprocessors: list[Processor]

    async def run_preprocessors(self, input_: T) -> AgentMessage[U]:
        processed_data = input_
        if not self.preprocessors:
            return AgentMessage(content=processed_data, error_message=None)

        for preprocessor in self.preprocessors:
            logger.debug("Running preprocessor: %s", processed_data)
            processed_data = await preprocessor.format(processed_data)
            logger.debug("Preprocessor result: %s", processed_data)
            if processed_data.error_message is not None:
                raise PreprocessorError(processed_data.error_message)
        return processed_data

import asyncio
import logging
import sys
import time
from typing import Generic, TypeVar

from pydantic import BaseModel, Field

from dowse.exceptions import PreprocessorError
from dowse.interfaces import SourceT
from dowse.interfaces.executor import Executor
from dowse.interfaces.llms.classifier import Classifier
from dowse.interfaces.processor.base import Processor
from dowse.models.message import AgentMessage

logger = logging.getLogger("dowse")

T = TypeVar("T")
U = TypeVar("U")
Classifications = TypeVar("Classifications")


class Pipeline(BaseModel, Generic[T, Classifications]):
    """
    A pipeline is a sequence of preprocessors, a classifier, and a mapping of classifications to handlers.

    Args:
        T: The input type to the pipeline
        U: The intermediate type after preprocessing
        Classifications: The possible classifications from the classifier
        Response: The type of the response from the handlers
    """

    processors: list[Processor] = Field(default_factory=list)
    classifier: Classifier[U, Classifications]
    handlers: dict[Classifications, Executor]
    source: SourceT[T] | None = None

    async def run_processors(self, input_: T) -> AgentMessage[U]:
        if not self.processors:
            return AgentMessage(content=input_, error_message=None)

        for processor in self.processors:
            input_ = await processor.format(input_)
            if input_.is_error:
                raise PreprocessorError(input_.error_message)

        return input_

    async def process(self, input_: T) -> AgentMessage:
        processed_input = await self.run_processors(input_)

        logger.debug("Processed input: %s", processed_input)

        classification = await self.classifier.classify(processed_input.content)

        logger.debug("Classified as: %s", classification)

        response = await self.handlers[classification].execute(processed_input.content)

        logger.debug("Response: %s", response)

        return response

    async def run(
        self, max_executions: int = sys.maxsize, iteration_min_time: int = 0
    ) -> None:
        """A function to run the execution loop for the intent executor"""

        count = 0
        if self.source is None:
            raise ValueError("Source is not set")

        while count < max_executions:
            loop_start_time = time.time()
            data = await self.source.get_data()
            for item in data:
                logger.info("ITEM FOUND: %s", item)

                await self.process(item)

            count += 1

            loop_end_time = time.time()
            loop_time = loop_end_time - loop_start_time

            if loop_time < iteration_min_time:
                await asyncio.sleep(iteration_min_time - loop_time)

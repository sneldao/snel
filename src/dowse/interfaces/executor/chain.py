from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict

from dowse.models.message import AgentMessage

from .executor import Executor, ExecutorT

T = TypeVar("T")
InputType = TypeVar("InputType", bound=BaseModel | str | None)
IntermediateType = TypeVar("IntermediateType", bound=BaseModel | str | None)
OutputType = TypeVar("OutputType", bound=BaseModel | str | None)


class ChainExecutor(
    Executor[InputType, OutputType],
    BaseModel,
    Generic[InputType, IntermediateType, OutputType],
):
    left_executor: ExecutorT[InputType, IntermediateType]
    right_executor: ExecutorT[IntermediateType, OutputType]

    model_config = ConfigDict(
        arbitrary_types_allowed=True,  # Needed to allow non-BaseModel types
    )

    async def execute(
        self,
        input_: InputType,
        persist: bool = False,
    ) -> AgentMessage[OutputType]:
        print(self.left_executor, type(self.left_executor))
        print(self.right_executor, type(self.right_executor))
        intermediate = await self.left_executor.execute(input_, persist=persist)

        if intermediate.error_message:
            return AgentMessage[OutputType](
                content=None,
                error_message=intermediate.error_message,
            )

        assert intermediate.content is not None
        return await self.right_executor.execute(intermediate.content, persist=persist)

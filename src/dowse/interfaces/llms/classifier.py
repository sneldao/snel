from abc import ABC
from pathlib import Path
from typing import Any, Generic, Literal, TypeVar, get_args

from emp_agents import AgentBase
from emp_agents.models import Provider
from emp_agents.providers import OpenAIModelType, OpenAIProvider
from pydantic import BaseModel, PrivateAttr

from ..prompt_loader import PromptLoader

InputType = TypeVar("InputType", bound=BaseModel)
Classifications = TypeVar(
    "Classifications",
)

T = TypeVar("T")


class ClassifierResponse(BaseModel, Generic[T]):
    __name__ = "ClassifierResponse"
    classification: T


class Classifier(ABC, PromptLoader, Generic[InputType, Classifications]):
    prompt: str = (
        "classify the input into the response_format.  Respond with the classification and nothing else."
    )

    provider: Provider = OpenAIProvider(
        default_model=OpenAIModelType.gpt4o,
    )

    _agent: AgentBase = PrivateAttr()

    def model_post_init(self, __context: Any) -> None:
        import inspect

        stack = inspect.stack()

        caller_frame: inspect.FrameInfo | None = None
        for frame_info in stack:
            filename = frame_info.filename
            if "pydantic" not in filename and filename != __file__:
                caller_frame = frame_info
                break

        assert caller_frame is not None
        self._path = Path(caller_frame.filename).parent

        prompt_path = self._path / "PROMPT.txt"
        if prompt_path.exists():
            self.prompt = prompt_path.read_text()

        self._agent = AgentBase(
            prompt=self.prompt,
            provider=self.provider,
        )
        if len(type(self).__pydantic_generic_metadata__["args"]) != 2:
            raise ValueError("Classifier must have input type and classifications set")

    async def classify(
        self,
        message: InputType,
    ) -> Classifications:
        (_, classifications) = type(self).__pydantic_generic_metadata__["args"]

        classification_type = get_args(get_args(Literal[*classifications])[0])[0]  # type: ignore

        response_type = ClassifierResponse[classification_type]
        response_type.__name__ = "ClassifierResponse"

        response = await self._agent.answer(
            message.model_dump_json(),
            response_format=response_type,
        )
        return ClassifierResponse.model_validate_json(response).classification

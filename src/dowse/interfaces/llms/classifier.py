from abc import ABC
from enum import Enum
from inspect import isclass
from typing import Any, Generic, Literal, Self, TypeVar, get_args, get_origin

from emp_agents import AgentBase
from emp_agents.models import Provider
from emp_agents.providers import OpenAIModelType, OpenAIProvider
from pydantic import BaseModel, PrivateAttr

from dowse.interfaces.loaders import Loaders

InputType = TypeVar("InputType", bound=BaseModel)
Classifications = TypeVar(
    "Classifications",
)

T = TypeVar("T")


class ClassifierResponse(BaseModel, Generic[T]):
    __name__ = "ClassifierResponse"
    classification: T


class Classifier(ABC, Loaders, Generic[InputType, Classifications]):
    prompt: str = (
        "classify the input into the response_format.  Respond with the classification and nothing else."
    )
    provider: Provider = OpenAIProvider(
        default_model=OpenAIModelType.gpt4o,
    )

    def update_provider(self, provider: Provider) -> Self:
        self.provider = provider
        return self

    _agent: AgentBase = PrivateAttr()

    def model_post_init(self, __context: Any) -> None:
        super().model_post_init(__context)

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

        if get_origin(classifications) == Literal:
            classification_type = get_args(get_args(Literal[*classifications])[0])[0]  # type: ignore
        elif isclass(classifications) and issubclass(classifications, Enum):
            classification_type = classifications
        else:
            raise ValueError("Invalid classifications type")

        response_type = ClassifierResponse[classification_type]  # type: ignore[valid-type]
        response_type.__name__ = "ClassifierResponse"

        response = await self._agent.answer(
            message.model_dump_json(),
            response_format=response_type,
        )
        return response.classification

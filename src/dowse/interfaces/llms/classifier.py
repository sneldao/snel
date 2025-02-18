from abc import ABC
from typing import Any, Generic, Literal, Self, TypeVar, get_args

from emp_agents import AgentBase
from emp_agents.models import Provider
from emp_agents.providers import OpenAIModelType, OpenAIProvider
from pydantic import BaseModel, PrivateAttr

from ..example_loader import ExampleLoader
from ..prompt_loader import PromptLoader

InputType = TypeVar("InputType", bound=BaseModel)
Classifications = TypeVar(
    "Classifications",
)

T = TypeVar("T")


class ClassifierResponse(BaseModel, Generic[T]):
    __name__ = "ClassifierResponse"
    classification: T


class Classifier(ABC, ExampleLoader, PromptLoader, Generic[InputType, Classifications]):
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

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        cls.load_examples()
        cls.load_prompt()

    def model_post_init(self, __context: Any) -> None:
        super().model_post_init(__context)

        self._agent = AgentBase(
            prompt=self.prompt,
            provider=self.provider,
        )
        if len(type(self).__pydantic_generic_metadata__["args"]) != 2:
            raise ValueError("Classifier must have input type and classifications set")

        if self._prompt is not None:
            self.prompt = self._prompt
        if self._examples:
            self.examples = self._examples

    async def classify(
        self,
        message: InputType,
    ) -> Classifications:
        (_, classifications) = type(self).__pydantic_generic_metadata__["args"]

        classification_type = get_args(get_args(Literal[*classifications])[0])[0]  # type: ignore

        response_type = ClassifierResponse[classification_type]  # type: ignore[valid-type]
        response_type.__name__ = "ClassifierResponse"

        response = await self._agent.answer(
            message.model_dump_json(),
            response_format=response_type,
        )
        return ClassifierResponse.model_validate_json(response).classification

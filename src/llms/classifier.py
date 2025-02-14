from typing import Literal

from emp_agents import AgentBase
from emp_agents.providers import OpenAIModelType, OpenAIProvider
from pydantic import BaseModel

from ..prompts import CLASSIFIER_PROMPT


class ClassifierResponse(BaseModel):
    classification: Literal["commands", "question", "not_talking"]


classifier = AgentBase(
    prompt=CLASSIFIER_PROMPT,
    provider=OpenAIProvider(
        default_model=OpenAIModelType.gpt4o,
    ),
)


async def classify_message(
    message: str,
) -> Literal["commands", "question", "not_talking"]:
    response = await classifier.answer(message, response_format=ClassifierResponse)
    return ClassifierResponse.model_validate_json(response).classification

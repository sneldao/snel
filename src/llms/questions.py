from emp_agents import AgentBase
from emp_agents.providers import OpenAIModelType, OpenAIProvider

from ..interfaces import ContextT
from ..prompts import QUESTION_PROMPT

classifier = AgentBase(
    prompt=QUESTION_PROMPT,
    provider=OpenAIProvider(
        default_model=OpenAIModelType.gpt4o,
    ),
)


async def handle_question(
    message: str,
    context_helper: ContextT,
) -> str:
    """
    Classify a message as a question or not a question
    """

    extra_context = await context_helper.load_extra_context()
    classifier.prompt = (
        classifier.prompt + f"Also use this extra context:\n{extra_context}"
    )
    response = await classifier.answer(message)
    return response

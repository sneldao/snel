from app.utils.models import AssistantMessage, UserMessage  # Updated from emp_agents

EXAMPLES = [
    [
        UserMessage(content="Tell me about 02108"),
        AssistantMessage(content="02108 is Boston, MA, it's a great city."),
        UserMessage(
            content="Hey! remember you can't use the letter 'e' in your response."
        ),
        AssistantMessage(content="oh no. ok. i'll try not to do it again"),
    ]
]

from emp_agents.models import AssistantMessage, UserMessage

EXAMPLES = [
    [
        UserMessage(content="What is the weather in San Francisco?"),
        AssistantMessage(content="The weather in San Francisco is sunny."),
        UserMessage(
            content="Hey! remember you can't use the letter 'e' in your response."
        ),
        AssistantMessage(content="oh shit. ok. i'll try not to use it again"),
    ]
]

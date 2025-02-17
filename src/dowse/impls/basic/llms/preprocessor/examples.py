# flake8: noqa

from emp_agents.models import AssistantMessage, ToolCall, ToolMessage, UserMessage

EXAMPLES = [
    [
        UserMessage(content='{"caller": "@user", "content": "swap $100 for AERO"}'),
        AssistantMessage(
            content="I will use my tools to get the token address for AERO",
            tool_calls=[
                ToolCall(
                    id="57d74922-3636-49b1-8109-fe25ca66ca19",
                    type="function",
                    function=ToolCall.Function(
                        name="get_token_address_tool",
                        arguments='{"symbol_or_token_address": "AERO"}',
                    ),
                ),
                ToolCall(
                    id="0b73576d-413a-4fb8-8fe4-99da789fb0e1",
                    type="function",
                    function=ToolCall.Function(
                        name="convert_dollar_amount_to_eth",
                        arguments='{"amount": "123123.1231"}',
                    ),
                ),
            ],
        ),
        ToolMessage(
            tool_call_id="57d74922-3636-49b1-8109-fe25ca66ca19",
            content="0x940181a94A35A4569E4529A3CDfB74e38FD98631",
        ),
        ToolMessage(
            tool_call_id="0b73576d-413a-4fb8-8fe4-99da789fb0e1", content="2.9649"
        ),
        AssistantMessage(
            content='{"content": {"caller": "@user", "user_request": "swap 123123.1231 ETH (0x4200000000000000000000000000000000000006) for $AERO (0x940181a94A35A4569E4529A3CDfB74e38FD98631)", "error_message": null}}'
        ),
        UserMessage(
            content="Ok Great, now lets ignore these values but use this as the general structure of how the processing should go",
        ),
        AssistantMessage(content="I understand."),
    ],
]

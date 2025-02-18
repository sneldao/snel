import json

from emp_agents.models import AssistantMessage, ToolCall, ToolMessage, UserMessage

EXAMPLES = [
    [
        UserMessage(
            content=json.dumps(
                {
                    "caller": "@user",
                    "content": (
                        "#simmi Whats up?  I want you to swap $123.13 for AERO"
                        " and then send half of it to @user2.  Can you do that for me now?"
                    ),
                }
            )
        ),
        AssistantMessage(
            content=(
                'Ok, I can convert simplify this command to "1. swap $123.13 for $AERO\n'
                '2. transfer 50% of the output to @user2" and then use my tools to further refine'
            ),
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
                        arguments='{"amount": "$123.13"}',
                    ),
                ),
            ],
        ),
        ToolMessage(
            tool_call_id="57d74922-3636-49b1-8109-fe25ca66ca19",
            content="0x940181a94A35A4569E4529A3CDfB74e38FD98631",
        ),
        ToolMessage(
            tool_call_id="0b73576d-413a-4fb8-8fe4-99da789fb0e1",
            content="46200000000000000 ETH",
        ),
        AssistantMessage(
            content=json.dumps(
                {
                    "caller": "@user",
                    "user_request": (
                        "1. swap 46200000000000000 ETH (0x4200000000000000000000000000000000000006)"
                        " for $AERO (0x940181a94A35A4569E4529A3CDfB74e38FD98631)\n"
                        "2. send 50% of the output to @user2"
                    ),
                }
            ),
        ),
        UserMessage(
            content="Ok Great, lets try this for a more complicated case",
        ),
        AssistantMessage(content="I understand."),
    ],
]

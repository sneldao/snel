# flake8: noqa: E501

import json

from emp_agents.models import AssistantMessage, ToolCall, ToolMessage, UserMessage

EXAMPLES = [
    [
        UserMessage(
            content="{'caller': '@jack', 'content': '1. swap 10000000000000000 ETH (0x4200000000000000000000000000000006) for $AERO (0x940181a94A35A4569E4529A3CDfB74e38FD98631)'}"
        ),
        AssistantMessage(
            content="Lets determine the amount of tokens that will be the output of this swap",
            tool_calls=[
                ToolCall(
                    id="c4649732-4cc9-47e4-bc48-88224566686b",
                    type="function",
                    function=ToolCall.Function(
                        name="get_amount_out_tool",
                        arguments='{"token_in_address": "0x4200000000000000000000000000000006", "token_out_address": "0x940181a94A35A4569E4529A3CDfB74e38FD98631", "amount": "10000000000000000"}',
                    ),
                )
            ],
        ),
        ToolMessage(
            tool_call_id="c4649732-4cc9-47e4-bc48-88224566686b",
            content="1394601928424631358765",
        ),
        AssistantMessage(
            content="""
            {
                "commands": [
                    {"command": "swap", "args": {"token_in_address": "0x4200000000000000000000000000000006", "token_out_address": "0x940181a94A35A4569E4529A3CDfB74e38FD98631", "amount_in": "3000000000000000", "amount_out": "1394601928424631358765", "recipient": "@jack"}},
                ],
                "error_message": None,
            }
            """,
        ),
    ],
    [
        UserMessage(
            content="{'caller': '@abc123', 'content': 'swap 3000000000000000 ETH (0x4200000000000000000000000000000000000006) for $AIXBT (0x4F9Fd6Be4a90f2620860d680c0d4d5Fb53d1A825) and send half of it to @myfriend'}"
        ),
        AssistantMessage(
            content="Lets determine the amount of tokens that will be the output of this swap",
            tool_calls=[
                ToolCall(
                    id="c4649732-4cc9-47e4-bc48-88224566686b",
                    type="function",
                    function=ToolCall.Function(
                        name="get_amount_out_tool",
                        arguments='{"token_in_address": "0x4200000000000000000000000000000000000006", "token_out_address": "0x4F9Fd6Be4a90f2620860d680c0d4d5Fb53d1A825", "amount": "3000000000000000"}',
                    ),
                )
            ],
        ),
        ToolMessage(
            tool_call_id="c4649732-4cc9-47e4-bc48-88224566686b",
            content="1394601928424631358765",
        ),
        AssistantMessage(
            content="Lets use the percentage tool to get half of the amount out",
            tool_calls=[
                ToolCall(
                    id="c4649732-4cc9-47e4-bc48-88224566686b",
                    type="function",
                    function=ToolCall.Function(
                        name="get_percentage",
                        arguments='{"amount": "1394601928424631358765", "percentage": "50"}',
                    ),
                )
            ],
        ),
        ToolMessage(
            tool_call_id="c4649732-4cc9-47e4-bc48-88224566686b",
            content="697300964212315679382",
        ),
        AssistantMessage(
            content="""
            {
                "commands": [
                    {"command": "swap", "args": {"token_in_address": "0x4200000000000000000000000000000006", "token_out_address": "0x4F9Fd6Be4a90f2620860d680c0d4d5Fb53d1A825", "amount_in": "3000000000000000", "amount_out": "1394601928424631358765", "recipient": "@user"}},
                    {"command": "transfer", "args": {"token_address": "0x4F9Fd6Be4a90f2620860d680c0d4d5Fb53d1A825", "amount": "697300964212315679382", "recipient": "@myfriend"}}
                ],
            }
            """,
        ),
    ],
    [
        UserMessage(content="ok now i'm going to send you a new user's commands"),
        AssistantMessage(
            content="ok, i'll wait",
        ),
    ],
]

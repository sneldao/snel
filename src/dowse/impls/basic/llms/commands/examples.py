# flake8: noqa: E501

import json

from emp_agents.models import AssistantMessage, ToolCall, ToolMessage, UserMessage

EXAMPLES = [
    [
        UserMessage(
            content="{'caller': '@jack', 'content': 'swap 10000000000000000 ETH (0x4200000000000000000000000000000006) for $AERO (0x940181a94A35A4569E4529A3CDfB74e38FD98631)'}"
        ),
        AssistantMessage(
            content="Let's use our swap tool to build this transaction",
            tool_calls=[
                ToolCall(
                    id="c4649732-4cc9-47e4-bc48-88224566686b",
                    type="function",
                    function=ToolCall.Function(
                        name="make_swap_command",
                        arguments='{"token_in": "0x4200000000000000000000000000000006", "token_out": "0x940181a94A35A4569E4529A3CDfB74e38FD98631", "amount": "10000000000000000", "recipient": "@jack"}',
                    ),
                )
            ],
        ),
        ToolMessage(
            tool_call_id="c4649732-4cc9-47e4-bc48-88224566686b",
            content=json.dumps(
                {
                    "amount_out": "1394601928424631358765",
                    "aggregator": "Paraswap",
                    "input_token_symbol": "$ETH",
                    "input_token_address": "0x4200000000000000000000000000000006",
                    "output_token": "$AERO",
                    "output_token_address": "0x940181a94A35A4569E4529A3CDfB74e38FD98631",
                }
            ),
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
            content="{'caller': '@abc123', 'content': 'swap for 3000000000000000 ETH (0x4200000000000000000000000000000000000006) for $AIXBT (0x4F9Fd6Be4a90f2620860d680c0d4d5Fb53d1A825) and send half of it to @myfriend'}"
        ),
        AssistantMessage(
            content="Let's use our swap tool to build this transaction",
            tool_calls=[
                ToolCall(
                    id="c4649732-4cc9-47e4-bc48-88224566686b",
                    type="function",
                    function=ToolCall.Function(
                        name="make_swap_command",
                        arguments='{"token_in": "0x4200000000000000000000000000000000000006", "token_out": "0x4F9Fd6Be4a90f2620860d680c0d4d5Fb53d1A825", "amount": "3000000000000000", "recipient": "@abc123"}',
                    ),
                )
            ],
        ),
        ToolMessage(
            tool_call_id="c4649732-4cc9-47e4-bc48-88224566686b",
            content='{"amount_out": "1394601928424631358765", "aggregator": "Paraswap", "input_token_symbol": "ETH", "input_token_address": "0x4200000000000000000000000000000000000006", "output_token_symbol": "AIXBT", "output_token_address": "0x4F9Fd6Be4a90f2620860d680c0d4d5Fb53d1A825"}',
        ),
        AssistantMessage(
            content="Let's use our transfer tools to build this transaction",
            tool_calls=[
                ToolCall(
                    id="5bcd249f-45e6-415f-8582-bd32af4d84aa",
                    type="function",
                    function=ToolCall.Function(
                        name="make_transfer_command",
                        arguments='{"token": "0x4F9Fd6Be4a90f2620860d680c0d4d5Fb53d1A825", "amount": "697300964212315679382", "sender": "@abc123", "recipient": "@myfriend"}',
                    ),
                )
            ],
        ),
        ToolMessage(
            tool_call_id="5bcd249f-45e6-415f-8582-bd32af4d84aa",
            content='{"token_symbol": "AERO", "token_address": "0x4F9Fd6Be4a90f2620860d680c0d4d5Fb53d1A825", "recipient": "@myfriend", "value": "697300964212315679382"}',
        ),
        AssistantMessage(
            content="""
            {
                "commands": [
                    {"command": "swap", "args": {"token_in_address": "0x4200000000000000000000000000000006", "token_out_address": "0x4F9Fd6Be4a90f2620860d680c0d4d5Fb53d1A825", "amount_in": "3000000000000000", "amount_out": "1394601928424631358765", "recipient": "@user"}},
                    {"command": "transfer", "args": {"token_address": "0x4F9Fd6Be4a90f2620860d680c0d4d5Fb53d1A825", "amount": "697300964212315679382", "recipient": "@myfriend"}}
                ],
                "error_message": None,
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

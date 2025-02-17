# flake8: noqa: E501

from emp_agents.models import AssistantMessage, ToolCall, ToolMessage, UserMessage

EXAMPLES = [
    [
        UserMessage(
            content="{'caller': '@user', 'content': 'swap .01 ETH (0x4200000000000000000000000000000006) for $AERO (0x940181a94A35A4569E4529A3CDfB74e38FD98631)'}"
        ),
        AssistantMessage(
            content="let's convert the decimal to ETH and lookup the $AERO token address",
            tool_calls=[
                ToolCall(
                    id="aad543ba-f689-4101-9dfb-43d0f81f1a6f",
                    type="function",
                    function=ToolCall.Function(
                        name="convert_decimal_eth_to_wei",
                        arguments='{"amount": "0.01"}',
                    ),
                )
            ],
        ),
        ToolMessage(
            tool_call_id="aad543ba-f689-4101-9dfb-43d0f81f1a6f",
            content="10000000000000000",
        ),
        AssistantMessage(
            content="Let's use our swap tool to build this transaction",
            tool_calls=[
                ToolCall(
                    id="c4649732-4cc9-47e4-bc48-88224566686b",
                    type="function",
                    function=ToolCall.Function(
                        name="make_swap_command",
                        arguments='{"token_in": "0x4200000000000000000000000000000006", "token_out": "0x940181a94A35A4569E4529A3CDfB74e38FD98631", "amount": "10000000000000000", "recipient": "@user"}',
                    ),
                )
            ],
        ),
        ToolMessage(
            tool_call_id="c4649732-4cc9-47e4-bc48-88224566686b",
            content='{"amount_out": "1394601928424631358765", "aggregator": "Paraswap", "input_token_symbol": "$ETH", "input_token_address": "0x4200000000000000000000000000000006", "output_token": "$AERO", "output_token_address": "0x940181a94A35A4569E4529A3CDfB74e38FD98631"}',
        ),
        AssistantMessage(
            content="""
            {
                "commands": [
                    {"command": "swap", "args": {"token_in_address": "0x4200000000000000000000000000000006", "token_out_address": "0x940181a94A35A4569E4529A3CDfB74e38FD98631", "amount_in": "3000000000000000", "amount_out": "1394601928424631358765", "recipient": "@user"}},
                ],
                "error_message": None,
            }
            """,
        ),
    ],
    [
        UserMessage(
            content="{'caller': '@user', 'content': 'swap for 0.003 ETH (0x4200000000000000000000000000000000000006) for $AIXBT (0x4F9Fd6Be4a90f2620860d680c0d4d5Fb53d1A825) and send half of it to @myfriend'}"
        ),
        AssistantMessage(
            content="Let's use our tools to convert the 0.003 ETH to an amount in wei",
            tool_calls=[
                ToolCall(
                    id="a6f8f1f1-aaeb-43e1-82a4-ad1cbf704fe1",
                    type="function",
                    function=ToolCall.Function(
                        name="convert_decimal_eth_to_wei",
                        arguments='{"amount": "0.003"}',
                    ),
                )
            ],
        ),
        ToolMessage(
            tool_call_id="a6f8f1f1-aaeb-43e1-82a4-ad1cbf704fe1",
            content="3000000000000000",
        ),
        AssistantMessage(
            content="Let's use our swap tool to build this transaction",
            tool_calls=[
                ToolCall(
                    id="c4649732-4cc9-47e4-bc48-88224566686b",
                    type="function",
                    function=ToolCall.Function(
                        name="make_swap_command",
                        arguments='{"token_in": "0x4200000000000000000000000000000000000006", "token_out": "0x4F9Fd6Be4a90f2620860d680c0d4d5Fb53d1A825", "amount": "3000000000000000", "recipient": "@user"}',
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
                        arguments='{"token": "0x4F9Fd6Be4a90f2620860d680c0d4d5Fb53d1A825", "amount": "697300964212315679382", "sender": "@user", "recipient": "@myfriend"}',
                    ),
                )
            ],
        ),
        ToolMessage(
            tool_call_id="5bcd249f-45e6-415f-8582-bd32af4d84aa",
            content='{"token_symbol": "AERO", "token_address": "0x4F9Fd6Be4a90f2620860d680c0d4d5Fb53d1A825", "sender": "@user", "recipient": "@myfriend", "value": "697300964212315679382"}',
        ),
        AssistantMessage(
            content="""
            {
                "commands": [
                    {"command": "swap", "args": {"token_in_address": "0x4200000000000000000000000000000006", "token_out_address": "0x4F9Fd6Be4a90f2620860d680c0d4d5Fb53d1A825", "amount_in": "3000000000000000", "amount_out": "1394601928424631358765", "recipient": "@user"}},
                    {"command": "transfer", "args": {"token_address": "0x4F9Fd6Be4a90f2620860d680c0d4d5Fb53d1A825", "amount": "697300964212315679382", "sender": "@user", "recipient": "@myfriend"}}
                ],
                "error_message": None,
            }
            """,
        ),
    ],
    [
        UserMessage(
            content="{'caller': '@user', 'content': 'transfer 0.003 ETH (0x4200000000000000000000000000000000000006) to @myfriend'}"
        ),
        AssistantMessage(
            content="Let's use our transfer tools to build this transaction",
            tool_calls=[
                ToolCall(
                    id="2372fee1-1f62-47d6-835d-c0bc29f2236e",
                    type="function",
                    function=ToolCall.Function(
                        name="convert_decimal_eth_to_wei",
                        arguments='{"amount": "0.003"}',
                    ),
                ),
            ],
        ),
        ToolMessage(
            tool_call_id="2372fee1-1f62-47d6-835d-c0bc29f2236e",
            content="3000000000000000",
        ),
        AssistantMessage(
            content="Let's use our transfer tools to build this transaction",
            tool_calls=[
                ToolCall(
                    id="f06b6ed2-a09a-4456-9595-8cbfa9826c1e",
                    type="function",
                    function=ToolCall.Function(
                        name="make_transfer_command",
                        arguments='{"token": "0x4200000000000000000000000000000000000006", "amount": "3000000000000000", "sender": "@user", "recipient": "@myfriend"}',
                    ),
                )
            ],
        ),
        ToolMessage(
            tool_call_id="f06b6ed2-a09a-4456-9595-8cbfa9826c1e",
            content='{"token": "ETH", "token_address": "0x4200000000000000000000000000000000000006", "from": "@user", "to": "@myfriend", "value": "3000000000000000"}',
        ),
        AssistantMessage(
            content="""
            {
                "commands": [
                    {"command": "transfer", "args": {"token_address": "0x4200000000000000000000000000000000000006", "amount": "3000000000000000", "sender": "@user", "recipient": "@myfriend"}}
                ],
                "error_message": None,
            }
            """,
        ),
    ],
]

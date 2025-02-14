# llm-conversion


### QUICKSTART

Setup your .env with the required variables
```
TWITTER_BEARER_TOKEN=
QUICKNODE_ENDPOINT=
MORALIS_API_KEY=
```

Also enable the [DEX Aggregator Trading API](https://marketplace.quicknode.com/add-on/dex-aggregator-trading-api)

Then you can run the project via:

```bash
python main.py
```

---

# Command Structure

I included the commands in the format, but you could pretty easily modify this.
```
"@username says: {command}"
```

---

# Project Layout

> Overview of the general project layout

    .
    |-- interfaces/              # Interfaces for twitter and executor to generalize the implementation
    |-- impls/                   # Implementations of the interfaces
    |-- llms/                    # LLM for classification and handling commands/questions
    |-- prompts/                 # Prompts for the LLM
    ├── tools/                   # Tools that the LLM can use
    ├── utils/                   # Utility functions
    ├── __main__.py              # The main file to run the project

---

# Example Output


![An image of the output from a run](./assets/screenshot.png?raw=true "Command Execution")

As you can see, the command execution converts the command given by the user into a JSON object with a list of steps to be executed synchronously.  This can easily be adapted to a variety of executors.  I included utils to convert this to Simulacrum addresses (which won't work for this example because we do not have control over user wallets), but it could be adapted to any sort of centralized execution framework.

```json
{
  "requests": [
    {
      "command": "swap",
      "args": {
        "tokenIn": "ETH",
        "tokenOut": "BNKR",
        "tokenInAddress": "0x4200000000000000000000000000000000000006",
        "tokenOutAddress": "0x22aF33FE49fD1Fa80c7149773dDe5890D3c76F3b",
        "amountIn": 3708919739531472,
        "amountOut": 4.492617197965086e+22,
        "slippage": 0.01,
        "sender": "0xDeployer",
        "senderAddress": "0xE8c408c5838b3734a39CcE7e645B4E88F093779b",
        "recipient": "0xDeployer",
        "recipientAddress": "0xE8c408c5838b3734a39CcE7e645B4E88F093779b"
      }
    },
    {
      "command": "swap",
      "args": {
        "tokenIn": "BNKR",
        "tokenOut": "TN100x",
        "tokenInAddress": "0x22aF33FE49fD1Fa80c7149773dDe5890D3c76F3b",
        "tokenOutAddress": "0x5B5dee44552546ECEA05EDeA01DCD7Be7aa6144A",
        "amountIn": 2.246308598982543e+22,
        "amountOut": 8.045563001833731e+21,
        "slippage": 0.01,
        "sender": "0xDeployer",
        "senderAddress": "0xE8c408c5838b3734a39CcE7e645B4E88F093779b",
        "recipient": "@696_eth",
        "recipientAddress": "0x1A1C8B53Fdd72f7c98293005452A890ccdDBd052"
      }
    },
    {
      "command": "transfer",
      "args": {
        "token": "ETH",
        "token_address": "0x4200000000000000000000000000000000000006",
        "amount": 100000000000000,
        "recipient": "@696_eth",
        "recipientAddress": "0x1A1C8B53Fdd72f7c98293005452A890ccdDBd052",
        "sender": "0xDeployer",
        "senderAddress": "0xE8c408c5838b3734a39CcE7e645B4E88F093779b"
      }
    }
  ]
}
```


## Next Steps

In order to run this, you just need to implement the three main interfaces:
  - `TwitterT`
  - `ExecutorT`
  - `ContextT`

I have an example of how you can do this for a swap and transfer in the `src/impls` file.  These mock the twitter interactions for the most part, but you could easily adapt them to your own needs.

As an exercise to the reader, you can execute the command JSON once it has been created by the LLM output.  I have an example of how you can do this for a swap and transfer in the `src/utils` file, and have methods that just print the command's execution in the `src/impls/executor.py` file.

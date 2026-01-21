"""
Centralized protocol configuration including contract addresses and API endpoints.
"""
from enum import Enum
from typing import Dict, Any, Set, List
from dataclasses import dataclass, field

class ProtocolType(Enum):
    DEX = "dex"
    BRIDGE = "bridge"
    AGGREGATOR = "aggregator"
    PAYMENT = "payment"

@dataclass
class ProtocolConfig:
    id: str
    name: str
    type: ProtocolType
    supported_chains: Set[int]
    contract_addresses: Dict[int, Dict[str, str]] = field(default_factory=dict)
    api_endpoints: Dict[str, str] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

PROTOCOLS: Dict[str, ProtocolConfig] = {
    "uniswap": ProtocolConfig(
        id="uniswap",
        name="Uniswap V3",
        type=ProtocolType.DEX,
        supported_chains={1, 137, 42161, 10, 8453},
        contract_addresses={
            1: {
                "router": "0xE592427A0AEce92De3Edee1F18E0157C05861564",
                "quoter": "0xb27308f9F90D607463bb33eA1BeBb41C27CE5AB6",
                "factory": "0x1F98431c8aD98523631AE4a59f267346ea31F984"
            },
            8453: {
                "router": "0x2626664c2603336E57B271c5C0b26F421741e481",
                "quoter": "0x3d4e44Eb1374240CE5F1B871ab261CD16335B76a",
                "factory": "0x33128a8fC17869897dcE68Ed026d694621f6FDfD"
            },
            42161: {
                "router": "0xE592427A0AEce92De3Edee1F18E0157C05861564",
                "quoter": "0xb27308f9F90D607463bb33eA1BeBb41C27CE5AB6",
                "factory": "0x1F98431c8aD98523631AE4a59f267346ea31F984"
            },
            10: {
                "router": "0xE592427A0AEce92De3Edee1F18E0157C05861564",
                "quoter": "0xb27308f9F90D607463bb33eA1BeBb41C27CE5AB6",
                "factory": "0x1F98431c8aD98523631AE4a59f267346ea31F984"
            },
            137: {
                "router": "0xE592427A0AEce92De3Edee1F18E0157C05861564",
                "quoter": "0xb27308f9F90D607463bb33eA1BeBb41C27CE5AB6",
                "factory": "0x1F98431c8aD98523631AE4a59f267346ea31F984"
            }
        }
    ),
    "0x": ProtocolConfig(
        id="0x",
        name="0x Protocol",
        type=ProtocolType.AGGREGATOR,
        supported_chains={1, 137, 42161, 10, 8453, 43114, 59144},
        api_endpoints={
            "1": "https://api.0x.org",
            "137": "https://polygon.api.0x.org",
            "42161": "https://arbitrum.api.0x.org",
            "10": "https://optimism.api.0x.org",
            "8453": "https://base.api.0x.org",
            "43114": "https://avalanche.api.0x.org",
            "59144": "https://linea.api.0x.org",
        }
    ),
    "axelar": ProtocolConfig(
        id="axelar",
        name="Axelar Network",
        type=ProtocolType.BRIDGE,
        supported_chains={1, 137, 42161, 10, 8453, 43114, 59144, 56},
        contract_addresses={
            1: {
                "gateway": "0x4F4495243837681061C4743b74B3eEdf548D56A5",
                "gas_service": "0x2d5d7d31F671F86C782533cc367F14109a082712"
            },
            42161: {
                "gateway": "0xe432150cce91c13a887f7D836923d5597adD8E31",
                "gas_service": "0x2d5d7d31F671F86C782533cc367F14109a082712"
            },
            137: {
                "gateway": "0x6f015F16De9fC8791b234eF68D486d2bF203FBA8",
                "gas_service": "0x2d5d7d31F671F86C782533cc367F14109a082712"
            },
            8453: {
                "gateway": "0xe432150cce91c13a887f7D836923d5597adD8E31",
                "gas_service": "0x2d5d7d31F671F86C782533cc367F14109a082712"
            },
            10: {
                "gateway": "0xe432150cce91c13a887f7D836923d5597adD8E31",
                "gas_service": "0x2d5d7d31F671F86C782533cc367F14109a082712"
            },
            43114: {
                "gateway": "0x5029C0EFf6C34351a0CEc334542cDb22c7928f78",
                "gas_service": "0x2d5d7d31F671F86C782533cc367F14109a082712"
            },
            56: {
                "gateway": "0x304acf330bbE08d1e512eefaa92F6a57871fD895",
                "gas_service": "0x2d5d7d31F671F86C782533cc367F14109a082712"
            }
        },
        api_endpoints={
            "mainnet": "https://api.axelar.dev",
            "lcd": "https://axelar-lcd.quickapi.com"
        }
    ),
    "cctp_v2": ProtocolConfig(
        id="cctp_v2",
        name="Circle CCTP V2",
        type=ProtocolType.BRIDGE,
        supported_chains={1, 42161, 8453, 137, 10, 43114, 59144, 480, 146},
        contract_addresses={
            1: {
                "token_messenger": "0xBd3fa81B58Ba92a82136038B25aDec7066af3155",
                "message_transmitter": "0x0a992d191DEeC32aFe36203Ad87D7d289a738F81",
                "usdc": "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"
            },
            42161: {
                "token_messenger": "0x19330d10D9Cc8751218eaf51E8885D058642E08A",
                "message_transmitter": "0xC30362313FBBA5cf9163F0bb16a0e01f01A896ca",
                "usdc": "0xaf88d065e77c8cC2239327C5EDb3A432268e5831"
            },
            8453: {
                "token_messenger": "0x1682Ae6375C4E4A97e4B583BC394c861A46D8962",
                "message_transmitter": "0xAD09780d193884d503182aD4588450C416D6F9D4",
                "usdc": "0x833589fcd6edb6e08f4c7c32d4f71b54bda02913"
            },
            137: {
                "token_messenger": "0x9daF8c91AEFAE50b9c0E69629D3F6Ca40cA3B3FE",
                "message_transmitter": "0xF3be9355363857F3e001be68856A2f96b4C39Ba9",
                "usdc": "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174"
            },
            10: {
                "token_messenger": "0x2B4069517957735bE00ceE0fadAE88a26365528f",
                "message_transmitter": "0x4D41f22c5a0e5c74090899E5a8Fb597a8842b3e8",
                "usdc": "0x0b2C639c533813f4Aa9D7837CAf62653d097Ff85"
            },
            43114: {
                "token_messenger": "0x6B25532e1060CE10cc3B0A99e5683b91BFDe6982",
                "message_transmitter": "0x8186359aF5F57FbB40c6b14A588d2A59C0C29880",
                "usdc": "0xB97EF9Ef8734C71904D8002F8b6Bc66Dd9c48a6E"
            },
            59144: {
                "token_messenger": "0x9f3B8679c73C2Fef8b59B4f3444d4e156fb70AA5",
                "message_transmitter": "0x4C1A2e70A006C29079c7d4073d8C3c7b8C5D8686",
                "usdc": "0x176211869cA2b568f2A7D4EE941E073a821EE1ff"
            },
            480: {
                "token_messenger": "0x9f3B8679c73C2Fef8b59B4f3444d4e156fb70AA5",
                "message_transmitter": "0x4C1A2e70A006C29079c7d4073d8C3c7b8C5D8686",
                "usdc": "0x79A02482A880bCE3F13e09Da970dC34db4CD24d1"
            },
            146: {
                "token_messenger": "0x9f3B8679c73C2Fef8b59B4f3444d4e156fb70AA5",
                "message_transmitter": "0x4C1A2e70A006C29079c7d4073d8C3c7b8C5D8686",
                "usdc": "0x29219dd400f2Bf60E5a23d13Be72B486D4038894"
            }
        },
        api_endpoints={
            "attestation": "https://iris-api.circle.com"
        }
    ),
    "x402": ProtocolConfig(
        id="x402",
        name="X402 Protocol",
        type=ProtocolType.PAYMENT,
        supported_chains={338, 25, 1},
        api_endpoints={
            "default": "https://facilitator.x402.org"
        }
    ),
    "mnee": ProtocolConfig(
        id="mnee",
        name="MNEE Protocol",
        type=ProtocolType.PAYMENT,
        supported_chains={236, 1},
        api_endpoints={
            "production": "https://proxy-api.mnee.net",
            "sandbox": "https://sandbox-proxy-api.mnee.net"
        }
    )
}

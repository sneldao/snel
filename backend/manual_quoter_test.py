import asyncio
import logging
import json
import httpx
from eth_abi import encode as abi_encode, decode as abi_decode
from eth_utils import to_checksum_address

async def test_quoter():
    # Base configuration
    rpc_url = "https://mainnet.base.org"
    quoter_address = "0x3d4e44Eb1374240CE5F1B871ab261CD16335B76a"
    usdc = to_checksum_address("0x833589fcd6edb6e08f4c7c32d4f71b54bda02913")
    weth = to_checksum_address("0x4200000000000000000000000000000000000006")
    amount_in = 1000000 # 1 USDC
    fee = 500 # 0.05%
    
    print(f"Testing Quoter at {quoter_address} on Base")
    print(f"USDC: {usdc}")
    print(f"WETH: {weth}")

    # V2 Selector: quoteExactInputSingle((address,address,uint256,uint24,uint160))
    v2_selector = "c6a5026a"
    v2_params = (usdc, weth, amount_in, fee, 0)
    v2_data = "0x" + v2_selector + abi_encode(["(address,address,uint256,uint24,uint160)"], [v2_params]).hex()

    # V1 Selector: quoteExactInputSingle(address,address,uint24,uint256,uint160)
    v1_selector = "f7729d43"
    v1_data = "0x" + v1_selector + abi_encode(["address", "address", "uint24", "uint256", "uint160"], [usdc, weth, fee, amount_in, 0]).hex()

    async with httpx.AsyncClient() as client:
        # Check Pool Slot0 to verify existence and price
        pool_address = "0xd0b53d9277642d899df5c87a3966a349a798f224"
        slot0_selector = "3850c7bd"
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "eth_call",
            "params": [{"to": pool_address, "data": "0x" + slot0_selector}, "latest"]
        }
        resp = await client.post(rpc_url, json=payload)
        print(f"\nPool Slot0 Response: {resp.json().get('result')}")
        if resp.json().get("result"):
            res = resp.json().get("result")[2:]
            sqrt_price_x96 = int(res[:64], 16)
            print(f"Pool sqrtPriceX96: {sqrt_price_x96}")

        # Test V2
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "eth_call",
            "params": [{"to": quoter_address, "data": v2_data}, "latest"]
        }
        resp = await client.post(rpc_url, json=payload)
        print(f"\nV2 Response Status: {resp.status_code}")
        print(f"V2 Response JSON: {json.dumps(resp.json(), indent=2)}")

        # Test V2 (Flipped: WETH -> USDC)
        v2_params_flipped = (weth, usdc, 10**16, fee, 0) # 0.01 ETH
        v2_data_flipped = "0x" + v2_selector + abi_encode(["(address,address,uint256,uint24,uint160)"], [v2_params_flipped]).hex()
        payload["params"][0]["data"] = v2_data_flipped
        resp = await client.post(rpc_url, json=payload)
        print(f"\nV2 Flipped (WETH->USDC) Response Status: {resp.status_code}")
        print(f"V2 Flipped Response JSON: {json.dumps(resp.json(), indent=2)}")

if __name__ == "__main__":
    asyncio.run(test_quoter())

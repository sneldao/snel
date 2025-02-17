def is_address(address: str) -> bool:
    return len(address) == 42 and address.startswith("0x")

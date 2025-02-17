import httpx

from dowse.interfaces import ContextT


class BasicContextHelper(ContextT):
    context: str = ""

    async def load_extra_context(self) -> str:
        """loads the bitcoin whitepaper"""
        if self.context == "":
            async with httpx.AsyncClient() as client:
                whitepaper = await client.get(
                    "https://raw.githubusercontent.com/karask/satoshi-paper/refs/heads/master/bitcoin.md"
                )
            self.context = whitepaper.text
        return self.context

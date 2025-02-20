from pydantic import BaseModel

from dowse import Executor


class InputType(BaseModel):
    question: str
    guidance: str


agent = Executor[InputType, str]()


async def main():
    response = await agent.execute(
        InputType(
            question="Tell a detail involving the current weather in San Francisco, referencing the date",
            guidance="Dont use the letter 'e' in your response.",
        )
    )
    print(response)


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())

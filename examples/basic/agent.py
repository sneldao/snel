from pydantic import BaseModel

from dowse import Executor


class QuestionFormat(BaseModel):
    question: str
    guidance: str


# input type is QuestionFormat
# output type is str
agent = Executor[QuestionFormat, str]()


async def main():
    response = await agent.execute(
        QuestionFormat(
            question="Tell a detail involving the current weather in San Francisco, referencing the date",
            guidance="Dont use the letter 'e' in your response.",
        )
    )
    print(response)


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())

from pydantic import BaseModel

from dowse import Executor


class Question(BaseModel):
    question: str
    guidance: str


# input type is QuestionFormat
# output type is str
agent = Executor[Question, str]()


async def main():
    response = await agent.execute(
        Question(
            question="Tell a detail about the city with zip code 21207 and mention the time",
            guidance="When you respond, do not use the letter 'e'.",
        )
    )
    print(response)


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())

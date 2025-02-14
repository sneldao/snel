import sys

from .interfaces import Command, ContextT, ExecutorT, TwitterT
from .llms import classify_message, get_commands, handle_question
from .logger import logger


async def run(
    twitter_manager: TwitterT,
    executor: ExecutorT,
    context_helper: ContextT,
    max_executions: int = sys.maxsize,
):
    """A function to run the execution loop for the intent executor"""
    count = 0
    while count < max_executions:
        tweets = await twitter_manager.get_tweets()
        for tweet in tweets:
            logger.info("TWEET FOUND: %s", tweet)

            if await twitter_manager.has_responded(tweet.id):
                continue
            classification = await classify_message(tweet.content)

            logger.info("CLASSIFICATION: %s", classification)

            if classification == "commands":
                commands = await get_commands(tweet, executor)
                logger.info("COMMANDS: %s", commands)
                for command in commands.requests:
                    await executor.execute_command(
                        Command(
                            command=command.command,
                            args=command.args,
                        )
                    )
            elif classification == "question":
                response = await handle_question(tweet.content, context_helper)
                logger.info("QUESTION RESPONSE: %s", response)
                await twitter_manager.respond(tweet.id, response)

            await twitter_manager.mark_as_responded(tweet.id)

            count += 1

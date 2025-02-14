from ..interfaces import Tweet, TwitterT


class TwitterMock(TwitterT):
    async def get_tweets(self) -> list[Tweet]:
        """Load tweets to be parsed for commands/questions"""
        return [
            Tweet(
                id=1890118705016877145,
                content="""#simmi buy me $10 of $BNKR, swap half of it to $TN100x, and then send my $TN100x to
@696_eth
 along with 0.0001 ETH for gas""",
                creator_id=1414021381298089984,
                creator_name="@0xDeployer",
            ),
            Tweet(
                id=1684298214198108160,
                content="""Why do you continue to ignore bitcoin and lightning?

what "crypto" is a better money transmission protocol and why?""",
                creator_id=12,
                creator_name="@jack",
            ),
        ]

    async def respond(self, tweet_id: int, content: str) -> None:
        """Respond to a tweet"""
        print("RESPONDING TO TWEET:", tweet_id, content)

    async def has_responded(
        self,
        tweet_id: int,
    ) -> bool:
        """Check if the bot has already responded to a tweet"""
        return False

    async def mark_as_responded(
        self,
        tweet_id: int,
    ) -> None:
        """Mark a tweet as responded to so you don't respond to it twice"""

from typing import Sequence

from dowse.interfaces.sources import SourceT
from dowse.models import Tweet


class TwitterMock(SourceT[Tweet]):
    async def get_data(self) -> Sequence[Tweet]:
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
            Tweet(
                id=1890118705016877145,
                content="I dont want to do anything",
                creator_id=12,
                creator_name="@jack",
            ),
        ]

    async def handle(self, data: Tweet) -> None:
        """Respond to a tweet"""
        print("RESPONDING TO TWEET:", data)

    async def has_handled(
        self,
        data: Tweet,
    ) -> bool:
        """Check if the bot has already responded to a tweet"""
        return False

    async def mark_as_handled(
        self,
        data: Tweet,
    ) -> None:
        """Mark a tweet as responded to so you don't respond to it twice"""

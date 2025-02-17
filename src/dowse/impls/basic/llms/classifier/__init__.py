from typing import Literal

from dowse.interfaces.llms.classifier import Classifier
from dowse.interfaces.sources.twitter import Tweet

BasicTweetClassifier = Classifier[
    Tweet, Literal["commands", "question", "not_talking"]
]()

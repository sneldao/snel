from typing import Generic, TypeVar

T = TypeVar("T")


class DowseType(Generic[T]):
    name: str
    description: str

    value: T

    def __init__(self, value: T):
        self.value = value

    def __repr__(self) -> str:
        return f"'{self.value}:{self.name}"

    __str__ = __repr__


class String(DowseType[str]):
    name = "string"
    description = "A string"


class User(DowseType, str):
    name = "user"
    description = (
        "A user.  Denoted by @username with no quotes, spaces or special characters."
    )


class Integer(DowseType[int]):
    name = "integer"
    description = "An integer"


class Float(DowseType[float]):
    name = "float"
    description = "A float"


class Address(DowseType[str]):
    name = "address"
    description = "An Ethereum address"


class TokenAmount(DowseType[tuple[Float, Address | User]]):
    name = "token_amount"
    description = "A token amount"


TokenAmount.__repr__ = lambda self: f"'{self.value[0].value}:{self.title}"  # type: ignore


DEFAULT_TYPES = [
    Address,
    TokenAmount,
    String,
    Integer,
    Float,
    Boolean,
]


def foo(s: String):
    pass


foo(String("3"))

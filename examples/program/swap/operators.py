from random import randint

from dowse.dsl.stack import StackOp
from dowse.dsl.types import Address, Boolean, Float, Integer, String, TokenAmount, User


class Random(StackOp):
    """Make a random value between two integers.  The top value on the stack must be lower than the second value on the stack."""

    def operation(self, lower_value: Integer, upper_value: Integer) -> Integer:
        [lower_value, upper_value] = sorted(
            [lower_value, upper_value], key=lambda x: x.value
        )
        return Integer(randint(lower_value.value, upper_value.value))


class MakeUser(StackOp):
    """Convert a username to a User"""

    def operation(self, username: String) -> User:
        return User(username.value)


class UserToAddress(StackOp):
    """Convert a User to an Address"""

    def operation(self, user: User) -> Address:
        return Address(user.value)


class MakeTokenAmount(StackOp):
    """Convert a Float and Address to a TokenAmount"""

    def operation(self, amount: Float, address: Address) -> TokenAmount:
        return TokenAmount((amount, address))


class GetTokenAddress(StackOp):
    """Get the Address of a Token"""

    def operation(self, symbol: String) -> Address:
        return Address(symbol.value)


class ConvertEthToWei(StackOp):
    """Convert a Float to an ETH TokenAmount"""

    def operation(self, amount: Float) -> TokenAmount:
        return TokenAmount(
            (amount, Address("0x4200000000000000000000000000000000000006"))
        )


class ConvertToTokenAmount(StackOp):
    """Convert an Amount and Address to a TokenAmount"""

    def operation(self, amount: Float, address: Address) -> TokenAmount:
        return TokenAmount((amount, address))


class TransferFunds(StackOp):
    """Transfer funds from the current address to the given address"""

    def operation(self, amount: TokenAmount, to_address: Address | User) -> None:
        return None


class MaybeTransferFunds(StackOp):
    """Transfer funds from the current address to the given address if the top of the stack is true"""

    def operation(
        self, do_transfer: Boolean, amount: TokenAmount, to_address: Address | User
    ) -> None:
        return None


class ExchangeFunds(StackOp):
    """Convert a TokenAmount to another Address via a swap, buy, sell, exchange, etc."""

    def operation(self, amount: TokenAmount, to_address: Address) -> TokenAmount:
        return TokenAmount((amount.value[0], to_address))


class GetPercentage(StackOp):
    """Get a percentage of a TokenAmount.  First arg must be a TokenAmount, second arg must be a Float between 0 and 1"""

    def operation(self, amount: TokenAmount, percentage: Float) -> TokenAmount:
        return TokenAmount((amount.value[0] * percentage.value, amount.value[1]))


SPECIAL_OPERATORS: list = [
    MakeUser,
    UserToAddress,
    MakeTokenAmount,
    GetTokenAddress,
    ConvertEthToWei,
    ConvertToTokenAmount,
    TransferFunds,
    MaybeTransferFunds,
    ExchangeFunds,
    Random,
]

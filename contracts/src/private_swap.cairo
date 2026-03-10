#[starknet::interface]
trait IPrivateSwap<TContractState> {
    fn submit_order(ref self: TContractState, commitment: felt252, amount: u256, token_in: starknet::ContractAddress, token_out: starknet::ContractAddress);
    fn cancel_order(ref self: TContractState, nullifier: felt252, proof: Array<felt252>);
    fn is_order_active(self: @TContractState, commitment: felt252) -> bool;
}

#[starknet::contract]
mod private_swap {
    use starknet::ContractAddress;
    use array::ArrayTrait;

    #[storage]
    struct Storage {
        orders: LegacyMap::<felt252, bool>,
        cancelled_orders: LegacyMap::<felt252, bool>,
    }

    #[event]
    #[derive(Drop, starknet::Event)]
    enum Event {
        OrderSubmitted: OrderSubmitted,
        OrderCancelled: OrderCancelled,
    }

    #[derive(Drop, starknet::Event)]
    struct OrderSubmitted {
        commitment: felt252,
        amount: u256,
        token_in: ContractAddress,
        token_out: ContractAddress,
    }

    #[derive(Drop, starknet::Event)]
    struct OrderCancelled {
        nullifier: felt252,
    }

    #[abi(embed_v0)]
    impl PrivateSwapImpl of super::IPrivateSwap<ContractState> {
        fn submit_order(ref self: ContractState, commitment: felt252, amount: u256, token_in: ContractAddress, token_out: ContractAddress) {
            assert(!self.orders.read(commitment), 'Order already exists');
            self.orders.write(commitment, true);
            self.emit(OrderSubmitted { commitment, amount, token_in, token_out });
        }

        fn cancel_order(ref self: ContractState, nullifier: felt252, proof: Array<felt252>) {
            assert(!self.cancelled_orders.read(nullifier), 'Order already cancelled');
            assert(proof.len() > 0, 'Invalid ZK proof');
            self.cancelled_orders.write(nullifier, true);
            self.emit(OrderCancelled { nullifier });
        }

        fn is_order_active(self: @ContractState, commitment: felt252) -> bool {
            self.orders.read(commitment) && !self.cancelled_orders.read(commitment)
        }
    }
}

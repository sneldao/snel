#[starknet::interface]
trait IPrivateSwap<TContractState> {
    fn submit_order(ref self: TContractState, commitment: felt252, amount: u256, token_in: starknet::ContractAddress, token_out: starknet::ContractAddress);
    fn cancel_order(ref self: TContractState, nullifier: felt252);
}

#[starknet::contract]
mod private_swap {
    use starknet::ContractAddress;

    #[storage]
    struct Storage {
        orders: LegacyMap::<felt252, bool>,
    }

    #[abi(embed_v0)]
    impl PrivateSwapImpl of super::IPrivateSwap<ContractState> {
        fn submit_order(ref self: ContractState, commitment: felt252, amount: u256, token_in: ContractAddress, token_out: ContractAddress) {
            self.orders.write(commitment, true);
        }

        fn cancel_order(ref self: ContractState, nullifier: felt252) {
            // Cancel logic
        }
    }
}

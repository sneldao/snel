#[starknet::interface]
trait IPrivacyPool<TContractState> {
    fn deposit(ref self: TContractState, commitment: felt252, amount: u256);
    fn withdraw(ref self: TContractState, nullifier: felt252, recipient: starknet::ContractAddress, amount: u256, proof: Array<felt252>);
}

#[starknet::contract]
mod privacy_pool {
    use starknet::ContractAddress;
    use array::ArrayTrait;

    #[storage]
    struct Storage {
        commitments: LegacyMap::<felt252, bool>,
        nullifiers: LegacyMap::<felt252, bool>,
    }

    #[abi(embed_v0)]
    impl PrivacyPoolImpl of super::IPrivacyPool<ContractState> {
        fn deposit(ref self: ContractState, commitment: felt252, amount: u256) {
            self.commitments.write(commitment, true);
        }

        fn withdraw(ref self: ContractState, nullifier: felt252, recipient: ContractAddress, amount: u256, proof: Array<felt252>) {
            assert(!self.nullifiers.read(nullifier), 'Already withdrawn');
            self.nullifiers.write(nullifier, true);
        }
    }
}

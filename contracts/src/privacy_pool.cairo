#[starknet::interface]
trait IPrivacyPool<TContractState> {
    fn deposit(ref self: TContractState, commitment: felt252, amount: u256);
    fn withdraw(ref self: TContractState, nullifier: felt252, recipient: starknet::ContractAddress, amount: u256, proof: Array<felt252>);
    fn is_commitment_used(self: @TContractState, commitment: felt252) -> bool;
    fn is_nullifier_used(self: @TContractState, nullifier: felt252) -> bool;
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

    #[event]
    #[derive(Drop, starknet::Event)]
    enum Event {
        Deposit: Deposit,
        Withdrawal: Withdrawal,
    }

    #[derive(Drop, starknet::Event)]
    struct Deposit {
        commitment: felt252,
        amount: u256,
    }

    #[derive(Drop, starknet::Event)]
    struct Withdrawal {
        nullifier: felt252,
        recipient: ContractAddress,
        amount: u256,
    }

    #[abi(embed_v0)]
    impl PrivacyPoolImpl of super::IPrivacyPool<ContractState> {
        fn deposit(ref self: ContractState, commitment: felt252, amount: u256) {
            assert(!self.commitments.read(commitment), 'Commitment already exists');
            self.commitments.write(commitment, true);
            self.emit(Deposit { commitment, amount });
        }

        fn withdraw(ref self: ContractState, nullifier: felt252, recipient: ContractAddress, amount: u256, proof: Array<felt252>) {
            assert(!self.nullifiers.read(nullifier), 'Nullifier already used');
            assert(proof.len() > 0, 'Invalid ZK proof');
            self.nullifiers.write(nullifier, true);
            self.emit(Withdrawal { nullifier, recipient, amount });
        }

        fn is_commitment_used(self: @ContractState, commitment: felt252) -> bool {
            self.commitments.read(commitment)
        }

        fn is_nullifier_used(self: @ContractState, nullifier: felt252) -> bool {
            self.nullifiers.read(nullifier)
        }
    }
}

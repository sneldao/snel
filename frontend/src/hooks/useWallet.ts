import { useAccount as useEvmAccount, useConnect as useEvmConnect, useDisconnect as useEvmDisconnect, useWalletClient } from 'wagmi';
import { injected } from 'wagmi/connectors';
import { useAccount as useStarknetAccount, useDisconnect as useStarknetDisconnect, useNetwork as useStarknetNetwork } from '@starknet-react/core';
import { useMemo } from 'react';

export const useWallet = () => {
  const { address: evmAddress, isConnected: isEvmConnected, chain: evmChain } = useEvmAccount();
  const { address: starknetAddress, isConnected: isStarknetConnected } = useStarknetAccount();
  const { chain: starknetChain } = useStarknetNetwork();
  
  const { connect: connectEvm } = useEvmConnect();
  const { disconnect: disconnectEvm } = useEvmDisconnect();
  const { disconnect: disconnectStarknet } = useStarknetDisconnect();
  
  const { data: wagmiWalletClient } = useWalletClient();

  const connectWallet = () => {
    connectEvm({ connector: injected() });
  };

  const disconnect = () => {
    if (isEvmConnected) disconnectEvm();
    if (isStarknetConnected) disconnectStarknet();
  };

  // Create a standardized wallet client interface for EVM
  const walletClient = useMemo(() => {
    if (!wagmiWalletClient || !evmAddress || !evmChain) {
      return null;
    }

    return {
      account: { address: evmAddress },
      chain: { id: evmChain.id, name: evmChain.name },
      getAddress: () => Promise.resolve(evmAddress),
      signMessage: (message: string) => wagmiWalletClient.signMessage({ message }),
      signTransaction: (transaction: any) => wagmiWalletClient.signTransaction(transaction),
      sendTransaction: (transaction: any) => wagmiWalletClient.sendTransaction(transaction),
      // For ethers compatibility
      _isSigner: true,
      provider: wagmiWalletClient.transport,
      chainId: evmChain.id
    };
  }, [wagmiWalletClient, evmAddress, evmChain]);

  return {
    address: evmAddress || starknetAddress,
    evmAddress,
    starknetAddress,
    isConnected: isEvmConnected || isStarknetConnected,
    isEvmConnected,
    isStarknetConnected,
    connect: connectWallet,
    disconnect,
    walletClient,
    chainId: evmChain?.id,
    chainName: evmChain?.name,
    starknetChainId: starknetChain?.id,
    starknetChainName: starknetChain?.name,
    activeChainId: evmChain?.id || starknetChain?.id,
    activeChainName: evmChain?.name || starknetChain?.name,
  };
};
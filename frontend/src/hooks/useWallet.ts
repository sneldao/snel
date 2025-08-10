import { useAccount, useConnect, useDisconnect, useWalletClient } from 'wagmi';
import { injected } from 'wagmi/connectors';
import { useMemo } from 'react';

export const useWallet = () => {
  const { address, isConnected, chain } = useAccount();
  const { connect } = useConnect();
  const { disconnect } = useDisconnect();
  const { data: wagmiWalletClient } = useWalletClient();

  const connectWallet = () => {
    connect({ connector: injected() });
  };

  // Create a standardized wallet client interface
  const walletClient = useMemo(() => {
    if (!wagmiWalletClient || !address || !chain) {
      return null;
    }

    return {
      account: { address },
      chain: { id: chain.id, name: chain.name },
      getAddress: () => Promise.resolve(address),
      signMessage: (message: string) => wagmiWalletClient.signMessage({ message }),
      signTransaction: (transaction: any) => wagmiWalletClient.signTransaction(transaction),
      sendTransaction: (transaction: any) => wagmiWalletClient.sendTransaction(transaction),
      // For ethers compatibility
      _isSigner: true,
      provider: wagmiWalletClient.transport,
      chainId: chain.id
    };
  }, [wagmiWalletClient, address, chain]);

  return {
    address,
    isConnected,
    connect: connectWallet,
    disconnect,
    walletClient,
    chainId: chain?.id,
    chainName: chain?.name,
  };
};
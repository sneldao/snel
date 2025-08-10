/**
 * Wallet Adapters
 * Converts between different wallet client formats for compatibility
 */

import { ethers } from 'ethers';
import { logger } from './logger';

/**
 * Convert wagmi wallet client to ethers signer
 */
export const createEthersSigner = (walletClient: any): any | null => {
  if (!walletClient) {
    logger.warn('No wallet client provided to createEthersSigner');
    return null;
  }

  try {
    // Create a custom signer that implements the ethers signer interface
    class WagmiEthersSigner {
      public address: string;
      public chainId: number;
      private walletClient: any;

      constructor(walletClient: any) {
        this.walletClient = walletClient;
        this.address = walletClient.account?.address || '';
        this.chainId = walletClient.chain?.id || walletClient.chainId || 1;
      }

      async getAddress(): Promise<string> {
        return this.address;
      }

      async signMessage(message: string): Promise<string> {
        if (!this.walletClient.signMessage) {
          throw new Error('Wallet client does not support message signing');
        }
        return await this.walletClient.signMessage(message);
      }

      async signTransaction(transaction: ethers.TransactionRequest): Promise<string> {
        if (!this.walletClient.signTransaction) {
          throw new Error('Wallet client does not support transaction signing');
        }
        return await this.walletClient.signTransaction(transaction);
      }

      async sendTransaction(transaction: ethers.TransactionRequest): Promise<ethers.TransactionResponse> {
        if (!this.walletClient.sendTransaction) {
          throw new Error('Wallet client does not support sending transactions');
        }
        
        const txHash = await this.walletClient.sendTransaction(transaction);
        
        // Create a mock transaction response for ethers compatibility
        return ({
          hash: txHash,
          chainId: this.chainId,
          from: this.address,
          to: transaction.to || '',
          value: transaction.value || '0',
          gasLimit: transaction.gasLimit || '21000',
          gasPrice: transaction.gasPrice,
          data: transaction.data || '0x',
          nonce: transaction.nonce || 0,
          wait: async (confirmations?: number) => {
            // For now, return a basic receipt structure
            // In a real implementation, you'd poll for the transaction receipt
            return {
              to: transaction.to,
              from: this.address,
              contractAddress: null,
              transactionIndex: 0,
              root: '',
              gasUsed: ethers.getBigInt('21000'),
              logsBloom: '0x',
              blockHash: '',
              transactionHash: txHash,
              logs: [],
              blockNumber: 0,
              confirmations: confirmations || 1,
              cumulativeGasUsed: ethers.getBigInt('21000'),
              effectiveGasPrice: ethers.getBigInt('20000000000'),
              status: 1,
              type: 2,
              byzantium: true
            };
          }
        } as any) as ethers.TransactionResponse;
      }

      connect(provider: any): any {
        // Return a new instance connected to the provider
        const newSigner = new WagmiEthersSigner(this.walletClient);
        (newSigner as any).provider = provider;
        return newSigner;
      }
    }

    return new WagmiEthersSigner(walletClient);

  } catch (error) {
    logger.error('Failed to create ethers signer:', error);
    return null;
  }
};

/**
 * Check if wallet client is compatible with ethers
 */
export const isEthersCompatible = (walletClient: any): boolean => {
  return walletClient && 
         walletClient.account?.address &&
         (walletClient.sendTransaction || walletClient.signTransaction);
};

// Re-export from centralized mappings for backward compatibility
export { getAxelarChainName } from './chainMappings';
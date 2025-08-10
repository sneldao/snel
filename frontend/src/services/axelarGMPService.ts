/**
 * Axelar General Message Passing (GMP) Service
 * Handles advanced cross-chain operations beyond simple token transfers
 */

import { ethers } from 'ethers';
import { logger } from '../utils/logger';
import { 
  getAxelarGatewayAddress, 
  getAxelarGasServiceAddress, 
  isAxelarSupported, 
  getSupportedAxelarChains 
} from '../utils/chainMappings';

// Axelar Gateway ABI (simplified - key functions only)
const AXELAR_GATEWAY_ABI = [
  "function callContract(string calldata destinationChain, string calldata contractAddress, bytes calldata payload) external",
  "function callContractWithToken(string calldata destinationChain, string calldata contractAddress, bytes calldata payload, string calldata symbol, uint256 amount) external",
  "function validateContractCall(bytes32 commandId, string calldata sourceChain, string calldata sourceAddress, bytes32 payloadHash) external returns (bool)",
  "function isContractCallApproved(bytes32 commandId, string calldata sourceChain, string calldata sourceAddress, address contractAddress, bytes32 payloadHash) external view returns (bool)"
];

// Axelar Gas Service ABI (simplified)
const AXELAR_GAS_SERVICE_ABI = [
  "function payNativeGasForContractCall(address sender, string calldata destinationChain, string calldata destinationAddress, bytes calldata payload, address refundAddress) external payable",
  "function payNativeGasForContractCallWithToken(address sender, string calldata destinationChain, string calldata destinationAddress, bytes calldata payload, string calldata symbol, uint256 amount, address refundAddress) external payable",
  "function estimateGasFee(string calldata destinationChain, string calldata destinationAddress, bytes calldata payload, uint256 gasLimit, address gasToken) external view returns (uint256)"
];

export interface GMPCallParams {
  destinationChain: string;
  destinationAddress: string;
  payload: string;
  gasLimit?: number;
  refundAddress?: string;
}

export interface GMPCallWithTokenParams extends GMPCallParams {
  tokenSymbol: string;
  amount: string;
}

export interface CrossChainSwapParams {
  sourceChain: string;
  destChain: string;
  sourceToken: string;
  destToken: string;
  amount: string;
  recipient: string;
  slippage?: number;
}

export interface GMPTransactionStatus {
  status: 'pending' | 'approved' | 'executed' | 'error';
  sourceTxHash: string;
  destTxHash?: string;
  gasPaid: boolean;
  approved: boolean;
  executed: boolean;
  error?: string;
  estimatedTimeRemaining?: string;
}

class AxelarGMPService {

  /**
   * Get Axelar Gateway contract for a chain
   */
  getGatewayContract(chainId: number, signer: ethers.Signer): ethers.Contract | null {
    const address = getAxelarGatewayAddress(chainId);
    if (!address) {
      logger.warn(`No Axelar Gateway address for chain ${chainId}`);
      return null;
    }
    return new ethers.Contract(address, AXELAR_GATEWAY_ABI, signer);
  }

  /**
   * Get Axelar Gas Service contract for a chain
   */
  getGasServiceContract(chainId: number, signer: ethers.Signer): ethers.Contract | null {
    const address = getAxelarGasServiceAddress(chainId);
    if (!address) {
      logger.warn(`No Axelar Gas Service address for chain ${chainId}`);
      return null;
    }
    return new ethers.Contract(address, AXELAR_GAS_SERVICE_ABI, signer);
  }

  /**
   * Estimate gas fee for cross-chain call
   */
  async estimateGasFee(
    chainId: number,
    destinationChain: string,
    destinationAddress: string,
    payload: string,
    gasLimit: number = 500000,
    signer: ethers.Signer
  ): Promise<{ gasFee: string; gasToken: string } | null> {
    try {
      const gasService = this.getGasServiceContract(chainId, signer);
      if (!gasService) return null;

      const gasFee = await gasService.estimateGasFee(
        destinationChain,
        destinationAddress,
        payload,
        gasLimit,
        ethers.ZeroAddress // Native token
      );

      return {
        gasFee: gasFee.toString(),
        gasToken: 'ETH' // Simplified - would be chain-specific
      };
    } catch (error) {
      logger.error('Error estimating gas fee:', error);
      return null;
    }
  }

  /**
   * Execute a cross-chain contract call
   */
  async executeContractCall(
    chainId: number,
    params: GMPCallParams,
    signer: ethers.Signer
  ): Promise<{ txHash: string; success: boolean; error?: string }> {
    try {
      const gateway = this.getGatewayContract(chainId, signer);
      const gasService = this.getGasServiceContract(chainId, signer);
      
      if (!gateway || !gasService) {
        return {
          txHash: '',
          success: false,
          error: 'Gateway or Gas Service not available for this chain'
        };
      }

      // Estimate gas fee
      const gasEstimate = await this.estimateGasFee(
        chainId,
        params.destinationChain,
        params.destinationAddress,
        params.payload,
        params.gasLimit,
        signer
      );

      if (!gasEstimate) {
        return {
          txHash: '',
          success: false,
          error: 'Failed to estimate gas fee'
        };
      }

      // Step 1: Pay gas for cross-chain execution
      const userAddress = await signer.getAddress();
      const gasPaymentTx = await gasService.payNativeGasForContractCall(
        userAddress,
        params.destinationChain,
        params.destinationAddress,
        params.payload,
        params.refundAddress || userAddress,
        { value: gasEstimate.gasFee }
      );

      await gasPaymentTx.wait();
      logger.info('Gas payment successful:', gasPaymentTx.hash);

      // Step 2: Execute the contract call
      const callTx = await gateway.callContract(
        params.destinationChain,
        params.destinationAddress,
        params.payload
      );

      await callTx.wait();
      logger.info('Contract call successful:', callTx.hash);

      return {
        txHash: callTx.hash,
        success: true
      };

    } catch (error) {
      logger.error('Error executing contract call:', error);
      return {
        txHash: '',
        success: false,
        error: error instanceof Error ? error.message : 'Unknown error'
      };
    }
  }

  /**
   * Execute a cross-chain contract call with token transfer
   */
  async executeContractCallWithToken(
    chainId: number,
    params: GMPCallWithTokenParams,
    signer: ethers.Signer
  ): Promise<{ txHash: string; success: boolean; error?: string }> {
    try {
      const gateway = this.getGatewayContract(chainId, signer);
      const gasService = this.getGasServiceContract(chainId, signer);
      
      if (!gateway || !gasService) {
        return {
          txHash: '',
          success: false,
          error: 'Gateway or Gas Service not available for this chain'
        };
      }

      // Estimate gas fee
      const gasEstimate = await this.estimateGasFee(
        chainId,
        params.destinationChain,
        params.destinationAddress,
        params.payload,
        params.gasLimit,
        signer
      );

      if (!gasEstimate) {
        return {
          txHash: '',
          success: false,
          error: 'Failed to estimate gas fee'
        };
      }

      // Step 1: Pay gas for cross-chain execution
      const userAddress = await signer.getAddress();
      const gasPaymentTx = await gasService.payNativeGasForContractCallWithToken(
        userAddress,
        params.destinationChain,
        params.destinationAddress,
        params.payload,
        params.tokenSymbol,
        params.amount,
        params.refundAddress || userAddress,
        { value: gasEstimate.gasFee }
      );

      await gasPaymentTx.wait();
      logger.info('Gas payment successful:', gasPaymentTx.hash);

      // Step 2: Execute the contract call with token
      const callTx = await gateway.callContractWithToken(
        params.destinationChain,
        params.destinationAddress,
        params.payload,
        params.tokenSymbol,
        params.amount
      );

      await callTx.wait();
      logger.info('Contract call with token successful:', callTx.hash);

      return {
        txHash: callTx.hash,
        success: true
      };

    } catch (error) {
      logger.error('Error executing contract call with token:', error);
      return {
        txHash: '',
        success: false,
        error: error instanceof Error ? error.message : 'Unknown error'
      };
    }
  }

  /**
   * Build a cross-chain swap transaction using GMP
   * This demonstrates how to use GMP for complex operations
   */
  async buildCrossChainSwap(
    chainId: number,
    params: CrossChainSwapParams,
    signer: ethers.Signer
  ): Promise<{ 
    transaction: any; 
    gasEstimate: string; 
    success: boolean; 
    error?: string 
  }> {
    try {
      // Encode the swap parameters as payload
      const swapPayload = ethers.AbiCoder.defaultAbiCoder().encode(
        ['string', 'string', 'uint256', 'address', 'uint256'],
        [
          params.sourceToken,
          params.destToken,
          ethers.parseUnits(params.amount, 18), // Assuming 18 decimals
          params.recipient,
          Math.floor((params.slippage || 0.01) * 10000) // Convert to basis points
        ]
      );

      // Estimate gas fee
      const gasEstimate = await this.estimateGasFee(
        chainId,
        params.destChain,
        params.recipient, // Simplified - would be swap contract address
        swapPayload,
        500000, // 500k gas limit for swap
        signer
      );

      if (!gasEstimate) {
        return {
          transaction: null,
          gasEstimate: '0',
          success: false,
          error: 'Failed to estimate gas fee'
        };
      }

      // Build transaction data (this would be more complex in reality)
      const gatewayAddress = getAxelarGatewayAddress(chainId);
      if (!gatewayAddress) {
        throw new Error(`Axelar Gateway not available for chain ${chainId}`);
      }

      const transaction = {
        to: gatewayAddress,
        data: swapPayload,
        value: gasEstimate.gasFee,
        gasLimit: 800000 // Higher gas limit for complex operation
      };

      return {
        transaction,
        gasEstimate: gasEstimate.gasFee,
        success: true
      };

    } catch (error) {
      logger.error('Error building cross-chain swap:', error);
      return {
        transaction: null,
        gasEstimate: '0',
        success: false,
        error: error instanceof Error ? error.message : 'Unknown error'
      };
    }
  }

  /**
   * Track GMP transaction status using AxelarGMPRecoveryAPI
   */
  async trackTransaction(
    txHash: string,
    sourceChain: string,
    destChain: string
  ): Promise<GMPTransactionStatus | null> {
    try {
      // Use AxelarGMPRecoveryAPI for proper tracking
      const { AxelarGMPRecoveryAPI, Environment } = await import('@axelar-network/axelarjs-sdk');
      
      const recoveryAPI = new AxelarGMPRecoveryAPI({
        environment: Environment.MAINNET // or TESTNET based on your config
      });

      // Query transaction status by source tx hash
      const txStatus = await recoveryAPI.queryTransactionStatus(txHash);
      
      if (!txStatus) {
        // Return pending status if not found
        return {
          status: 'pending',
          sourceTxHash: txHash,
          gasPaid: false,
          approved: false,
          executed: false,
          estimatedTimeRemaining: '5-10 minutes'
        };
      }

      // Map Axelar status to our status format
      let status: 'pending' | 'approved' | 'executed' | 'error' = 'pending';
      const statusValue = (txStatus as any).status;
      
      if (statusValue === 'executed') {
        status = 'executed';
      } else if (statusValue === 'approved') {
        status = 'approved';
      } else if ((txStatus as any).error) {
        status = 'error';
      }
      
      return {
        status,
        sourceTxHash: txHash,
        destTxHash: (txStatus as any).destinationTxHash || (txStatus as any).destTxHash,
        gasPaid: (txStatus as any).gasPaid || false,
        approved: status === 'approved' || status === 'executed',
        executed: status === 'executed',
        error: (txStatus as any).error,
        estimatedTimeRemaining: status === 'executed' ? '0 minutes' : '5-10 minutes'
      };

    } catch (error) {
      logger.error('Error tracking transaction:', error);
      // Fallback to pending status
      return {
        status: 'pending',
        sourceTxHash: txHash,
        gasPaid: true,
        approved: false,
        executed: false,
        estimatedTimeRemaining: '5-10 minutes'
      };
    }
  }

  /**
   * Check if a chain supports GMP operations
   */
  isGMPSupported(chainId: number): boolean {
    return isAxelarSupported(chainId);
  }

  /**
   * Get supported chains for GMP
   */
  getSupportedChains(): number[] {
    return getSupportedAxelarChains();
  }
}

// Export singleton instance
export const axelarGMPService = new AxelarGMPService();
export default AxelarGMPService;

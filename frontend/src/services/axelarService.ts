import {
  AxelarAssetTransfer,
  AxelarQueryAPI,
  Environment,
  EvmChain,
  SendTokenParams
} from "@axelar-network/axelarjs-sdk";
import { ethers } from "ethers";
import { ChainUtils } from "../utils/chainUtils";
import { logger } from "../utils/logger";

export interface TransferQuote {
  fee: string;
  estimatedTime: string;
  route: string[];
}

export interface AxelarConfig {
  environment: Environment;
  rpcUrl?: string;
}

class AxelarService {
  private assetTransfer: AxelarAssetTransfer | null = null;
  private queryAPI: AxelarQueryAPI | null = null;
  private environment: Environment;
  private isInitialized: boolean = false;

  constructor(config: AxelarConfig = { environment: Environment.MAINNET }) {
    this.environment = config.environment;
    
    try {
      // Initialize AxelarAssetTransfer with proper config
      this.assetTransfer = new AxelarAssetTransfer({
        environment: this.environment,
        auth: "metamask" // Use metamask for browser environment
      });

      // Initialize AxelarQueryAPI
      this.queryAPI = new AxelarQueryAPI({
        environment: this.environment,
        axelarRpcUrl: config.rpcUrl
      });

      this.isInitialized = true;
      logger.service('axelar', `Service initialized successfully for ${this.environment}`);
    } catch (error) {
      logger.warn(`Failed to initialize Axelar service for ${this.environment}:`, error);
      
      // Fallback to testnet if mainnet fails
      if (this.environment === Environment.MAINNET) {
        try {
          this.environment = Environment.TESTNET;
          this.assetTransfer = new AxelarAssetTransfer({
            environment: this.environment,
            auth: "metamask"
          });
          this.queryAPI = new AxelarQueryAPI({
            environment: this.environment
          });
          this.isInitialized = true;
          logger.service('axelar', 'Service initialized with testnet fallback');
        } catch (fallbackError) {
          logger.error("Failed to initialize Axelar service with testnet fallback:", fallbackError);
          this.isInitialized = false;
        }
      } else {
        this.isInitialized = false;
      }
    }
  }

  /**
   * Check if the service is properly initialized
   */
  isReady(): boolean {
    return this.isInitialized && this.assetTransfer !== null && this.queryAPI !== null;
  }

  /**
   * Get the current environment
   */
  getEnvironment(): Environment {
    return this.environment;
  }

  /**
   * Convert chain name to Axelar format using ChainUtils
   */
  getAxelarChainName(chainNameOrId: string | number): string | null {
    try {
      let chainName: string;
      
      if (typeof chainNameOrId === 'number') {
        const config = ChainUtils.getChainConfig(chainNameOrId);
        chainName = config?.name || '';
      } else {
        chainName = chainNameOrId;
      }

      // Normalize the chain name and get Axelar mapping
      const normalizedName = ChainUtils.normalizeChainName(chainName);
      
      // Map common chain names to Axelar chain names
      const axelarMapping: { [key: string]: string } = {
        'Ethereum': 'ethereum',
        'Polygon': 'polygon',
        'Avalanche': 'avalanche',
        'Arbitrum': 'arbitrum',
        'optimism': 'optimism',
        'binance': 'binance',
        'base': 'base'
      };

      return axelarMapping[normalizedName] || null;
    } catch (error) {
      logger.error('Error getting Axelar chain name:', error);
      return null;
    }
  }

  /**
   * Check if a chain is supported by Axelar
   */
  isChainSupported(chainIdentifier: string | number): boolean {
    if (!this.isReady()) {
      return false;
    }

    try {
      const axelarName = this.getAxelarChainName(chainIdentifier);
      return axelarName !== null;
    } catch (error) {
      logger.error('Error checking chain support:', error);
      return false;
    }
  }

  /**
   * Get list of supported chains
   */
  getSupportedChains(): string[] {
    if (!this.isReady()) {
      return [];
    }

    try {
      const supportedChainIds = ChainUtils.getSupportedChainIds();
      return supportedChainIds
        .map(chainId => {
          const config = ChainUtils.getChainConfig(chainId);
          return config?.name;
        })
        .filter((name) => name !== undefined && this.getAxelarChainName(name) !== null) as string[];
    } catch (error) {
      logger.error('Error getting supported chains:', error);
      return [];
    }
  }

  /**
   * Get transfer quote for cross-chain transaction
   */
  async getTransferQuote(
    fromChain: string,
    toChain: string,
    asset: string,
    amount: string
  ): Promise<TransferQuote | null> {
    if (!this.isReady() || !this.queryAPI) {
      throw new Error('Axelar service not initialized');
    }

    try {
      const fromAxelarChain = this.getAxelarChainName(fromChain);
      const toAxelarChain = this.getAxelarChainName(toChain);

      if (!fromAxelarChain || !toAxelarChain) {
        throw new Error(`Unsupported chain: ${fromChain} -> ${toChain}`);
      }

      // Convert amount to number for the API
      const amountNumber = parseFloat(amount);
      if (isNaN(amountNumber)) {
        throw new Error('Invalid amount');
      }

      // Use the correct API method based on SDK structure
      const feeResponse = await Promise.race([
        this.queryAPI.getTransferFee(
          fromAxelarChain,
          toAxelarChain,
          asset,
          amountNumber
        ),
        new Promise((_, reject) => 
          setTimeout(() => reject(new Error('Request timeout')), 10000)
        )
      ]) as any;

      if (!feeResponse) {
        throw new Error('Failed to get transfer fee');
      }

      return {
        fee: feeResponse.fee?.amount || '0',
        estimatedTime: '10-20 minutes', // Default estimate
        route: [fromChain, toChain]
      };
    } catch (error) {
      logger.error('Error getting transfer quote:', error);
      throw error;
    }
  }

  /**
   * Get deposit address for cross-chain transfer
   */
  async getDepositAddress(
    fromChain: string,
    toChain: string,
    toAddress: string,
    asset: string
  ): Promise<string> {
    if (!this.isReady() || !this.assetTransfer) {
      throw new Error('Axelar service not initialized');
    }

    try {
      const fromAxelarChain = this.getAxelarChainName(fromChain);
      const toAxelarChain = this.getAxelarChainName(toChain);

      if (!fromAxelarChain || !toAxelarChain) {
        throw new Error(`Unsupported chain: ${fromChain} -> ${toChain}`);
      }

      // Use the correct method signature based on SDK
      const depositAddress = await this.assetTransfer.getDepositAddress({
        fromChain: fromAxelarChain,
        toChain: toAxelarChain,
        destinationAddress: toAddress,
        asset: asset
      });

      return depositAddress;
    } catch (error) {
      logger.error('Error getting deposit address:', error);
      throw error;
    }
  }

  /**
   * Execute cross-chain transfer
   */
  async executeTransfer(
    fromChain: string,
    toChain: string,
    toAddress: string,
    asset: string,
    amount: string,
    provider?: ethers.BrowserProvider
  ): Promise<string> {
    if (!this.isReady() || !this.assetTransfer) {
      throw new Error('Axelar service not initialized');
    }

    if (!provider) {
      throw new Error('Web3 provider required for transfer execution');
    }

    try {
      const fromAxelarChain = this.getAxelarChainName(fromChain);
      const toAxelarChain = this.getAxelarChainName(toChain);

      if (!fromAxelarChain || !toAxelarChain) {
        throw new Error(`Unsupported chain: ${fromChain} -> ${toChain}`);
      }

      const signer = await provider.getSigner();

      // Prepare the send token parameters according to the SDK interface
      const sendTokenParams: SendTokenParams = {
        fromChain: fromAxelarChain,
        toChain: toAxelarChain,
        destinationAddress: toAddress,
        asset: {
          symbol: asset
        },
        amountInAtomicUnits: amount,
        options: {
          evmOptions: {
            signer: signer as any,
            provider: provider as any
          }
        }
      };

      // Execute the transfer using the asset transfer service
      const txResponse = await this.assetTransfer.sendToken(sendTokenParams);

      // Extract transaction hash from the response
      if ('hash' in txResponse) {
        return txResponse.hash;
      } else if ('transactionHash' in txResponse) {
        return (txResponse as any).transactionHash;
      } else {
        throw new Error('Unable to extract transaction hash from response');
      }
    } catch (error) {
      logger.error('Error executing transfer:', error);
      throw error;
    }
  }

  /**
   * Get gas fee estimate for cross-chain transaction
   */
  async getGasFeeEstimate(
    fromChain: string,
    toChain: string,
    gasLimit: string = "100000"
  ): Promise<string> {
    if (!this.isReady() || !this.queryAPI) {
      throw new Error('Axelar service not initialized');
    }

    try {
      const fromAxelarChain = this.getAxelarChainName(fromChain);
      const toAxelarChain = this.getAxelarChainName(toChain);

      if (!fromAxelarChain || !toAxelarChain) {
        throw new Error(`Unsupported chain: ${fromChain} -> ${toChain}`);
      }

      // Use the estimateGasFee method
      const gasFee = await this.queryAPI.estimateGasFee(
        fromAxelarChain as EvmChain,
        toAxelarChain as EvmChain,
        gasLimit
      );

      return typeof gasFee === 'string' ? gasFee : gasFee.baseFee;
    } catch (error) {
      logger.error('Error getting gas fee estimate:', error);
      throw error;
    }
  }

  /**
   * Check if chains are active
   */
  async areChainsActive(chains: string[]): Promise<boolean> {
    if (!this.isReady() || !this.queryAPI) {
      return false;
    }

    try {
      const axelarChains = chains
        .map(chain => this.getAxelarChainName(chain))
        .filter((name): name is string => name !== null);

      if (axelarChains.length !== chains.length) {
        return false; // Some chains are not supported
      }

      // Check if all chains are active
      const activeChecks = await Promise.all(
        axelarChains.map(chain => this.queryAPI!.isChainActive(chain))
      );

      return activeChecks.every(isActive => isActive);
    } catch (error) {
      logger.error('Error checking chain activity:', error);
      return false;
    }
  }
}

// Export singleton instance
export const axelarService = new AxelarService({
  environment: process.env.NODE_ENV === 'production' ? Environment.MAINNET : Environment.TESTNET
});

export default AxelarService;
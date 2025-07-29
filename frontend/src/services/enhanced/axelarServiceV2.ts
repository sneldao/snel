import {
  AxelarAssetTransfer,
  AxelarQueryAPI,
  AxelarGMPRecoveryAPI,
  Environment,
  EvmChain,
  SendTokenParams,
  GasEstimateResponse,
  AxelarRecoveryAPIParams,
  GMPStatus,
  GMPStatusResponse,
  TransactionStatus
} from "@axelar-network/axelarjs-sdk";
import { ethers } from "ethers";
import { ChainUtils } from "../../utils/chainUtils";
import { logger } from "../../utils/logger";
import { memoize } from "../../utils/memoize";
import { retry } from "../../utils/retry";

// ======== TypeScript Interfaces ========

export interface AxelarConfigV2 {
  environment: Environment;
  rpcUrl?: string;
  enableMonitoring?: boolean;
  cacheTimeout?: number; // In milliseconds
  maxRetries?: number;
  retryDelay?: number; // Base delay in milliseconds
  recoveryEnabled?: boolean;
}

export interface TransferQuoteV2 {
  fee: string;
  estimatedTime: string;
  route: string[];
  estimatedGas: string;
  feeBreakdown: FeeBreakdown;
  routeOptions?: RouteOption[];
  tokenPrice?: string;
  estimatedUsdValue?: string;
  estimatedConfirmations?: number;
}

export interface FeeBreakdown {
  networkFee: string; // Gas fee for the transaction
  bridgeFee: string; // Fee charged by Axelar
  relayerFee?: string; // Fee for relayers (if applicable)
  totalFee: string; // Sum of all fees
  estimatedUsd?: string; // USD value of total fee
}

export interface RouteOption {
  protocol: 'axelar' | 'wormhole' | 'layerzero' | 'other';
  time: string; // Estimated time in minutes
  cost: string; // Total cost in native token
  costUsd?: string; // Cost in USD
  security: 'high' | 'medium' | 'low';
  recommended: boolean;
}

export interface TransactionDetailsV2 {
  txHash: string;
  sourceChain: string;
  destinationChain: string;
  sourceAddress: string;
  destinationAddress: string;
  asset: string;
  amount: string;
  status: TransactionStatus;
  timestamp: number;
  estimatedCompletionTime?: number;
  message?: string;
  error?: string;
}

export interface BatchTransferParams {
  fromChain: string;
  toChain: string;
  transfers: {
    asset: string;
    amount: string;
    toAddress: string;
  }[];
}

export interface PortfolioBalanceParams {
  chains: string[];
  address: string;
  includeNativeTokens?: boolean;
  includeTokens?: boolean;
}

export interface ChainAssetBalance {
  chain: string;
  assets: {
    symbol: string;
    name: string;
    address: string;
    amount: string;
    decimals: number;
    usdValue?: string;
    priceUsd?: string;
  }[];
  totalUsdValue?: string;
}

export interface CrossChainPortfolio {
  balances: ChainAssetBalance[];
  totalUsdValue: string;
  lastUpdated: number;
}

export interface PerformanceMetrics {
  requestCount: number;
  averageResponseTime: number;
  errorRate: number;
  cacheHitRate: number;
  lastUpdated: number;
}

// ======== Utility Classes ========

/**
 * Manages caching and retrieval of transfer quotes
 */
class QuoteManager {
  private cacheTimeout: number;
  private queryAPI: AxelarQueryAPI;
  private environment: Environment;

  constructor(queryAPI: AxelarQueryAPI, environment: Environment, cacheTimeout: number = 30000) {
    this.queryAPI = queryAPI;
    this.environment = environment;
    this.cacheTimeout = cacheTimeout;
  }

  /**
   * Get transfer quote with caching
   */
  getTransferQuote = memoize(
    async (
      fromChain: string,
      toChain: string,
      asset: string,
      amount: string
    ): Promise<TransferQuoteV2> => {
      try {
        const amountNumber = parseFloat(amount);
        if (isNaN(amountNumber)) {
          throw new Error('Invalid amount');
        }

        const feeResponse = await retry(
          () => this.queryAPI.getTransferFee(fromChain, toChain, asset, amountNumber),
          { maxRetries: 3, delay: 1000 }
        );

        // Get gas estimate for the transaction
        const gasEstimate = await retry(
          () => this.queryAPI.estimateGasFee(
            fromChain as EvmChain,
            toChain as EvmChain,
            '100000' // Default gas limit
          ),
          { maxRetries: 3, delay: 1000 }
        );

        // Calculate estimated time based on historical data and chain congestion
        const estimatedTime = this.calculateEstimatedTime(fromChain, toChain);

        // Get token price for USD conversion if available
        let tokenPrice = '0';
        try {
          // This would be replaced with actual price API call
          tokenPrice = await this.getTokenPrice(asset);
        } catch (error) {
          logger.warn('Failed to get token price:', error);
        }

        // Calculate fee breakdown
        const networkFee = typeof gasEstimate === 'string' ? gasEstimate : gasEstimate.baseFee;
        const bridgeFee = feeResponse?.fee?.amount || '0';
        const totalFee = (parseFloat(networkFee) + parseFloat(bridgeFee)).toString();
        const estimatedUsdValue = parseFloat(tokenPrice) * parseFloat(totalFee);

        // Get alternative route options if available
        const routeOptions = await this.getRouteOptions(fromChain, toChain, asset, amount);

        return {
          fee: totalFee,
          estimatedTime,
          route: [fromChain, toChain],
          estimatedGas: networkFee,
          feeBreakdown: {
            networkFee,
            bridgeFee,
            totalFee,
            estimatedUsd: estimatedUsdValue.toFixed(2)
          },
          routeOptions,
          tokenPrice,
          estimatedUsdValue: (parseFloat(tokenPrice) * parseFloat(amount)).toFixed(2),
          estimatedConfirmations: this.getEstimatedConfirmations(fromChain, toChain)
        };
      } catch (error) {
        logger.error('Error getting transfer quote:', error);
        throw new AxelarServiceError('Failed to get transfer quote', { cause: error });
      }
    },
    { ttl: this.cacheTimeout }
  );

  /**
   * Calculate estimated time based on source and destination chains
   */
  private calculateEstimatedTime(fromChain: string, toChain: string): string {
    // Base times in minutes
    const baseTimes: Record<string, number> = {
      'ethereum': 15,
      'polygon': 8,
      'avalanche': 5,
      'arbitrum': 10,
      'optimism': 12,
      'binance': 6,
      'base': 8,
      'linea': 10
    };

    const fromTime = baseTimes[fromChain.toLowerCase()] || 10;
    const toTime = baseTimes[toChain.toLowerCase()] || 10;
    
    // Calculate estimated time range
    const minTime = Math.max(5, fromTime);
    const maxTime = fromTime + toTime;
    
    return `${minTime}-${maxTime} minutes`;
  }

  /**
   * Get estimated number of confirmations required
   */
  private getEstimatedConfirmations(fromChain: string, toChain: string): number {
    const confirmations: Record<string, number> = {
      'ethereum': 15,
      'polygon': 128,
      'avalanche': 12,
      'arbitrum': 20,
      'optimism': 15,
      'binance': 15,
      'base': 12
    };
    
    return confirmations[fromChain.toLowerCase()] || 15;
  }

  /**
   * Get token price (placeholder - would connect to a price API)
   */
  private async getTokenPrice(asset: string): Promise<string> {
    // This would be replaced with actual price API integration
    const mockPrices: Record<string, string> = {
      'ETH': '3500',
      'USDC': '1',
      'USDT': '1',
      'WETH': '3500',
      'WBTC': '65000',
      'DAI': '1'
    };
    
    return mockPrices[asset.toUpperCase()] || '0';
  }

  /**
   * Get alternative route options for comparison
   */
  private async getRouteOptions(
    fromChain: string,
    toChain: string,
    asset: string,
    amount: string
  ): Promise<RouteOption[]> {
    // In a real implementation, this would query multiple bridge protocols
    // For now, we'll return mock data for comparison
    
    const axelarOption: RouteOption = {
      protocol: 'axelar',
      time: this.calculateEstimatedTime(fromChain, toChain),
      cost: (await this.getTransferQuote(fromChain, toChain, asset, amount)).fee,
      security: 'high',
      recommended: true
    };
    
    // Mock alternative options
    const alternatives: RouteOption[] = [
      {
        protocol: 'wormhole',
        time: `${parseInt(axelarOption.time.split('-')[0]) + 2}-${parseInt(axelarOption.time.split('-')[1]) + 5} minutes`,
        cost: (parseFloat(axelarOption.cost) * 0.9).toString(), // 10% cheaper
        security: 'high',
        recommended: false
      },
      {
        protocol: 'layerzero',
        time: `${parseInt(axelarOption.time.split('-')[0]) - 2}-${parseInt(axelarOption.time.split('-')[1]) - 3} minutes`,
        cost: (parseFloat(axelarOption.cost) * 1.15).toString(), // 15% more expensive
        security: 'high',
        recommended: false
      }
    ];
    
    return [axelarOption, ...alternatives];
  }
}

/**
 * Manages transaction execution and monitoring
 */
class TransactionManager {
  private assetTransfer: AxelarAssetTransfer;
  private queryAPI: AxelarQueryAPI;
  private recoveryAPI: AxelarGMPRecoveryAPI | null;
  private environment: Environment;
  private maxRetries: number;
  private retryDelay: number;
  private transactions: Map<string, TransactionDetailsV2>;

  constructor(
    assetTransfer: AxelarAssetTransfer,
    queryAPI: AxelarQueryAPI,
    environment: Environment,
    recoveryAPI: AxelarGMPRecoveryAPI | null = null,
    maxRetries: number = 3,
    retryDelay: number = 1000
  ) {
    this.assetTransfer = assetTransfer;
    this.queryAPI = queryAPI;
    this.recoveryAPI = recoveryAPI;
    this.environment = environment;
    this.maxRetries = maxRetries;
    this.retryDelay = retryDelay;
    this.transactions = new Map<string, TransactionDetailsV2>();
  }

  /**
   * Execute cross-chain transfer with retry logic
   */
  async executeTransfer(
    fromChain: string,
    toChain: string,
    toAddress: string,
    asset: string,
    amount: string,
    provider: ethers.providers.Web3Provider
  ): Promise<string> {
    try {
      const signer = provider.getSigner();

      // Prepare the send token parameters
      const sendTokenParams: SendTokenParams = {
        fromChain,
        toChain,
        destinationAddress: toAddress,
        asset: {
          symbol: asset
        },
        amountInAtomicUnits: amount,
        options: {
          evmOptions: {
            signer,
            provider
          }
        }
      };

      // Execute with retry logic
      const txResponse = await retry(
        () => this.assetTransfer.sendToken(sendTokenParams),
        { maxRetries: this.maxRetries, delay: this.retryDelay, backoff: 'exponential' }
      );

      // Extract transaction hash
      let txHash = '';
      if ('hash' in txResponse) {
        txHash = txResponse.hash;
      } else if ('transactionHash' in txResponse) {
        txHash = (txResponse as any).transactionHash;
      } else {
        throw new Error('Unable to extract transaction hash from response');
      }

      // Store transaction details for monitoring
      const txDetails: TransactionDetailsV2 = {
        txHash,
        sourceChain: fromChain,
        destinationChain: toChain,
        sourceAddress: await signer.getAddress(),
        destinationAddress: toAddress,
        asset,
        amount,
        status: 'pending',
        timestamp: Date.now(),
        estimatedCompletionTime: this.calculateEstimatedCompletionTime(fromChain, toChain)
      };

      this.transactions.set(txHash, txDetails);

      // Start monitoring the transaction
      this.monitorTransaction(txHash);

      return txHash;
    } catch (error) {
      logger.error('Error executing transfer:', error);
      throw new AxelarServiceError('Failed to execute transfer', { cause: error });
    }
  }

  /**
   * Monitor transaction status with regular polling
   */
  private async monitorTransaction(txHash: string): Promise<void> {
    try {
      const txDetails = this.transactions.get(txHash);
      if (!txDetails) return;

      // Initial delay before first check
      await new Promise(resolve => setTimeout(resolve, 5000));

      let completed = false;
      let attempts = 0;
      const maxAttempts = 30; // Stop after 30 attempts (with increasing delays)

      while (!completed && attempts < maxAttempts) {
        try {
          // Get transaction status from Axelar API
          const status = await this.getTransactionStatus(txHash, txDetails.sourceChain, txDetails.destinationChain);
          
          // Update transaction details with new status
          this.transactions.set(txHash, {
            ...txDetails,
            status: status.status,
            message: status.message
          });

          // Check if transaction is completed or failed
          if (['executed', 'error', 'completed'].includes(status.status)) {
            completed = true;
            logger.info(`Transaction ${txHash} completed with status: ${status.status}`);
            
            // If error occurred and recovery API is available, attempt recovery
            if (status.status === 'error' && this.recoveryAPI) {
              this.attemptTransactionRecovery(txHash);
            }
          }
        } catch (error) {
          logger.warn(`Error checking transaction status for ${txHash}:`, error);
        }

        // Increase delay between checks as attempts increase
        const delay = Math.min(5000 * Math.pow(1.5, attempts), 60000); // Max 1 minute
        await new Promise(resolve => setTimeout(resolve, delay));
        attempts++;
      }

      if (!completed) {
        logger.warn(`Transaction monitoring timed out for ${txHash}`);
        this.transactions.set(txHash, {
          ...txDetails,
          status: 'unknown',
          message: 'Transaction monitoring timed out'
        });
      }
    } catch (error) {
      logger.error(`Error monitoring transaction ${txHash}:`, error);
    }
  }

  /**
   * Get detailed transaction status
   */
  async getTransactionStatus(
    txHash: string,
    sourceChain?: string,
    destinationChain?: string
  ): Promise<GMPStatusResponse> {
    try {
      // If we have the transaction in our store, use those chain details
      const txDetails = this.transactions.get(txHash);
      const fromChain = sourceChain || txDetails?.sourceChain;
      const toChain = destinationChain || txDetails?.destinationChain;

      if (!fromChain || !toChain) {
        throw new Error('Source and destination chains are required for status check');
      }

      // Query transaction status from Axelar API
      const status = await retry(
        () => this.queryAPI.queryTransactionStatus(txHash, fromChain, toChain),
        { maxRetries: 3, delay: 1000 }
      );

      return status;
    } catch (error) {
      logger.error('Error getting transaction status:', error);
      throw new AxelarServiceError('Failed to get transaction status', { cause: error });
    }
  }

  /**
   * Attempt to recover a failed transaction
   */
  private async attemptTransactionRecovery(txHash: string): Promise<boolean> {
    try {
      if (!this.recoveryAPI) {
        logger.warn('Recovery API not initialized, cannot attempt recovery');
        return false;
      }

      const txDetails = this.transactions.get(txHash);
      if (!txDetails) {
        logger.warn(`Transaction ${txHash} not found for recovery`);
        return false;
      }

      // Get recovery parameters
      const recoveryParams: AxelarRecoveryAPIParams = {
        txHash,
        sourceChain: txDetails.sourceChain,
        destinationChain: txDetails.destinationChain
      };

      // Attempt recovery
      const recoveryResult = await this.recoveryAPI.recoverGMPTransaction(recoveryParams);

      if (recoveryResult.success) {
        logger.info(`Successfully initiated recovery for transaction ${txHash}`);
        
        // Update transaction status
        this.transactions.set(txHash, {
          ...txDetails,
          status: 'recovering',
          message: 'Transaction recovery in progress'
        });

        // Monitor the recovery process
        this.monitorRecovery(txHash, recoveryResult.recoveryTransactionHash);
        return true;
      } else {
        logger.warn(`Recovery failed for transaction ${txHash}: ${recoveryResult.error}`);
        return false;
      }
    } catch (error) {
      logger.error(`Error attempting recovery for transaction ${txHash}:`, error);
      return false;
    }
  }

  /**
   * Monitor the recovery process for a transaction
   */
  private async monitorRecovery(txHash: string, recoveryTxHash: string): Promise<void> {
    try {
      const txDetails = this.transactions.get(txHash);
      if (!txDetails) return;

      // Initial delay before first check
      await new Promise(resolve => setTimeout(resolve, 10000));

      let completed = false;
      let attempts = 0;
      const maxAttempts = 20;

      while (!completed && attempts < maxAttempts) {
        try {
          // Check recovery status
          const status = await this.recoveryAPI?.getRecoveryStatus(recoveryTxHash);
          
          if (status?.status === 'completed') {
            completed = true;
            logger.info(`Recovery completed for transaction ${txHash}`);
            
            // Update transaction status
            this.transactions.set(txHash, {
              ...txDetails,
              status: 'completed',
              message: 'Transaction recovered successfully'
            });
          } else if (status?.status === 'failed') {
            completed = true;
            logger.warn(`Recovery failed for transaction ${txHash}`);
            
            // Update transaction status
            this.transactions.set(txHash, {
              ...txDetails,
              status: 'failed',
              message: status?.error || 'Transaction recovery failed'
            });
          }
        } catch (error) {
          logger.warn(`Error checking recovery status for ${txHash}:`, error);
        }

        // Increase delay between checks
        const delay = Math.min(10000 * Math.pow(1.5, attempts), 120000); // Max 2 minutes
        await new Promise(resolve => setTimeout(resolve, delay));
        attempts++;
      }

      if (!completed) {
        logger.warn(`Recovery monitoring timed out for ${txHash}`);
        this.transactions.set(txHash, {
          ...txDetails,
          status: 'unknown',
          message: 'Recovery monitoring timed out'
        });
      }
    } catch (error) {
      logger.error(`Error monitoring recovery for transaction ${txHash}:`, error);
    }
  }

  /**
   * Calculate estimated completion time based on source and destination chains
   */
  private calculateEstimatedCompletionTime(fromChain: string, toChain: string): number {
    // Base times in minutes
    const baseTimes: Record<string, number> = {
      'ethereum': 15,
      'polygon': 8,
      'avalanche': 5,
      'arbitrum': 10,
      'optimism': 12,
      'binance': 6,
      'base': 8
    };

    const fromTime = baseTimes[fromChain.toLowerCase()] || 10;
    const toTime = baseTimes[toChain.toLowerCase()] || 10;
    
    // Calculate estimated time in milliseconds
    const estimatedMinutes = fromTime + toTime;
    return Date.now() + (estimatedMinutes * 60 * 1000);
  }

  /**
   * Get all tracked transactions
   */
  getAllTransactions(): TransactionDetailsV2[] {
    return Array.from(this.transactions.values());
  }

  /**
   * Get transaction details by hash
   */
  getTransaction(txHash: string): TransactionDetailsV2 | undefined {
    return this.transactions.get(txHash);
  }

  /**
   * Execute batch transfers (if supported by the protocol)
   */
  async executeBatchTransfer(
    params: BatchTransferParams,
    provider: ethers.providers.Web3Provider
  ): Promise<string[]> {
    try {
      const signer = provider.getSigner();
      const txHashes: string[] = [];

      // Execute transfers in sequence
      // Note: In a real implementation, this could use batching if supported by the protocol
      for (const transfer of params.transfers) {
        const txHash = await this.executeTransfer(
          params.fromChain,
          params.toChain,
          transfer.toAddress,
          transfer.asset,
          transfer.amount,
          provider
        );
        txHashes.push(txHash);
      }

      return txHashes;
    } catch (error) {
      logger.error('Error executing batch transfer:', error);
      throw new AxelarServiceError('Failed to execute batch transfer', { cause: error });
    }
  }
}

/**
 * Manages cross-chain portfolio operations
 */
class PortfolioManager {
  private queryAPI: AxelarQueryAPI;
  private environment: Environment;
  private cacheTimeout: number;

  constructor(queryAPI: AxelarQueryAPI, environment: Environment, cacheTimeout: number = 60000) {
    this.queryAPI = queryAPI;
    this.environment = environment;
    this.cacheTimeout = cacheTimeout;
  }

  /**
   * Get cross-chain portfolio balances with caching
   */
  getPortfolioBalances = memoize(
    async (params: PortfolioBalanceParams): Promise<CrossChainPortfolio> => {
      try {
        const { chains, address, includeNativeTokens = true, includeTokens = true } = params;
        
        // Process each chain in parallel
        const chainBalances = await Promise.all(
          chains.map(async (chain) => {
            try {
              // This would use Axelar API or other chain-specific APIs to get balances
              // For now, we'll use a placeholder implementation
              const assets = await this.getChainBalances(chain, address, includeNativeTokens, includeTokens);
              
              // Calculate total USD value for this chain
              const totalUsdValue = assets.reduce((sum, asset) => {
                return sum + (parseFloat(asset.usdValue || '0'));
              }, 0);
              
              return {
                chain,
                assets,
                totalUsdValue: totalUsdValue.toFixed(2)
              };
            } catch (error) {
              logger.warn(`Error fetching balances for chain ${chain}:`, error);
              return {
                chain,
                assets: [],
                totalUsdValue: '0'
              };
            }
          })
        );
        
        // Calculate total USD value across all chains
        const totalUsdValue = chainBalances.reduce((sum, chain) => {
          return sum + parseFloat(chain.totalUsdValue || '0');
        }, 0);
        
        return {
          balances: chainBalances,
          totalUsdValue: totalUsdValue.toFixed(2),
          lastUpdated: Date.now()
        };
      } catch (error) {
        logger.error('Error getting portfolio balances:', error);
        throw new AxelarServiceError('Failed to get portfolio balances', { cause: error });
      }
    },
    { ttl: this.cacheTimeout }
  );

  /**
   * Get balances for a specific chain (placeholder implementation)
   */
  private async getChainBalances(
    chain: string,
    address: string,
    includeNativeTokens: boolean,
    includeTokens: boolean
  ): Promise<ChainAssetBalance['assets']> {
    // This would be replaced with actual chain-specific API calls
    // For now, we'll return mock data
    
    const mockAssets: ChainAssetBalance['assets'] = [];
    
    if (includeNativeTokens) {
      // Add native token based on chain
      const nativeToken = {
        ethereum: { symbol: 'ETH', name: 'Ethereum', decimals: 18 },
        polygon: { symbol: 'MATIC', name: 'Polygon', decimals: 18 },
        avalanche: { symbol: 'AVAX', name: 'Avalanche', decimals: 18 },
        arbitrum: { symbol: 'ETH', name: 'Ethereum', decimals: 18 },
        optimism: { symbol: 'ETH', name: 'Ethereum', decimals: 18 },
        binance: { symbol: 'BNB', name: 'Binance Coin', decimals: 18 },
        base: { symbol: 'ETH', name: 'Ethereum', decimals: 18 }
      }[chain.toLowerCase()];
      
      if (nativeToken) {
        const amount = (Math.random() * 10).toFixed(4);
        const priceUsd = nativeToken.symbol === 'ETH' ? '3500' : 
                         nativeToken.symbol === 'MATIC' ? '0.70' : 
                         nativeToken.symbol === 'AVAX' ? '35' : 
                         nativeToken.symbol === 'BNB' ? '600' : '1';
        
        mockAssets.push({
          symbol: nativeToken.symbol,
          name: nativeToken.name,
          address: 'native',
          amount,
          decimals: nativeToken.decimals,
          priceUsd,
          usdValue: (parseFloat(amount) * parseFloat(priceUsd)).toFixed(2)
        });
      }
    }
    
    if (includeTokens) {
      // Add some common tokens
      const commonTokens = [
        { symbol: 'USDC', name: 'USD Coin', decimals: 6, price: '1.00' },
        { symbol: 'USDT', name: 'Tether', decimals: 6, price: '1.00' },
        { symbol: 'DAI', name: 'Dai Stablecoin', decimals: 18, price: '1.00' },
        { symbol: 'WETH', name: 'Wrapped Ethereum', decimals: 18, price: '3500' },
        { symbol: 'WBTC', name: 'Wrapped Bitcoin', decimals: 8, price: '65000' }
      ];
      
      // Add 1-3 random tokens
      const numTokens = Math.floor(Math.random() * 3) + 1;
      for (let i = 0; i < numTokens; i++) {
        const token = commonTokens[Math.floor(Math.random() * commonTokens.length)];
        const amount = (Math.random() * 1000).toFixed(token.decimals === 18 ? 4 : 2);
        
        mockAssets.push({
          symbol: token.symbol,
          name: token.name,
          address: `0x${Math.random().toString(16).substring(2, 42)}`,
          amount,
          decimals: token.decimals,
          priceUsd: token.price,
          usdValue: (parseFloat(amount) * parseFloat(token.price)).toFixed(2)
        });
      }
    }
    
    return mockAssets;
  }

  /**
   * Optimize portfolio allocation across chains
   */
  async optimizePortfolioAllocation(
    currentPortfolio: CrossChainPortfolio,
    targetAllocation: { chain: string; percentage: number }[]
  ): Promise<{ moves: { fromChain: string; toChain: string; asset: string; amount: string }[] }> {
    // This would implement portfolio optimization logic
    // For now, we'll return a placeholder implementation
    
    const moves = [];
    
    // Simple rebalancing strategy: identify imbalances and suggest moves
    const totalValue = parseFloat(currentPortfolio.totalUsdValue);
    
    // Calculate current allocation percentages
    const currentAllocation = currentPortfolio.balances.map(chain => ({
      chain: chain.chain,
      percentage: (parseFloat(chain.totalUsdValue || '0') / totalValue) * 100
    }));
    
    // Find chains that need rebalancing
    for (const target of targetAllocation) {
      const current = currentAllocation.find(c => c.chain === target.chain);
      const currentPercentage = current ? current.percentage : 0;
      
      // If significant difference, suggest a move
      if (Math.abs(currentPercentage - target.percentage) > 5) {
        if (currentPercentage < target.percentage) {
          // Need to move assets TO this chain
          const deficit = ((target.percentage - currentPercentage) / 100) * totalValue;
          
          // Find a chain with excess funds
          const excessChains = currentAllocation.filter(c => {
            const targetPct = targetAllocation.find(t => t.chain === c.chain)?.percentage || 0;
            return c.percentage > targetPct + 5;
          });
          
          if (excessChains.length > 0) {
            const sourceChain = excessChains[0].chain;
            const sourceBalance = currentPortfolio.balances.find(b => b.chain === sourceChain);
            
            if (sourceBalance && sourceBalance.assets.length > 0) {
              // Prefer stablecoins for transfers when available
              const stablecoin = sourceBalance.assets.find(a => 
                ['USDC', 'USDT', 'DAI'].includes(a.symbol)
              );
              
              const assetToMove = stablecoin || sourceBalance.assets[0];
              const amountToMove = Math.min(
                parseFloat(assetToMove.amount),
                parseFloat(assetToMove.usdValue || '0') > deficit ? 
                  deficit / parseFloat(assetToMove.priceUsd || '1') : 
                  parseFloat(assetToMove.amount)
              ).toFixed(6);
              
              moves.push({
                fromChain: sourceChain,
                toChain: target.chain,
                asset: assetToMove.symbol,
                amount: amountToMove
              });
            }
          }
        }
      }
    }
    
    return { moves };
  }
}

/**
 * Monitoring service for tracking performance metrics
 */
class MonitoringService {
  private metrics: PerformanceMetrics;
  private requestTimes: number[];
  private errorCount: number;
  private requestCount: number;
  private cacheHits: number;
  private cacheMisses: number;

  constructor() {
    this.metrics = {
      requestCount: 0,
      averageResponseTime: 0,
      errorRate: 0,
      cacheHitRate: 0,
      lastUpdated: Date.now()
    };
    this.requestTimes = [];
    this.errorCount = 0;
    this.requestCount = 0;
    this.cacheHits = 0;
    this.cacheMisses = 0;
  }

  /**
   * Record the start of a request
   */
  startRequest(): number {
    this.requestCount++;
    this.metrics.requestCount++;
    return Date.now();
  }

  /**
   * Record the completion of a request
   */
  completeRequest(startTime: number, isError: boolean = false, isCacheHit: boolean = false): void {
    const duration = Date.now() - startTime;
    this.requestTimes.push(duration);
    
    // Keep only the last 100 request times
    if (this.requestTimes.length > 100) {
      this.requestTimes.shift();
    }
    
    // Update average response time
    this.metrics.averageResponseTime = this.requestTimes.reduce((sum, time) => sum + time, 0) / this.requestTimes.length;
    
    // Update error rate
    if (isError) {
      this.errorCount++;
    }
    this.metrics.errorRate = (this.errorCount / this.requestCount) * 100;
    
    // Update cache hit rate
    if (isCacheHit) {
      this.cacheHits++;
    } else {
      this.cacheMisses++;
    }
    this.metrics.cacheHitRate = (this.cacheHits / (this.cacheHits + this.cacheMisses)) * 100;
    
    // Update timestamp
    this.metrics.lastUpdated = Date.now();
  }

  /**
   * Get current metrics
   */
  getMetrics(): PerformanceMetrics {
    return { ...this.metrics };
  }

  /**
   * Reset metrics
   */
  resetMetrics(): void {
    this.metrics = {
      requestCount: 0,
      averageResponseTime: 0,
      errorRate: 0,
      cacheHitRate: 0,
      lastUpdated: Date.now()
    };
    this.requestTimes = [];
    this.errorCount = 0;
    this.requestCount = 0;
    this.cacheHits = 0;
    this.cacheMisses = 0;
  }
}

/**
 * Custom error class for Axelar service errors
 */
export class AxelarServiceError extends Error {
  cause?: Error;

  constructor(message: string, options?: { cause?: Error }) {
    super(message);
    this.name = 'AxelarServiceError';
    this.cause = options?.cause;
  }
}

/**
 * Main Axelar service class that integrates all components
 */
export class AxelarServiceV2 {
  private assetTransfer: AxelarAssetTransfer | null = null;
  private queryAPI: AxelarQueryAPI | null = null;
  private recoveryAPI: AxelarGMPRecoveryAPI | null = null;
  private environment: Environment;
  private isInitialized: boolean = false;
  
  // Component managers
  private quoteManager: QuoteManager | null = null;
  private transactionManager: TransactionManager | null = null;
  private portfolioManager: PortfolioManager | null = null;
  private monitoringService: MonitoringService | null = null;

  // Configuration
  private config: AxelarConfigV2;

  constructor(config: AxelarConfigV2 = { environment: Environment.MAINNET }) {
    this.environment = config.environment;
    this.config = {
      ...config,
      cacheTimeout: config.cacheTimeout || 30000, // Default 30 seconds
      maxRetries: config.maxRetries || 3,
      retryDelay: config.retryDelay || 1000,
      enableMonitoring: config.enableMonitoring !== false,
      recoveryEnabled: config.recoveryEnabled !== false
    };
    
    try {
      // Initialize AxelarAssetTransfer
      this.assetTransfer = new AxelarAssetTransfer({
        environment: this.environment,
        auth: "metamask" // Use metamask for browser environment
      });

      // Initialize AxelarQueryAPI
      this.queryAPI = new AxelarQueryAPI({
        environment: this.environment,
        axelarRpcUrl: config.rpcUrl
      });

      // Initialize AxelarGMPRecoveryAPI if recovery is enabled
      if (this.config.recoveryEnabled) {
        this.recoveryAPI = new AxelarGMPRecoveryAPI({
          environment: this.environment
        });
      }

      // Initialize component managers
      if (this.queryAPI) {
        this.quoteManager = new QuoteManager(
          this.queryAPI,
          this.environment,
          this.config.cacheTimeout
        );
        
        this.portfolioManager = new PortfolioManager(
          this.queryAPI,
          this.environment,
          this.config.cacheTimeout
        );
      }

      if (this.assetTransfer && this.queryAPI) {
        this.transactionManager = new TransactionManager(
          this.assetTransfer,
          this.queryAPI,
          this.environment,
          this.recoveryAPI,
          this.config.maxRetries,
          this.config.retryDelay
        );
      }

      if (this.config.enableMonitoring) {
        this.monitoringService = new MonitoringService();
      }

      this.isInitialized = true;
      logger.service('axelar', `AxelarServiceV2 initialized successfully for ${this.environment}`);
    } catch (error) {
      logger.warn(`Failed to initialize AxelarServiceV2 for ${this.environment}:`, error);
      
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
          
          // Initialize component managers with fallback environment
          if (this.queryAPI) {
            this.quoteManager = new QuoteManager(
              this.queryAPI,
              this.environment,
              this.config.cacheTimeout
            );
            
            this.portfolioManager = new PortfolioManager(
              this.queryAPI,
              this.environment,
              this.config.cacheTimeout
            );
          }

          if (this.assetTransfer && this.queryAPI) {
            this.transactionManager = new TransactionManager(
              this.assetTransfer,
              this.queryAPI,
              this.environment,
              null, // No recovery API in fallback mode
              this.config.maxRetries,
              this.config.retryDelay
            );
          }

          if (this.config.enableMonitoring) {
            this.monitoringService = new MonitoringService();
          }
          
          this.isInitialized = true;
          logger.service('axelar', 'AxelarServiceV2 initialized with testnet fallback');
        } catch (fallbackError) {
          logger.error("Failed to initialize AxelarServiceV2 with testnet fallback:", fallbackError);
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
    return this.isInitialized && 
           this.assetTransfer !== null && 
           this.queryAPI !== null && 
           this.quoteManager !== null && 
           this.transactionManager !== null;
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
        'base': 'base',
        'linea': 'linea'
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
        .filter((name): name is string => name !== undefined && this.getAxelarChainName(name) !== null);
    } catch (error) {
      logger.error('Error getting supported chains:', error);
      return [];
    }
  }

  /**
   * Get transfer quote with enhanced details
   */
  async getTransferQuote(
    fromChain: string,
    toChain: string,
    asset: string,
    amount: string
  ): Promise<TransferQuoteV2> {
    if (!this.isReady() || !this.quoteManager) {
      throw new AxelarServiceError('Axelar service not initialized');
    }

    let startTime = 0;
    let isCacheHit = false;
    
    if (this.monitoringService) {
      startTime = this.monitoringService.startRequest();
    }

    try {
      const fromAxelarChain = this.getAxelarChainName(fromChain);
      const toAxelarChain = this.getAxelarChainName(toChain);

      if (!fromAxelarChain || !toAxelarChain) {
        throw new AxelarServiceError(`Unsupported chain: ${fromChain} -> ${toChain}`);
      }

      // Use the QuoteManager to get a quote with caching
      const quote = await this.quoteManager.getTransferQuote(
        fromAxelarChain,
        toAxelarChain,
        asset,
        amount
      );
      
      if (this.monitoringService) {
        this.monitoringService.completeRequest(startTime, false, isCacheHit);
      }
      
      return quote;
    } catch (error) {
      if (this.monitoringService) {
        this.monitoringService.completeRequest(startTime, true, isCacheHit);
      }
      
      logger.error('Error getting transfer quote:', error);
      throw new AxelarServiceError('Failed to get transfer quote', { cause: error as Error });
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
      throw new AxelarServiceError('Axelar service not initialized');
    }

    let startTime = 0;
    if (this.monitoringService) {
      startTime = this.monitoringService.startRequest();
    }

    try {
      const fromAxelarChain = this.getAxelarChainName(fromChain);
      const toAxelarChain = this.getAxelarChainName(toChain);

      if (!fromAxelarChain || !toAxelarChain) {
        throw new AxelarServiceError(`Unsupported chain: ${fromChain} -> ${toChain}`);
      }

      // Use retry logic for deposit address
      const depositAddress = await retry(
        () => this.assetTransfer!.getDepositAddress({
          fromChain: fromAxelarChain,
          toChain: toAxelarChain,
          destinationAddress: toAddress,
          asset: asset
        }),
        { maxRetries: this.config.maxRetries, delay: this.config.retryDelay, backoff: 'exponential' }
      );
      
      if (this.monitoringService) {
        this.monitoringService.completeRequest(startTime);
      }

      return depositAddress;
    } catch (error) {
      if (this.monitoringService) {
        this.monitoringService.completeRequest(startTime, true);
      }
      
      logger.error('Error getting deposit address:', error);
      throw new AxelarServiceError('Failed to get deposit address', { cause: error as Error });
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
    provider: ethers.providers.Web3Provider
  ): Promise<string> {
    if (!this.isReady() || !this.transactionManager) {
      throw new AxelarServiceError('Axelar service not initialized');
    }

    let startTime = 0;
    if (this.monitoringService) {
      startTime = this.monitoringService.startRequest();
    }

    try {
      const fromAxelarChain = this.getAxelarChainName(fromChain);
      const toAxelarChain = this.getAxelarChainName(toChain);

      if (!fromAxelarChain || !toAxelarChain) {
        throw new AxelarServiceError(`Unsupported chain: ${fromChain} -> ${toChain}`);
      }

      // Execute the transfer using the transaction manager
      const txHash = await this.transactionManager.executeTransfer(
        fromAxelarChain,
        toAxelarChain,
        toAddress,
        asset,
        amount,
        provider
      );
      
      if (this.monitoringService) {
        this.monitoringService.completeRequest(startTime);
      }

      return txHash;
    } catch (error) {
      if (this.monitoringService) {
        this.monitoringService.completeRequest(startTime, true);
      }
      
      logger.error('Error executing transfer:', error);
      throw new AxelarServiceError('Failed to execute transfer', { cause: error as Error });
    }
  }

  /**
   * Get transaction status
   */
  async getTransactionStatus(
    txHash: string,
    sourceChain?: string,
    destinationChain?: string
  ): Promise<GMPStatusResponse> {
    if (!this.isReady() || !this.transactionManager) {
      throw new AxelarServiceError('Axelar service not initialized');
    }

    let startTime = 0;
    if (this.monitoringService) {
      startTime = this.monitoringService.startRequest();
    }

    try {
      let fromChain = sourceChain;
      let toChain = destinationChain;
      
      // If chains not provided, try to get from stored transaction
      if ((!fromChain || !toChain) && txHash) {
        const txDetails = this.transactionManager.getTransaction(txHash);
        if (txDetails) {
          fromChain = txDetails.sourceChain;
          toChain = txDetails.destinationChain;
        }
      }
      
      if (!fromChain || !toChain) {
        throw new AxelarServiceError('Source and destination chains are required for status check');
      }

      // Convert to Axelar chain names if needed
      const fromAxelarChain = this.getAxelarChainName(fromChain) || fromChain;
      const toAxelarChain = this.getAxelarChainName(toChain) || toChain;

      // Get status using transaction manager
      const status = await this.transactionManager.getTransactionStatus(
        txHash,
        fromAxelarChain,
        toAxelarChain
      );
      
      if (this.monitoringService) {
        this.monitoringService.completeRequest(startTime);
      }

      return status;
    } catch (error) {
      if (this.monitoringService) {
        this.monitoringService.completeRequest(startTime, true);
      }
      
      logger.error('Error getting transaction status:', error);
      throw new AxelarServiceError('Failed to get transaction status', { cause: error as Error });
    }
  }

  /**
   * Get gas fee estimate for cross-chain transaction
   */
  async getGasFeeEstimate(
    fromChain: string,
    toChain: string,
    gasLimit: string = "100000"
  ): Promise<string | GasEstimateResponse> {
    if (!this.isReady() || !this.queryAPI) {
      throw new AxelarServiceError('Axelar service not initialized');
    }

    let startTime = 0;
    if (this.monitoringService) {
      startTime = this.monitoringService.startRequest();
    }

    try {
      const fromAxelarChain = this.getAxelarChainName(fromChain);
      const toAxelarChain = this.getAxelarChainName(toChain);

      if (!fromAxelarChain || !toAxelarChain) {
        throw new AxelarServiceError(`Unsupported chain: ${fromChain} -> ${toChain}`);
      }

      // Use retry logic for gas estimate
      const gasFee = await retry(
        () => this.queryAPI!.estimateGasFee(
          fromAxelarChain as EvmChain,
          toAxelarChain as EvmChain,
          gasLimit
        ),
        { maxRetries: this.config.maxRetries, delay: this.config.retryDelay }
      );
      
      if (this.monitoringService) {
        this.monitoringService.completeRequest(startTime);
      }

      return gasFee;
    } catch (error) {
      if (this.monitoringService) {
        this.monitoringService.completeRequest(startTime, true);
      }
      
      logger.error('Error getting gas fee estimate:', error);
      throw new AxelarServiceError('Failed to get gas fee estimate', { cause: error as Error });
    }
  }

  /**
   * Check if chains are active
   */
  async areChainsActive(chains: string[]): Promise<boolean> {
    if (!this.isReady() || !this.queryAPI) {
      return false;
    }

    let startTime = 0;
    if (this.monitoringService) {
      startTime = this.monitoringService.startRequest();
    }

    try {
      const axelarChains = chains
        .map(chain => this.getAxelarChainName(chain))
        .filter((name): name is string => name !== null);

      if (axelarChains.length !== chains.length) {
        if (this.monitoringService) {
          this.monitoringService.completeRequest(startTime, true);
        }
        return false; // Some chains are not supported
      }

      // Check if all chains are active with retry logic
      const activeChecks = await Promise.all(
        axelarChains.map(chain => 
          retry(
            () => this.queryAPI!.isChainActive(chain),
            { maxRetries: 2, delay: 500 }
          )
        )
      );
      
      if (this.monitoringService) {
        this.monitoringService.completeRequest(startTime);
      }

      return activeChecks.every(isActive => isActive);
    } catch (error) {
      if (this.monitoringService) {
        this.monitoringService.completeRequest(startTime, true);
      }
      
      logger.error('Error checking chain activity:', error);
      return false;
    }
  }

  /**
   * Execute batch transfers
   */
  async executeBatchTransfer(
    params: BatchTransferParams,
    provider: ethers.providers.Web3Provider
  ): Promise<string[]> {
    if (!this.isReady() || !this.transactionManager) {
      throw new AxelarServiceError('Axelar service not initialized');
    }

    let startTime = 0;
    if (this.monitoringService) {
      startTime = this.monitoringService.startRequest();
    }

    try {
      const fromAxelarChain = this.getAxelarChainName(params.fromChain);
      const toAxelarChain = this.getAxelarChainName(params.toChain);

      if (!fromAxelarChain || !toAxelarChain) {
        throw new AxelarServiceError(`Unsupported chain: ${params.fromChain} -> ${params.toChain}`);
      }

      // Execute batch transfer using transaction manager
      const txHashes = await this.transactionManager.executeBatchTransfer(
        {
          ...params,
          fromChain: fromAxelarChain,
          toChain: toAxelarChain
        },
        provider
      );
      
      if (this.monitoringService) {
        this.monitoringService.completeRequest(startTime);
      }

      return txHashes;
    } catch (error) {
      if (this.monitoringService) {
        this.monitoringService.completeRequest(startTime, true);
      }
      
      logger.error('Error executing batch transfer:', error);
      throw new AxelarServiceError('Failed to execute batch transfer', { cause: error as Error });
    }
  }

  /**
   * Get cross-chain portfolio balances
   */
  async getPortfolioBalances(params: PortfolioBalanceParams): Promise<CrossChainPortfolio> {
    if (!this.isReady() || !this.portfolioManager) {
      throw new AxelarServiceError('Axelar service not initialized');
    }

    let startTime = 0;
    let isCacheHit = false;
    
    if (this.monitoringService) {
      startTime = this.monitoringService.startRequest();
    }

    try {
      // Convert chain identifiers to Axelar chain names
      const axelarChains = params.chains
        .map(chain => this.getAxelarChainName(chain) || chain);
      
      // Get portfolio balances using portfolio manager
      const portfolio = await this.portfolioManager.getPortfolioBalances({
        ...params,
        chains: axelarChains
      });
      
      if (this.monitoringService) {
        this.monitoringService.completeRequest(startTime, false, isCacheHit);
      }

      return portfolio;
    } catch (error) {
      if (this.monitoringService) {
        this.monitoringService.completeRequest(startTime, true, isCacheHit);
      }
      
      logger.error('Error getting portfolio balances:', error);
      throw new AxelarServiceError('Failed to get portfolio balances', { cause: error as Error });
    }
  }

  /**
   * Optimize portfolio allocation across chains
   */
  async optimizePortfolioAllocation(
    currentPortfolio: CrossChainPortfolio,
    targetAllocation: { chain: string; percentage: number }[]
  ): Promise<{ moves: { fromChain: string; toChain: string; asset: string; amount: string }[] }> {
    if (!this.isReady() || !this.portfolioManager) {
      throw new AxelarServiceError('Axelar service not initialized');
    }

    let startTime = 0;
    if (this.monitoringService) {
      startTime = this.monitoringService.startRequest();
    }

    try {
      // Optimize portfolio using portfolio manager
      const optimization = await this.portfolioManager.optimizePortfolioAllocation(
        currentPortfolio,
        targetAllocation
      );
      
      if (this.monitoringService) {
        this.monitoringService.completeRequest(startTime);
      }

      return optimization;
    } catch (error) {
      if (this.monitoringService) {
        this.monitoringService.completeRequest(startTime, true);
      }
      
      logger.error('Error optimizing portfolio allocation:', error);
      throw new AxelarServiceError('Failed to optimize portfolio allocation', { cause: error as Error });
    }
  }

  /**
   * Get all tracked transactions
   */
  getAllTransactions(): TransactionDetailsV2[] {
    if (!this.isReady() || !this.transactionManager) {
      return [];
    }

    return this.transactionManager.getAllTransactions();
  }

  /**
   * Get transaction details by hash
   */
  getTransaction(txHash: string): TransactionDetailsV2 | undefined {
    if (!this.isReady() || !this.transactionManager) {
      return undefined;
    }

    return this.transactionManager.getTransaction(txHash);
  }

  /**
   * Get performance metrics
   */
  getPerformanceMetrics(): PerformanceMetrics | null {
    if (!this.monitoringService) {
      return null;
    }

    return this.monitoringService.getMetrics();
  }
}

// Export singleton instance
export const axelarServiceV2 = new AxelarServiceV2({
  environment: process.env.NODE_ENV === 'production' ? Environment.MAINNET : Environment.TESTNET,
  enableMonitoring: true,
  recoveryEnabled: true,
  cacheTimeout: 30000, // 30 seconds
  maxRetries: 3,
  retryDelay: 1000
});

export default AxelarServiceV2;

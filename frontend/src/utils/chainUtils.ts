import { CHAIN_CONFIG, type SupportedChainId } from '../constants/chains';

// Re-export CHAIN_CONFIG for components that need it
export { CHAIN_CONFIG };

/**
 * Utility functions for chain operations
 */
export class ChainUtils {
  /**
   * Get chain configuration by ID
   */
  static getChainConfig(chainId: number) {
    return CHAIN_CONFIG[chainId as SupportedChainId] || null;
  }

  /**
   * Get chain name by ID
   */
  static getChainName(chainId: number): string {
    const config = this.getChainConfig(chainId);
    return config?.name || `Chain ${chainId}`;
  }

  /**
   * Get Axelar chain name by chain ID
   */
  static getAxelarChainName(chainId: number): string | null {
    const config = this.getChainConfig(chainId);
    return config?.axelarName || null;
  }

  /**
   * Get block explorer URL by chain ID
   */
  static getExplorerUrl(chainId: number, txHash?: string): string {
    const config = this.getChainConfig(chainId);
    if (!config) return '';
    
    return txHash ? `${config.explorer}${txHash}` : config.explorer;
  }

  /**
   * Check if chain is supported by Axelar
   */
  static isAxelarSupported(chainId: number): boolean {
    const config = this.getChainConfig(chainId);
    return config?.axelarName != null;
  }

  /**
   * Normalize chain name for consistent comparison
   */
  static normalizeChainName(chainName: string): string {
    const normalized = chainName.toLowerCase();
    const mapping: { [key: string]: string } = {
      'eth': 'Ethereum',
      'ethereum': 'Ethereum', 
      'matic': 'Polygon',
      'polygon': 'Polygon',
      'avax': 'Avalanche',
      'avalanche': 'Avalanche',
      'arb': 'Arbitrum',
      'arbitrum': 'Arbitrum',
      'op': 'optimism',
      'optimism': 'optimism',
      'bsc': 'binance',
      'bnb': 'binance',
      'binance': 'binance',
      'base': 'base'
    };
    
    return mapping[normalized] || chainName;
  }

  /**
   * Get supported chain IDs
   */
  static getSupportedChainIds(): number[] {
    return Object.keys(CHAIN_CONFIG).map(Number);
  }

  /**
   * Check if chain ID is supported
   */
  static isChainSupported(chainId: number): boolean {
    return chainId in CHAIN_CONFIG;
  }
}

// Export individual functions for backward compatibility
export const getChainName = ChainUtils.getChainName.bind(ChainUtils);
export const getAxelarChainName = ChainUtils.getAxelarChainName.bind(ChainUtils);
export const getExplorerUrl = ChainUtils.getExplorerUrl.bind(ChainUtils);
export const isAxelarSupported = ChainUtils.isAxelarSupported.bind(ChainUtils);
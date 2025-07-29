import { ethers } from 'ethers';
import { ApiService } from './apiService';
import { ChainId } from '../constants/chains';
import { POPULAR_TOKENS, Token } from '../constants/tokens';
import { memoize } from '../utils/memoize';

// Standard ERC20 ABI for token interactions
const ERC20_ABI = [
  'function name() view returns (string)',
  'function symbol() view returns (string)',
  'function decimals() view returns (uint8)',
  'function totalSupply() view returns (uint256)',
  'function balanceOf(address owner) view returns (uint256)',
  'function allowance(address owner, address spender) view returns (uint256)',
];

// Token price data interface
export interface TokenPrice {
  symbol: string;
  price: number;
  priceChange24h?: number;
  priceChange7d?: number;
  volume24h?: number;
  marketCap?: number;
  lastUpdated: Date;
}

// Token balance interface
export interface TokenBalance {
  token: Token;
  balance: string;
  balanceRaw: ethers.BigNumber;
  balanceUsd?: string;
  value?: string;
  price?: number;
}

// Token details interface
export interface TokenDetails extends Token {
  price?: number;
  priceChange24h?: number;
  volume24h?: number;
  marketCap?: number;
  description?: string;
  website?: string;
  twitter?: string;
  telegram?: string;
  discord?: string;
  github?: string;
  tags?: string[];
}

/**
 * Service for working with tokens, including getting token prices,
 * balances, and other token-related data
 */
export class TokenService {
  private apiService: ApiService;
  private providers: Record<number, ethers.providers.Provider> = {};
  
  // Cache for token prices (symbol -> price data)
  private tokenPriceCache: Map<string, TokenPrice> = new Map();
  
  // Cache for token balances (address_chainId_symbol -> balance data)
  private tokenBalanceCache: Map<string, TokenBalance> = new Map();
  
  // Cache for token details (address_chainId -> details)
  private tokenDetailsCache: Map<string, TokenDetails> = new Map();
  
  // Cache expiry times (in milliseconds)
  private readonly PRICE_CACHE_TTL = 60 * 1000; // 1 minute
  private readonly BALANCE_CACHE_TTL = 30 * 1000; // 30 seconds
  private readonly DETAILS_CACHE_TTL = 3600 * 1000; // 1 hour
  
  constructor(apiService?: ApiService) {
    this.apiService = apiService || new ApiService();
    
    // Initialize providers for supported chains
    this.initializeProviders();
  }
  
  /**
   * Initialize providers for supported chains
   */
  private initializeProviders(): void {
    // Ethereum Mainnet
    this.providers[ChainId.ETHEREUM] = new ethers.providers.JsonRpcProvider(
      'https://eth-mainnet.g.alchemy.com/v2/demo'
    );
    
    // Polygon
    this.providers[ChainId.POLYGON] = new ethers.providers.JsonRpcProvider(
      'https://polygon-mainnet.g.alchemy.com/v2/demo'
    );
    
    // Arbitrum
    this.providers[ChainId.ARBITRUM] = new ethers.providers.JsonRpcProvider(
      'https://arb-mainnet.g.alchemy.com/v2/demo'
    );
    
    // Optimism
    this.providers[ChainId.OPTIMISM] = new ethers.providers.JsonRpcProvider(
      'https://opt-mainnet.g.alchemy.com/v2/demo'
    );
    
    // Base
    this.providers[ChainId.BASE] = new ethers.providers.JsonRpcProvider(
      'https://base-mainnet.g.alchemy.com/v2/demo'
    );
    
    // Avalanche
    this.providers[ChainId.AVALANCHE] = new ethers.providers.JsonRpcProvider(
      'https://api.avax.network/ext/bc/C/rpc'
    );
  }
  
  /**
   * Get provider for a specific chain
   */
  public getProvider(chainId: number): ethers.providers.Provider | undefined {
    return this.providers[chainId];
  }
  
  /**
   * Get token price from CoinGecko or other price API
   * Memoized to reduce API calls
   */
  public getTokenPrice = memoize(
    async (symbol: string): Promise<TokenPrice | null> => {
      try {
        // Check cache first
        const cachedPrice = this.tokenPriceCache.get(symbol.toUpperCase());
        if (cachedPrice && (new Date().getTime() - cachedPrice.lastUpdated.getTime()) < this.PRICE_CACHE_TTL) {
          return cachedPrice;
        }
        
        // Find token in our list to get coingeckoId
        const token = POPULAR_TOKENS.find(t => t.symbol.toUpperCase() === symbol.toUpperCase());
        if (!token || !token.coingeckoId) {
          console.warn(`No coingeckoId found for token ${symbol}`);
          return null;
        }
        
        // Fetch price data from API
        const response = await this.apiService.get(
          `https://api.coingecko.com/api/v3/coins/${token.coingeckoId}?localization=false&tickers=false&market_data=true&community_data=false&developer_data=false`
        );
        
        if (!response || !response.market_data) {
          console.warn(`No price data found for token ${symbol}`);
          return null;
        }
        
        // Create price data object
        const priceData: TokenPrice = {
          symbol: symbol.toUpperCase(),
          price: response.market_data.current_price.usd,
          priceChange24h: response.market_data.price_change_percentage_24h,
          priceChange7d: response.market_data.price_change_percentage_7d,
          volume24h: response.market_data.total_volume.usd,
          marketCap: response.market_data.market_cap.usd,
          lastUpdated: new Date()
        };
        
        // Update cache
        this.tokenPriceCache.set(symbol.toUpperCase(), priceData);
        
        return priceData;
      } catch (error) {
        console.error(`Error fetching price for ${symbol}:`, error);
        return null;
      }
    },
    { ttl: this.PRICE_CACHE_TTL, maxSize: 100 }
  );
  
  /**
   * Get token balance for an address
   */
  public async getTokenBalance(
    address: string,
    tokenAddress: string,
    chainId: number = ChainId.ETHEREUM
  ): Promise<TokenBalance | null> {
    try {
      // Generate cache key
      const cacheKey = `${address.toLowerCase()}_${chainId}_${tokenAddress.toLowerCase()}`;
      
      // Check cache first
      const cachedBalance = this.tokenBalanceCache.get(cacheKey);
      if (cachedBalance && (new Date().getTime() - new Date(cachedBalance.token.lastUpdated || 0).getTime()) < this.BALANCE_CACHE_TTL) {
        return cachedBalance;
      }
      
      // Get provider for chain
      const provider = this.getProvider(chainId);
      if (!provider) {
        console.warn(`No provider available for chain ID ${chainId}`);
        return null;
      }
      
      // Find token in our list
      const token = POPULAR_TOKENS.find(t => 
        t.address.toLowerCase() === tokenAddress.toLowerCase() && t.chainId === chainId
      );
      
      if (!token) {
        console.warn(`Token ${tokenAddress} not found in supported tokens list`);
        return null;
      }
      
      let balance: ethers.BigNumber;
      
      // Handle native token (ETH, MATIC, etc.)
      if (tokenAddress === '0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE') {
        balance = await provider.getBalance(address);
      } else {
        // Create contract instance for ERC20 token
        const tokenContract = new ethers.Contract(tokenAddress, ERC20_ABI, provider);
        balance = await tokenContract.balanceOf(address);
      }
      
      // Get token price
      const priceData = await this.getTokenPrice(token.symbol);
      
      // Calculate value in USD
      const balanceFormatted = ethers.utils.formatUnits(balance, token.decimals);
      const valueUsd = priceData ? parseFloat(balanceFormatted) * priceData.price : undefined;
      
      // Create balance object
      const balanceData: TokenBalance = {
        token: {
          ...token,
          lastUpdated: new Date()
        },
        balance: balanceFormatted,
        balanceRaw: balance,
        balanceUsd: valueUsd ? valueUsd.toFixed(2) : undefined,
        value: valueUsd ? valueUsd.toFixed(2) : undefined,
        price: priceData?.price
      };
      
      // Update cache
      this.tokenBalanceCache.set(cacheKey, balanceData);
      
      return balanceData;
    } catch (error) {
      console.error(`Error fetching balance for ${tokenAddress} on chain ${chainId}:`, error);
      return null;
    }
  }
  
  /**
   * Get all token balances for an address
   */
  public async getAllTokenBalances(
    address: string,
    chainId: number = ChainId.ETHEREUM
  ): Promise<TokenBalance[]> {
    try {
      // Get tokens for this chain
      const chainTokens = POPULAR_TOKENS.filter(token => token.chainId === chainId);
      
      // Fetch balances in parallel
      const balancePromises = chainTokens.map(token => 
        this.getTokenBalance(address, token.address, chainId)
      );
      
      const balances = await Promise.all(balancePromises);
      
      // Filter out null results and tokens with zero balance
      return balances.filter(
        balance => balance !== null && 
        balance.balanceRaw && 
        !balance.balanceRaw.isZero()
      ) as TokenBalance[];
    } catch (error) {
      console.error(`Error fetching all token balances for ${address} on chain ${chainId}:`, error);
      return [];
    }
  }
  
  /**
   * Get token details including price, social links, etc.
   */
  public async getTokenDetails(
    tokenAddressOrSymbol: string,
    chainId: number = ChainId.ETHEREUM
  ): Promise<TokenDetails | null> {
    try {
      // Generate cache key
      const cacheKey = `${tokenAddressOrSymbol.toLowerCase()}_${chainId}`;
      
      // Check cache first
      const cachedDetails = this.tokenDetailsCache.get(cacheKey);
      if (cachedDetails && (new Date().getTime() - new Date(cachedDetails.lastUpdated || 0).getTime()) < this.DETAILS_CACHE_TTL) {
        return cachedDetails;
      }
      
      // Find token in our list
      let token: Token | undefined;
      
      if (tokenAddressOrSymbol.startsWith('0x')) {
        // Look up by address
        token = POPULAR_TOKENS.find(t => 
          t.address.toLowerCase() === tokenAddressOrSymbol.toLowerCase() && 
          t.chainId === chainId
        );
      } else {
        // Look up by symbol
        token = POPULAR_TOKENS.find(t => 
          t.symbol.toLowerCase() === tokenAddressOrSymbol.toLowerCase() && 
          t.chainId === chainId
        );
      }
      
      if (!token) {
        console.warn(`Token ${tokenAddressOrSymbol} not found in supported tokens list`);
        return null;
      }
      
      // Get token price
      const priceData = await this.getTokenPrice(token.symbol);
      
      // Fetch additional details from API if available
      let additionalDetails: any = {};
      
      if (token.coingeckoId) {
        try {
          const response = await this.apiService.get(
            `https://api.coingecko.com/api/v3/coins/${token.coingeckoId}?localization=false&tickers=false&market_data=true&community_data=true&developer_data=true`
          );
          
          if (response) {
            additionalDetails = {
              description: response.description?.en,
              website: response.links?.homepage?.[0],
              twitter: response.links?.twitter_screen_name ? 
                `https://twitter.com/${response.links.twitter_screen_name}` : undefined,
              telegram: response.links?.telegram_channel_identifier ? 
                `https://t.me/${response.links.telegram_channel_identifier}` : undefined,
              discord: response.links?.chat_url?.find((url: string) => url.includes('discord')),
              github: response.links?.repos_url?.github?.[0],
              tags: response.categories?.slice(0, 5)
            };
          }
        } catch (error) {
          console.warn(`Error fetching additional details for ${token.symbol}:`, error);
          // Continue with basic details
        }
      }
      
      // Create details object
      const tokenDetails: TokenDetails = {
        ...token,
        price: priceData?.price,
        priceChange24h: priceData?.priceChange24h,
        volume24h: priceData?.volume24h,
        marketCap: priceData?.marketCap,
        lastUpdated: new Date(),
        ...additionalDetails
      };
      
      // Update cache
      this.tokenDetailsCache.set(cacheKey, tokenDetails);
      
      return tokenDetails;
    } catch (error) {
      console.error(`Error fetching details for ${tokenAddressOrSymbol} on chain ${chainId}:`, error);
      return null;
    }
  }
  
  /**
   * Search for tokens by name or symbol
   */
  public searchTokens(
    query: string,
    chainId?: number
  ): Token[] {
    if (!query || query.length < 2) {
      return [];
    }
    
    const normalizedQuery = query.toLowerCase();
    
    // Filter tokens based on query and optional chainId
    return POPULAR_TOKENS.filter(token => {
      const matchesQuery = 
        token.symbol.toLowerCase().includes(normalizedQuery) ||
        token.name.toLowerCase().includes(normalizedQuery);
        
      const matchesChain = chainId ? token.chainId === chainId : true;
      
      return matchesQuery && matchesChain;
    });
  }
  
  /**
   * Get popular tokens
   */
  public getPopularTokens(chainId?: number): Token[] {
    const tokens = POPULAR_TOKENS.filter(token => token.isPopular);
    
    if (chainId) {
      return tokens.filter(token => token.chainId === chainId);
    }
    
    return tokens;
  }
  
  /**
   * Get stablecoins
   */
  public getStablecoins(chainId?: number): Token[] {
    const tokens = POPULAR_TOKENS.filter(token => token.isStablecoin);
    
    if (chainId) {
      return tokens.filter(token => token.chainId === chainId);
    }
    
    return tokens;
  }
  
  /**
   * Validate if a token exists
   */
  public validateToken(symbol: string, chainId?: number): boolean {
    const normalizedSymbol = symbol.toUpperCase();
    
    if (chainId) {
      return POPULAR_TOKENS.some(
        token => token.symbol.toUpperCase() === normalizedSymbol && token.chainId === chainId
      );
    }
    
    return POPULAR_TOKENS.some(token => token.symbol.toUpperCase() === normalizedSymbol);
  }
  
  /**
   * Get token by symbol and chain
   */
  public getTokenBySymbol(symbol: string, chainId: number): Token | undefined {
    return POPULAR_TOKENS.find(
      token => token.symbol.toUpperCase() === symbol.toUpperCase() && token.chainId === chainId
    );
  }
  
  /**
   * Get token by address and chain
   */
  public getTokenByAddress(address: string, chainId: number): Token | undefined {
    return POPULAR_TOKENS.find(
      token => token.address.toLowerCase() === address.toLowerCase() && token.chainId === chainId
    );
  }
  
  /**
   * Clear caches
   */
  public clearCaches(): void {
    this.tokenPriceCache.clear();
    this.tokenBalanceCache.clear();
    this.tokenDetailsCache.clear();
  }
}

// Create singleton instance
export const tokenService = new TokenService();

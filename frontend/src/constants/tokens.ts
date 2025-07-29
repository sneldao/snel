import { ChainId } from './chains';

export interface Token {
  symbol: string;
  name: string;
  address: string;
  chainId: number;
  decimals: number;
  logoURI?: string;
  coingeckoId?: string;
  isPopular?: boolean;
  isStablecoin?: boolean;
}

/**
 * List of popular tokens across different chains
 * Used for auto-completion in the command input
 */
export const POPULAR_TOKENS: Token[] = [
  // Ethereum Mainnet Tokens
  {
    symbol: 'ETH',
    name: 'Ethereum',
    address: '0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE', // Native token representation
    chainId: ChainId.ETHEREUM,
    decimals: 18,
    logoURI: 'https://assets.coingecko.com/coins/images/279/small/ethereum.png',
    coingeckoId: 'ethereum',
    isPopular: true
  },
  {
    symbol: 'WETH',
    name: 'Wrapped Ethereum',
    address: '0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2',
    chainId: ChainId.ETHEREUM,
    decimals: 18,
    logoURI: 'https://assets.coingecko.com/coins/images/2518/small/weth.png',
    coingeckoId: 'weth',
    isPopular: true
  },
  {
    symbol: 'USDC',
    name: 'USD Coin',
    address: '0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48',
    chainId: ChainId.ETHEREUM,
    decimals: 6,
    logoURI: 'https://assets.coingecko.com/coins/images/6319/small/USD_Coin_icon.png',
    coingeckoId: 'usd-coin',
    isPopular: true,
    isStablecoin: true
  },
  {
    symbol: 'USDT',
    name: 'Tether',
    address: '0xdAC17F958D2ee523a2206206994597C13D831ec7',
    chainId: ChainId.ETHEREUM,
    decimals: 6,
    logoURI: 'https://assets.coingecko.com/coins/images/325/small/Tether.png',
    coingeckoId: 'tether',
    isPopular: true,
    isStablecoin: true
  },
  {
    symbol: 'DAI',
    name: 'Dai Stablecoin',
    address: '0x6B175474E89094C44Da98b954EedeAC495271d0F',
    chainId: ChainId.ETHEREUM,
    decimals: 18,
    logoURI: 'https://assets.coingecko.com/coins/images/9956/small/Badge_Dai.png',
    coingeckoId: 'dai',
    isPopular: true,
    isStablecoin: true
  },
  {
    symbol: 'WBTC',
    name: 'Wrapped Bitcoin',
    address: '0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599',
    chainId: ChainId.ETHEREUM,
    decimals: 8,
    logoURI: 'https://assets.coingecko.com/coins/images/7598/small/wrapped_bitcoin_wbtc.png',
    coingeckoId: 'wrapped-bitcoin',
    isPopular: true
  },
  {
    symbol: 'LINK',
    name: 'Chainlink',
    address: '0x514910771AF9Ca656af840dff83E8264EcF986CA',
    chainId: ChainId.ETHEREUM,
    decimals: 18,
    logoURI: 'https://assets.coingecko.com/coins/images/877/small/chainlink-new-logo.png',
    coingeckoId: 'chainlink',
    isPopular: true
  },
  {
    symbol: 'UNI',
    name: 'Uniswap',
    address: '0x1f9840a85d5aF5bf1D1762F925BDADdC4201F984',
    chainId: ChainId.ETHEREUM,
    decimals: 18,
    logoURI: 'https://assets.coingecko.com/coins/images/12504/small/uni.jpg',
    coingeckoId: 'uniswap',
    isPopular: true
  },
  {
    symbol: 'AAVE',
    name: 'Aave',
    address: '0x7Fc66500c84A76Ad7e9c93437bFc5Ac33E2DDaE9',
    chainId: ChainId.ETHEREUM,
    decimals: 18,
    logoURI: 'https://assets.coingecko.com/coins/images/12645/small/AAVE.png',
    coingeckoId: 'aave',
    isPopular: true
  },
  
  // Polygon Tokens
  {
    symbol: 'MATIC',
    name: 'Polygon',
    address: '0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE', // Native token representation
    chainId: ChainId.POLYGON,
    decimals: 18,
    logoURI: 'https://assets.coingecko.com/coins/images/4713/small/matic-token-icon.png',
    coingeckoId: 'matic-network',
    isPopular: true
  },
  {
    symbol: 'WMATIC',
    name: 'Wrapped Matic',
    address: '0x0d500B1d8E8eF31E21C99d1Db9A6444d3ADf1270',
    chainId: ChainId.POLYGON,
    decimals: 18,
    logoURI: 'https://assets.coingecko.com/coins/images/4713/small/matic-token-icon.png',
    coingeckoId: 'matic-network',
    isPopular: true
  },
  {
    symbol: 'USDC',
    name: 'USD Coin (Polygon)',
    address: '0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174',
    chainId: ChainId.POLYGON,
    decimals: 6,
    logoURI: 'https://assets.coingecko.com/coins/images/6319/small/USD_Coin_icon.png',
    coingeckoId: 'usd-coin',
    isPopular: true,
    isStablecoin: true
  },
  {
    symbol: 'USDT',
    name: 'Tether (Polygon)',
    address: '0xc2132D05D31c914a87C6611C10748AEb04B58e8F',
    chainId: ChainId.POLYGON,
    decimals: 6,
    logoURI: 'https://assets.coingecko.com/coins/images/325/small/Tether.png',
    coingeckoId: 'tether',
    isPopular: true,
    isStablecoin: true
  },
  {
    symbol: 'DAI',
    name: 'Dai Stablecoin (Polygon)',
    address: '0x8f3Cf7ad23Cd3CaDbD9735AFf958023239c6A063',
    chainId: ChainId.POLYGON,
    decimals: 18,
    logoURI: 'https://assets.coingecko.com/coins/images/9956/small/Badge_Dai.png',
    coingeckoId: 'dai',
    isPopular: true,
    isStablecoin: true
  },
  
  // Arbitrum Tokens
  {
    symbol: 'ETH',
    name: 'Ethereum (Arbitrum)',
    address: '0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE', // Native token representation
    chainId: ChainId.ARBITRUM,
    decimals: 18,
    logoURI: 'https://assets.coingecko.com/coins/images/279/small/ethereum.png',
    coingeckoId: 'ethereum',
    isPopular: true
  },
  {
    symbol: 'WETH',
    name: 'Wrapped Ethereum (Arbitrum)',
    address: '0x82aF49447D8a07e3bd95BD0d56f35241523fBab1',
    chainId: ChainId.ARBITRUM,
    decimals: 18,
    logoURI: 'https://assets.coingecko.com/coins/images/2518/small/weth.png',
    coingeckoId: 'weth',
    isPopular: true
  },
  {
    symbol: 'USDC',
    name: 'USD Coin (Arbitrum)',
    address: '0xFF970A61A04b1cA14834A43f5dE4533eBDDB5CC8',
    chainId: ChainId.ARBITRUM,
    decimals: 6,
    logoURI: 'https://assets.coingecko.com/coins/images/6319/small/USD_Coin_icon.png',
    coingeckoId: 'usd-coin',
    isPopular: true,
    isStablecoin: true
  },
  {
    symbol: 'ARB',
    name: 'Arbitrum',
    address: '0x912CE59144191C1204E64559FE8253a0e49E6548',
    chainId: ChainId.ARBITRUM,
    decimals: 18,
    logoURI: 'https://assets.coingecko.com/coins/images/16547/small/arbitrum.png',
    coingeckoId: 'arbitrum',
    isPopular: true
  },
  
  // Optimism Tokens
  {
    symbol: 'ETH',
    name: 'Ethereum (Optimism)',
    address: '0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE', // Native token representation
    chainId: ChainId.OPTIMISM,
    decimals: 18,
    logoURI: 'https://assets.coingecko.com/coins/images/279/small/ethereum.png',
    coingeckoId: 'ethereum',
    isPopular: true
  },
  {
    symbol: 'WETH',
    name: 'Wrapped Ethereum (Optimism)',
    address: '0x4200000000000000000000000000000000000006',
    chainId: ChainId.OPTIMISM,
    decimals: 18,
    logoURI: 'https://assets.coingecko.com/coins/images/2518/small/weth.png',
    coingeckoId: 'weth',
    isPopular: true
  },
  {
    symbol: 'USDC',
    name: 'USD Coin (Optimism)',
    address: '0x7F5c764cBc14f9669B88837ca1490cCa17c31607',
    chainId: ChainId.OPTIMISM,
    decimals: 6,
    logoURI: 'https://assets.coingecko.com/coins/images/6319/small/USD_Coin_icon.png',
    coingeckoId: 'usd-coin',
    isPopular: true,
    isStablecoin: true
  },
  {
    symbol: 'OP',
    name: 'Optimism',
    address: '0x4200000000000000000000000000000000000042',
    chainId: ChainId.OPTIMISM,
    decimals: 18,
    logoURI: 'https://assets.coingecko.com/coins/images/25244/small/Optimism.png',
    coingeckoId: 'optimism',
    isPopular: true
  },
  
  // Avalanche Tokens
  {
    symbol: 'AVAX',
    name: 'Avalanche',
    address: '0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE', // Native token representation
    chainId: ChainId.AVALANCHE,
    decimals: 18,
    logoURI: 'https://assets.coingecko.com/coins/images/12559/small/Avalanche_Circle_RedWhite_Trans.png',
    coingeckoId: 'avalanche-2',
    isPopular: true
  },
  {
    symbol: 'WAVAX',
    name: 'Wrapped AVAX',
    address: '0xB31f66AA3C1e785363F0875A1B74E27b85FD66c7',
    chainId: ChainId.AVALANCHE,
    decimals: 18,
    logoURI: 'https://assets.coingecko.com/coins/images/12559/small/Avalanche_Circle_RedWhite_Trans.png',
    coingeckoId: 'avalanche-2',
    isPopular: true
  },
  {
    symbol: 'USDC',
    name: 'USD Coin (Avalanche)',
    address: '0xB97EF9Ef8734C71904D8002F8b6Bc66Dd9c48a6E',
    chainId: ChainId.AVALANCHE,
    decimals: 6,
    logoURI: 'https://assets.coingecko.com/coins/images/6319/small/USD_Coin_icon.png',
    coingeckoId: 'usd-coin',
    isPopular: true,
    isStablecoin: true
  },
  
  // Base Tokens
  {
    symbol: 'ETH',
    name: 'Ethereum (Base)',
    address: '0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE', // Native token representation
    chainId: ChainId.BASE,
    decimals: 18,
    logoURI: 'https://assets.coingecko.com/coins/images/279/small/ethereum.png',
    coingeckoId: 'ethereum',
    isPopular: true
  },
  {
    symbol: 'USDC',
    name: 'USD Coin (Base)',
    address: '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913',
    chainId: ChainId.BASE,
    decimals: 6,
    logoURI: 'https://assets.coingecko.com/coins/images/6319/small/USD_Coin_icon.png',
    coingeckoId: 'usd-coin',
    isPopular: true,
    isStablecoin: true
  },
  
  // Additional Popular DeFi Tokens (Ethereum)
  {
    symbol: 'SNX',
    name: 'Synthetix',
    address: '0xC011a73ee8576Fb46F5E1c5751cA3B9Fe0af2a6F',
    chainId: ChainId.ETHEREUM,
    decimals: 18,
    logoURI: 'https://assets.coingecko.com/coins/images/3406/small/SNX.png',
    coingeckoId: 'havven',
    isPopular: true
  },
  {
    symbol: 'CRV',
    name: 'Curve DAO Token',
    address: '0xD533a949740bb3306d119CC777fa900bA034cd52',
    chainId: ChainId.ETHEREUM,
    decimals: 18,
    logoURI: 'https://assets.coingecko.com/coins/images/12124/small/Curve.png',
    coingeckoId: 'curve-dao-token',
    isPopular: true
  },
  {
    symbol: 'COMP',
    name: 'Compound',
    address: '0xc00e94Cb662C3520282E6f5717214004A7f26888',
    chainId: ChainId.ETHEREUM,
    decimals: 18,
    logoURI: 'https://assets.coingecko.com/coins/images/10775/small/COMP.png',
    coingeckoId: 'compound-governance-token',
    isPopular: true
  },
  {
    symbol: 'MKR',
    name: 'Maker',
    address: '0x9f8F72aA9304c8B593d555F12eF6589cC3A579A2',
    chainId: ChainId.ETHEREUM,
    decimals: 18,
    logoURI: 'https://assets.coingecko.com/coins/images/1364/small/Mark_Maker.png',
    coingeckoId: 'maker',
    isPopular: true
  },
  {
    symbol: 'SUSHI',
    name: 'SushiSwap',
    address: '0x6B3595068778DD592e39A122f4f5a5cF09C90fE2',
    chainId: ChainId.ETHEREUM,
    decimals: 18,
    logoURI: 'https://assets.coingecko.com/coins/images/12271/small/sushi.png',
    coingeckoId: 'sushi',
    isPopular: true
  },
  {
    symbol: 'YFI',
    name: 'yearn.finance',
    address: '0x0bc529c00C6401aEF6D220BE8C6Ea1667F6Ad93e',
    chainId: ChainId.ETHEREUM,
    decimals: 18,
    logoURI: 'https://assets.coingecko.com/coins/images/11849/small/yfi-192x192.png',
    coingeckoId: 'yearn-finance',
    isPopular: true
  },
  {
    symbol: 'BAL',
    name: 'Balancer',
    address: '0xba100000625a3754423978a60c9317c58a424e3D',
    chainId: ChainId.ETHEREUM,
    decimals: 18,
    logoURI: 'https://assets.coingecko.com/coins/images/11683/small/Balancer.png',
    coingeckoId: 'balancer',
    isPopular: true
  }
];

// Helper function to get tokens by chain
export const getTokensByChain = (chainId: number): Token[] => {
  return POPULAR_TOKENS.filter(token => token.chainId === chainId);
};

// Helper function to get token by symbol and chain
export const getTokenBySymbol = (symbol: string, chainId: number): Token | undefined => {
  return POPULAR_TOKENS.find(
    token => token.symbol.toLowerCase() === symbol.toLowerCase() && token.chainId === chainId
  );
};

// Helper function to get token by address
export const getTokenByAddress = (address: string, chainId: number): Token | undefined => {
  return POPULAR_TOKENS.find(
    token => token.address.toLowerCase() === address.toLowerCase() && token.chainId === chainId
  );
};

// Get all stablecoins
export const getStablecoins = (): Token[] => {
  return POPULAR_TOKENS.filter(token => token.isStablecoin);
};

// Get all popular tokens
export const getPopularTokens = (): Token[] => {
  return POPULAR_TOKENS.filter(token => token.isPopular);
};

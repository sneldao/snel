/* NOTE:
 *  This file must stay framework-agnostic.  No React, JSX, or component
 *  imports should exist here – only plain data structures.
 */

export interface CommandTemplate {
  name: string;
  template: string;
  description: string;
  /* Icon is kept as a string identifier so the UI layer can decide
   * how to render it (e.g., mapping to an actual icon component).
   */
  icon: string;
  category: string;
  examples?: string[];
  popularity?: number; // 1-10 scale, 10 being most popular
  isAdvanced?: boolean;
}

/**
 * List of command templates for the command input
 * Used for auto-completion and suggestions
 */
export const COMMAND_TEMPLATES: CommandTemplate[] = [
  // Swap Commands
  {
    name: 'Basic Swap',
    template: 'swap 0.1 ETH for USDC',
    description: 'Swap one token for another',
    icon: 'exchange-alt',
    category: 'swap',
    examples: ['swap 1 ETH for DAI', 'swap 100 USDC for WBTC'],
    popularity: 10
  },
  {
    name: 'Swap with Slippage',
    template: 'swap 0.1 ETH for USDC with 0.5% slippage',
    description: 'Swap with custom slippage tolerance',
    icon: 'exchange-alt',
    category: 'swap',
    examples: ['swap 1 ETH for DAI with 1% slippage'],
    popularity: 8,
    isAdvanced: true
  },
  {
    name: 'Swap with Min Amount',
    template: 'swap 0.1 ETH for at least 100 USDC',
    description: 'Swap with minimum output amount',
    icon: 'exchange-alt',
    category: 'swap',
    examples: ['swap 1 ETH for at least 1500 DAI'],
    popularity: 7,
    isAdvanced: true
  },
  {
    name: 'Swap on Specific DEX',
    template: 'swap 0.1 ETH for USDC on uniswap',
    description: 'Swap using a specific exchange',
    icon: 'exchange-alt',
    category: 'swap',
    examples: ['swap 100 USDC for DAI on curve', 'swap 0.5 ETH for WBTC on sushiswap'],
    popularity: 6,
    isAdvanced: true
  },
  {
    name: 'Swap All Balance',
    template: 'swap all my ETH for USDC',
    description: 'Swap entire token balance',
    icon: 'exchange-alt',
    category: 'swap',
    examples: ['swap all my LINK for ETH', 'swap all my USDC for DAI'],
    popularity: 8
  },
  {
    name: 'Swap Percentage',
    template: 'swap 50% of my ETH for USDC',
    description: 'Swap percentage of token balance',
    icon: 'exchange-alt',
    category: 'swap',
    examples: ['swap 25% of my LINK for ETH', 'swap 75% of my USDC for DAI'],
    popularity: 7
  },
  
  // Bridge Commands
  {
    name: 'Basic Bridge',
    template: 'bridge 100 USDC from Ethereum to Polygon',
    description: 'Bridge tokens between chains',
    icon: 'link',
    category: 'bridge',
    examples: ['bridge 1 ETH from Ethereum to Arbitrum', 'bridge 50 USDC from Polygon to Optimism'],
    popularity: 9
  },
  {
    name: 'Bridge with Gas Token',
    template: 'bridge 100 USDC from Ethereum to Polygon with 0.01 ETH for gas',
    description: 'Bridge tokens with gas for destination chain',
    icon: 'link',
    category: 'bridge',
    examples: ['bridge 1 ETH from Ethereum to Arbitrum with 0.005 ETH for gas'],
    popularity: 7,
    isAdvanced: true
  },
  {
    name: 'Bridge All Balance',
    template: 'bridge all my USDC from Ethereum to Polygon',
    description: 'Bridge entire token balance',
    icon: 'link',
    category: 'bridge',
    examples: ['bridge all my ETH from Ethereum to Arbitrum', 'bridge all my USDC from Polygon to Optimism'],
    popularity: 8
  },
  {
    name: 'Bridge to Address',
    template: 'bridge 100 USDC from Ethereum to Polygon to 0x1234...5678',
    description: 'Bridge tokens to a specific address',
    icon: 'link',
    category: 'bridge',
    examples: ['bridge 1 ETH from Ethereum to Arbitrum to vitalik.eth'],
    popularity: 6,
    isAdvanced: true
  },
  {
    name: 'Fast Bridge',
    template: 'fast bridge 100 USDC from Ethereum to Polygon',
    description: 'Bridge tokens using fastest route',
    icon: 'rocket',
    category: 'bridge',
    examples: ['fast bridge 1 ETH from Ethereum to Arbitrum', 'fast bridge 50 USDC from Polygon to Optimism'],
    popularity: 8
  },
  
  // Send/Transfer Commands
  {
    name: 'Basic Send',
    template: 'send 0.1 ETH to vitalik.eth',
    description: 'Send tokens to an address',
    icon: 'arrow-right',
    category: 'transfer',
    examples: ['send 100 USDC to 0x1234...5678', 'send 0.5 ETH to friend.eth'],
    popularity: 9
  },
  {
    name: 'Send with Message',
    template: 'send 0.1 ETH to vitalik.eth with message "Thanks for Ethereum!"',
    description: 'Send tokens with an attached message',
    icon: 'arrow-right',
    category: 'transfer',
    examples: ['send 100 USDC to 0x1234...5678 with message "Reimbursement"'],
    popularity: 7,
    isAdvanced: true
  },
  {
    name: 'Send All Balance',
    template: 'send all my ETH to vitalik.eth',
    description: 'Send entire token balance',
    icon: 'arrow-right',
    category: 'transfer',
    examples: ['send all my USDC to 0x1234...5678', 'send all my ETH to friend.eth'],
    popularity: 8
  },
  {
    name: 'Cross-chain Send',
    template: 'send 100 USDC to vitalik.eth on Polygon',
    description: 'Send tokens to an address on another chain',
    icon: 'arrow-right',
    category: 'transfer',
    examples: ['send 0.5 ETH to 0x1234...5678 on Arbitrum'],
    popularity: 7,
    isAdvanced: true
  },
  {
    name: 'Schedule Send',
    template: 'schedule send 0.1 ETH to vitalik.eth in 7 days',
    description: 'Schedule a future token transfer',
    icon: 'arrow-right',
    category: 'transfer',
    examples: ['schedule send 100 USDC to 0x1234...5678 in 30 days'],
    popularity: 5,
    isAdvanced: true
  },
  
  // Portfolio Analysis Commands
  {
    name: 'Portfolio Overview',
    template: 'analyze my portfolio',
    description: 'Get a complete portfolio analysis',
    icon: 'chart-pie',
    category: 'portfolio',
    examples: ['show my portfolio', 'portfolio analysis'],
    popularity: 10
  },
  {
    name: 'Portfolio History',
    template: 'show my portfolio history',
    description: 'View historical portfolio performance',
    icon: 'history',
    category: 'portfolio',
    examples: ['portfolio history', 'show my historical returns'],
    popularity: 8
  },
  {
    name: 'Portfolio on Chain',
    template: 'analyze my portfolio on Ethereum',
    description: 'Get portfolio analysis for specific chain',
    icon: 'chart-pie',
    category: 'portfolio',
    examples: ['show my Polygon portfolio', 'analyze my Arbitrum assets'],
    popularity: 7
  },
  {
    name: 'Portfolio Risk Analysis',
    template: 'analyze portfolio risk',
    description: 'Get risk assessment of your portfolio',
    icon: 'exclamation-triangle',
    category: 'portfolio',
    examples: ['portfolio risk assessment', 'check my portfolio volatility'],
    popularity: 6,
    isAdvanced: true
  },
  {
    name: 'Portfolio Yield',
    template: 'show my yield opportunities',
    description: 'Find yield opportunities for your assets',
    icon: 'percentage',
    category: 'portfolio',
    examples: ['yield opportunities', 'staking options for my portfolio'],
    popularity: 7
  },
  {
    name: 'Portfolio Diversification',
    template: 'suggest portfolio diversification',
    description: 'Get suggestions to diversify your portfolio',
    icon: 'layer-group',
    category: 'portfolio',
    examples: ['how to diversify my portfolio', 'portfolio allocation suggestions'],
    popularity: 6,
    isAdvanced: true
  },
  
  // Balance and Token Commands
  {
    name: 'Check Balance',
    template: 'check my balance',
    description: 'Check your token balances',
    icon: 'wallet',
    category: 'balance',
    examples: ['show my balances', 'what tokens do I have'],
    popularity: 9
  },
  {
    name: 'Check Specific Token',
    template: 'check my ETH balance',
    description: 'Check balance of specific token',
    icon: 'wallet',
    category: 'balance',
    examples: ['how much USDC do I have', 'check my WBTC balance'],
    popularity: 8
  },
  {
    name: 'Check Balance on Chain',
    template: 'check my balance on Polygon',
    description: 'Check balances on specific chain',
    icon: 'wallet',
    category: 'balance',
    examples: ['show my Arbitrum balances', 'check my Optimism tokens'],
    popularity: 7
  },
  {
    name: 'Check Gas Balance',
    template: 'check my gas balance',
    description: 'Check if you have enough gas tokens',
    icon: 'gas-pump',
    category: 'balance',
    examples: ['do I have enough gas', 'check ETH for gas'],
    popularity: 8
  },
  {
    name: 'Check Address Balance',
    template: 'check balance of vitalik.eth',
    description: 'Check token balances of any address',
    icon: 'wallet',
    category: 'balance',
    examples: ['show balances of 0x1234...5678', 'what tokens does snel.eth have'],
    popularity: 6
  },
  
  // Price and Market Commands
  {
    name: 'Check Token Price',
    template: 'check ETH price',
    description: 'Check current price of a token',
    icon: 'search',
    category: 'price',
    examples: ['what is USDC price', 'check BTC price'],
    popularity: 9
  },
  {
    name: 'Price Comparison',
    template: 'compare ETH and BTC prices',
    description: 'Compare prices of multiple tokens',
    icon: 'chart-line',
    category: 'price',
    examples: ['compare USDC and DAI', 'ETH vs BTC price'],
    popularity: 7
  },
  {
    name: 'Price History',
    template: 'show ETH price history',
    description: 'View historical price data',
    icon: 'history',
    category: 'price',
    examples: ['BTC price last 30 days', 'LINK price chart'],
    popularity: 8
  },
  {
    name: 'Price Alert',
    template: 'alert when ETH reaches 3000',
    description: 'Set price alert for a token',
    icon: 'exclamation-triangle',
    category: 'price',
    examples: ['notify when BTC drops below 25000', 'alert if LINK goes above 20'],
    popularity: 7,
    isAdvanced: true
  },
  {
    name: 'Market Overview',
    template: 'show market overview',
    description: 'Get overview of crypto market',
    icon: 'globe',
    category: 'price',
    examples: ['crypto market summary', 'top gainers and losers'],
    popularity: 8
  },
  {
    name: 'Token Info',
    template: 'tell me about ETH',
    description: 'Get information about a token',
    icon: 'info',
    category: 'price',
    examples: ['what is LINK', 'information about AAVE'],
    popularity: 8
  },
  
  // Gas and Network Commands
  {
    name: 'Check Gas Price',
    template: 'check gas price',
    description: 'Check current gas prices',
    icon: 'gas-pump',
    category: 'network',
    examples: ['current gas fees', 'Ethereum gas price'],
    popularity: 9
  },
  {
    name: 'Check Gas Price on Chain',
    template: 'check gas price on Polygon',
    description: 'Check gas prices on specific chain',
    icon: 'gas-pump',
    category: 'network',
    examples: ['Arbitrum gas fees', 'Optimism gas price'],
    popularity: 7
  },
  {
    name: 'Network Status',
    template: 'check network status',
    description: 'Check status of blockchain networks',
    icon: 'network-wired',
    category: 'network',
    examples: ['Ethereum network status', 'is Polygon congested'],
    popularity: 8
  },
  {
    name: 'Transaction Time Estimate',
    template: 'estimate transaction time',
    description: 'Estimate time for transaction confirmation',
    icon: 'history',
    category: 'network',
    examples: ['how long for transaction to confirm', 'ETH transfer time estimate'],
    popularity: 7
  },
  {
    name: 'Gas Saving Tips',
    template: 'gas saving tips',
    description: 'Get tips to save on gas fees',
    icon: 'lightbulb',
    category: 'network',
    examples: ['how to reduce gas costs', 'save on transaction fees'],
    popularity: 8
  },
  
  // Settings and Configuration Commands
  {
    name: 'Change Network',
    template: 'switch to Polygon',
    description: 'Switch to a different network',
    icon: 'network-wired',
    category: 'settings',
    examples: ['connect to Arbitrum', 'change to Ethereum mainnet'],
    popularity: 9
  },
  {
    name: 'Connect Wallet',
    template: 'connect wallet',
    description: 'Connect your wallet',
    icon: 'wallet',
    category: 'settings',
    examples: ['connect MetaMask', 'link wallet'],
    popularity: 10
  },
  {
    name: 'Disconnect Wallet',
    template: 'disconnect wallet',
    description: 'Disconnect your wallet',
    icon: 'unlock',
    category: 'settings',
    examples: ['logout', 'unlink wallet'],
    popularity: 8
  },
  {
    name: 'Set Default Slippage',
    template: 'set default slippage to 0.5%',
    description: 'Set default slippage tolerance',
    icon: 'cog',
    category: 'settings',
    examples: ['change slippage to 1%', 'update default slippage'],
    popularity: 6,
    isAdvanced: true
  },
  {
    name: 'Set Gas Price',
    template: 'set gas price to fast',
    description: 'Set gas price preference',
    icon: 'gas-pump',
    category: 'settings',
    examples: ['use average gas price', 'set max gas price'],
    popularity: 7,
    isAdvanced: true
  },
  {
    name: 'Change Theme',
    template: 'switch to dark mode',
    description: 'Change app theme',
    icon: 'cog',
    category: 'settings',
    examples: ['use light theme', 'toggle dark mode'],
    popularity: 8
  },
  
  // Help and Information Commands
  {
    name: 'Help',
    template: 'help',
    description: 'Show help information',
    icon: 'question',
    category: 'help',
    examples: ['show commands', 'what can I do'],
    popularity: 9
  },
  {
    name: 'Tutorial',
    template: 'show tutorial',
    description: 'Start interactive tutorial',
    icon: 'book',
    category: 'help',
    examples: ['how to use SNEL', 'beginner guide'],
    popularity: 8
  },
  {
    name: 'Command List',
    template: 'list all commands',
    description: 'Show all available commands',
    icon: 'list-alt',
    category: 'help',
    examples: ['show commands', 'command reference'],
    popularity: 8
  },
  {
    name: 'FAQ',
    template: 'show FAQ',
    description: 'Show frequently asked questions',
    icon: 'question',
    category: 'help',
    examples: ['frequently asked questions', 'common issues'],
    popularity: 7
  },
  {
    name: 'About',
    template: 'about SNEL',
    description: 'Show information about SNEL',
    icon: 'info',
    category: 'help',
    examples: ['what is SNEL', 'SNEL information'],
    popularity: 7
  },
  
  // Advanced DeFi Commands
  {
    name: 'Provide Liquidity',
    template: 'provide liquidity for ETH/USDC',
    description: 'Add liquidity to a pool',
    icon: 'hand-holding-usd',
    category: 'defi',
    examples: ['add liquidity to WBTC/ETH', 'provide ETH/DAI liquidity'],
    popularity: 6,
    isAdvanced: true
  },
  {
    name: 'Remove Liquidity',
    template: 'remove liquidity from ETH/USDC',
    description: 'Remove liquidity from a pool',
    icon: 'hand-holding-usd',
    category: 'defi',
    examples: ['withdraw from WBTC/ETH pool', 'remove ETH/DAI liquidity'],
    popularity: 6,
    isAdvanced: true
  },
  {
    name: 'Stake Tokens',
    template: 'stake 100 SNEL',
    description: 'Stake tokens for rewards',
    icon: 'lock',
    category: 'defi',
    examples: ['stake ETH', 'deposit 10 AAVE for staking'],
    popularity: 7,
    isAdvanced: true
  },
  {
    name: 'Unstake Tokens',
    template: 'unstake 100 SNEL',
    description: 'Unstake tokens',
    icon: 'unlock',
    category: 'defi',
    examples: ['withdraw staked ETH', 'unstake all my AAVE'],
    popularity: 7,
    isAdvanced: true
  },
  {
    name: 'Claim Rewards',
    template: 'claim rewards',
    description: 'Claim staking or protocol rewards',
    icon: 'coins',
    category: 'defi',
    examples: ['harvest yield', 'collect staking rewards'],
    popularity: 8,
    isAdvanced: true
  },
  {
    name: 'Borrow',
    template: 'borrow 1000 USDC against ETH',
    description: 'Borrow tokens using collateral',
    icon: 'arrow-down',
    category: 'defi',
    examples: ['take loan of 5000 DAI using WBTC', 'borrow USDT with ETH collateral'],
    popularity: 6,
    isAdvanced: true
  },
  {
    name: 'Repay Loan',
    template: 'repay 1000 USDC loan',
    description: 'Repay borrowed tokens',
    icon: 'arrow-up',
    category: 'defi',
    examples: ['repay DAI debt', 'return borrowed USDT'],
    popularity: 6,
    isAdvanced: true
  },
  {
    name: 'Check Loan Health',
    template: 'check loan health',
    description: 'Check health of your loans',
    icon: 'heartbeat',
    category: 'defi',
    examples: ['loan health factor', 'check liquidation risk'],
    popularity: 7,
    isAdvanced: true
  },
  
  // Social and Community Commands
  {
    name: 'Join Community',
    template: 'join SNEL community',
    description: 'Join the SNEL community',
    icon: 'user-friends',
    category: 'community',
    examples: ['SNEL discord', 'community channels'],
    popularity: 7
  },
  {
    name: 'Share Portfolio',
    template: 'share my portfolio',
    description: 'Generate shareable portfolio link',
    icon: 'external-link-alt',
    category: 'community',
    examples: ['create portfolio link', 'export portfolio'],
    popularity: 6,
    isAdvanced: true
  },
  {
    name: 'Follow Address',
    template: 'follow vitalik.eth',
    description: 'Follow an address for updates',
    icon: 'user-check',
    category: 'community',
    examples: ['track 0x1234...5678', 'monitor address activity'],
    popularity: 6,
    isAdvanced: true
  },
  
  // Tools and Utilities
  {
    name: 'Calculate',
    template: 'calculate 100 USDC to ETH',
    description: 'Convert between token amounts',
    icon: 'calculator',
    category: 'tools',
    examples: ['convert 5 ETH to USDC', 'how much is 1000 DAI in BTC'],
    popularity: 8
  },
  {
    name: 'Generate New Wallet',
    template: 'generate new wallet',
    description: 'Create a new wallet',
    icon: 'wallet',
    category: 'tools',
    examples: ['create wallet', 'new address'],
    popularity: 6,
    isAdvanced: true
  },
  {
    name: 'Verify Contract',
    template: 'verify contract 0x1234...5678',
    description: 'Verify a smart contract',
    icon: 'shield-alt',
    category: 'tools',
    examples: ['check if contract is verified', 'contract security check'],
    popularity: 5,
    isAdvanced: true
  },
  {
    name: 'Decode Transaction',
    template: 'decode transaction 0x1234...5678',
    description: 'Decode a transaction',
    icon: 'code',
    category: 'tools',
    examples: ['explain transaction', 'what does this transaction do'],
    popularity: 5,
    isAdvanced: true
  },
  {
    name: 'Find Best Route',
    template: 'find best route to swap ETH to USDC',
    description: 'Find optimal trading route',
    icon: 'compass',
    category: 'tools',
    examples: ['best way to swap WBTC to DAI', 'optimal route for ETH to LINK'],
    popularity: 7,
    isAdvanced: true
  },
  {
    name: 'Gas Refund',
    template: 'request gas refund',
    description: 'Request gas fee refund',
    icon: 'gas-pump',
    category: 'tools',
    examples: ['claim gas refund', 'gas cashback'],
    popularity: 6
  },
  
  // SNEL-specific Commands
  {
    name: 'SNEL Stats',
    template: 'show SNEL stats',
    description: 'Show SNEL protocol statistics',
    icon: 'chart-bar',
    category: 'snel',
    examples: ['SNEL protocol stats', 'SNEL usage metrics'],
    popularity: 7
  },
  {
    name: 'SNEL Rewards',
    template: 'check my SNEL rewards',
    description: 'Check your SNEL rewards',
    icon: 'coins',
    category: 'snel',
    examples: ['my SNEL points', 'SNEL earnings'],
    popularity: 8
  },
  {
    name: 'SNEL Governance',
    template: 'view SNEL governance proposals',
    description: 'View SNEL governance',
    icon: 'users',
    category: 'snel',
    examples: ['SNEL voting', 'governance dashboard'],
    popularity: 6,
    isAdvanced: true
  },
  {
    name: 'SNEL Feedback',
    template: 'provide feedback',
    description: 'Submit feedback about SNEL',
    icon: 'lightbulb',
    category: 'snel',
    examples: ['suggest feature', 'report issue'],
    popularity: 7
  }
];

// Helper functions

/**
 * Get templates by category
 */
export const getTemplatesByCategory = (category: string): CommandTemplate[] => {
  return COMMAND_TEMPLATES.filter(template => template.category === category);
};

/**
 * Get popular templates (popularity >= 8)
 */
export const getPopularTemplates = (): CommandTemplate[] => {
  return COMMAND_TEMPLATES.filter(template => (template.popularity || 0) >= 8);
};

/**
 * Get beginner templates (not marked as advanced)
 */
export const getBeginnerTemplates = (): CommandTemplate[] => {
  return COMMAND_TEMPLATES.filter(template => !template.isAdvanced);
};

/**
 * Get advanced templates
 */
export const getAdvancedTemplates = (): CommandTemplate[] => {
  return COMMAND_TEMPLATES.filter(template => template.isAdvanced);
};

/**
 * Search templates by keywords
 */
export const searchTemplates = (query: string): CommandTemplate[] => {
  const lowerQuery = query.toLowerCase();
  return COMMAND_TEMPLATES.filter(template => 
    template.name.toLowerCase().includes(lowerQuery) ||
    template.template.toLowerCase().includes(lowerQuery) ||
    template.description.toLowerCase().includes(lowerQuery) ||
    template.category.toLowerCase().includes(lowerQuery) ||
    template.examples?.some(example => example.toLowerCase().includes(lowerQuery))
  );
};

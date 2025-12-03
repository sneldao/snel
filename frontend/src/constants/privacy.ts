/**
 * Privacy and Zcash Integration Constants
 * Single source of truth for all privacy-related information
 */

/**
 * Zcash Wallet Recommendations
 * Ordered by recommendation level (shielded-by-default first)
 */
export const ZCASH_WALLETS = [
  {
    id: 'zashi',
    name: 'Zashi',
    type: 'mobile',
    shieldedByDefault: true,
    url: 'https://zashi.app/',
    description: 'Official Zcash mobile wallet. Shielded by default, built by Electric Coin Co.',
    platforms: ['iOS', 'Android'] as const,
    badge: 'Recommended' as const,
  },
  {
    id: 'nighthawk',
    name: 'Nighthawk',
    type: 'desktop',
    shieldedByDefault: true,
    url: 'https://nighthawkwallet.com/',
    description: 'Open-source desktop wallet with full privacy support. Shielded by default.',
    platforms: ['Windows', 'macOS', 'Linux'] as const,
    badge: 'Recommended' as const,
  },
  {
    id: 'ywallet',
    name: 'YWallet',
    type: 'mobile',
    shieldedByDefault: true,
    url: 'https://ywallet.app/',
    description: 'Community-built mobile wallet for Zcash',
    platforms: ['iOS', 'Android'] as const,
    badge: undefined as undefined,
  },
  {
    id: 'edge',
    name: 'Edge Wallet',
    type: 'mobile',
    shieldedByDefault: false,
    url: 'https://edge.app/',
    description: 'Multi-asset wallet with Zcash support',
    platforms: ['iOS', 'Android'] as const,
    badge: undefined as undefined,
  },
] as const;

/**
 * Privacy Concepts Explained
 * Used in educational components, tooltips, and responses
 * Definitions sourced from official Zcash documentation
 */
export const PRIVACY_CONCEPTS = {
  SHIELDED: {
    title: 'Shielded Addresses (Private)',
    description: 'Your transaction details (addresses, amounts, memos) are hidden using zero-knowledge proofs. Only you can see your transaction history.',
    tooltip: 'Addresses, amounts, and memo fields stay private using cryptography. This provides mathematically verified privacy.',
    learnUrl: 'https://z.cash/learn/what-is-the-difference-between-shielded-and-transparent-zcash/',
    icon: '🔒',
  },
  TRANSPARENT: {
    title: 'Transparent Addresses (Public)',
    description: 'Transaction details are visible on the blockchain, like Bitcoin or Ethereum. Useful for regulatory compliance but less private.',
    tooltip: 'Works like most blockchains - all transactions are public and traceable.',
    learnUrl: 'https://z.cash/learn/what-is-the-difference-between-shielded-and-transparent-zcash/',
    icon: '👁️',
  },
  UNIFIED_ADDRESS: {
    title: 'Unified Address (UA)',
    description: 'The modern Zcash address starting with "u". Works with all wallets and pools. Like a universal adapter that automatically provides privacy with supporting wallets.',
    tooltip: 'One address works across all Zcash address types (transparent and shielded). If your wallet supports autoshielding, funds arrive private by default.',
    learnUrl: 'https://z.cash/learn/what-are-zcash-unified-addresses/',
    icon: '🔗',
  },
  PRIVACY_POOL: {
    title: 'Shielded Pool',
    description: 'The set of all shielded transactions on Zcash. Larger pools = better anonymity because your transaction blends with more others.',
    tooltip: 'More users in the pool means better privacy for everyone. Your transaction becomes harder to trace.',
    learnUrl: 'https://z.cash/learn/what-is-zcash/',
    icon: '🌊',
  },
  SHIELDED_BY_DEFAULT: {
    title: 'Shielded by Default',
    description: 'A wallet feature that automatically keeps your Zcash private. Recommended by the Zcash Foundation.',
    tooltip: 'Wallets marked "shielded by default" ensure all transactions use privacy features automatically.',
    learnUrl: 'https://z.cash/learn/whats-the-best-zcash-wallet/',
    icon: '✓',
  },
} as const;

/**
 * Privacy Bridge Guidance
 * Progressive disclosure messaging
 */
export const PRIVACY_BRIDGE_GUIDANCE = {
  SIMPLE: 'Your assets will move to Zcash, where transaction details are hidden from public view.',
  
  DETAILED: `
You're about to bridge your assets to Zcash, a privacy-focused blockchain where:
• Your addresses stay hidden
• Transaction amounts are encrypted
• Your financial history remains private

The bridge uses Axelar's secure cross-chain protocol. After bridging, you'll receive your assets in a Zcash wallet.
  `.trim(),

  POST_BRIDGE_STEPS: [
    {
      step: 1,
      title: 'Confirm the Transaction',
      description: 'Sign the bridge transaction in your wallet',
    },
    {
      step: 2,
      title: 'Wait for Confirmation',
      description: 'Bridge typically completes in 5-10 minutes',
    },
    {
      step: 3,
      title: 'Get a Zcash Wallet',
      description: 'Download Zashi (mobile) or Nighthawk (desktop) - both are shielded by default',
    },
    {
      step: 4,
      title: 'Receive Your Funds',
      description: 'Your bridged assets will appear in your Zcash wallet automatically',
    },
    {
      step: 5,
      title: 'Use Privately',
      description: 'Spend at merchants or send privately to others (visit paywithz.cash for merchant list)',
    },
  ] as const,

  SECURITY_TIPS: [
    'Always use a wallet that is "shielded by default"',
    'Use unified addresses (UA) - they work with all wallets automatically',
    'Enable encrypted memos for private notes on transactions',
    'Avoid reusing the same address for different purposes to maintain anonymity',
    'Backup your seed phrase securely and keep it offline',
    'Verify wallet URLs carefully to avoid phishing',
  ] as const,
} as const;

/**
 * External Resources
 * Links to official Zcash documentation
 */
export const PRIVACY_RESOURCES = {
  // Zcash Learn - Educational Links (Tier 2)
  LEARN_ZCASH: 'https://z.cash/learn/what-is-zcash/',
  SHIELDED_VS_TRANSPARENT: 'https://z.cash/learn/what-is-the-difference-between-shielded-and-transparent-zcash/',
  HOW_TO_USE: 'https://z.cash/learn/how-to-use-zcash/',
  UNIFIED_ADDRESSES: 'https://z.cash/learn/what-are-zcash-unified-addresses/',
  WHY_PRIVACY: 'https://z.cash/learn/why-is-privacy-so-important/',
  WHATS_BEST_WALLET: 'https://z.cash/learn/whats-the-best-zcash-wallet/',
  USEFUL_TIPS: 'https://z.cash/learn/useful-tips-when-using-zcash/',
  SPEND_ZCASH: 'https://z.cash/learn/where-can-i-use-or-spend-zcash/',
  
  // Communities & Merchants
  MERCHANT_DIRECTORY: 'https://paywithz.cash/',
  ECOSYSTEM: 'https://z.cash/ecosystem/',
  COMMUNITY_FORUM: 'https://forum.zcashcommunity.com/',
} as const;

/**
 * Zcash Education Links (Tier 2)
 * Used in progressive disclosure and help sections
 */
export const ZCASH_EDUCATION_LINKS = [
  {
    title: "What's Zcash?",
    description: 'Introduction to Zcash and how it provides privacy',
    url: PRIVACY_RESOURCES.LEARN_ZCASH,
  },
  {
    title: 'Shielded vs. Transparent',
    description: 'Understand the difference between private and public transactions',
    url: PRIVACY_RESOURCES.SHIELDED_VS_TRANSPARENT,
  },
  {
    title: 'Unified Addresses',
    description: 'Learn about modern Zcash addresses that work everywhere',
    url: PRIVACY_RESOURCES.UNIFIED_ADDRESSES,
  },
  {
    title: 'Best Wallets',
    description: 'Find wallets that are "shielded by default"',
    url: PRIVACY_RESOURCES.WHATS_BEST_WALLET,
  },
  {
    title: 'Useful Tips',
    description: 'Security best practices for private transactions',
    url: PRIVACY_RESOURCES.USEFUL_TIPS,
  },
  {
    title: 'Why Privacy Matters',
    description: 'The importance of financial privacy and how Zcash protects it',
    url: PRIVACY_RESOURCES.WHY_PRIVACY,
  },
  {
    title: 'Where to Spend',
    description: 'Merchants and services that accept private Zcash',
    url: PRIVACY_RESOURCES.SPEND_ZCASH,
  },
] as const;

/**
 * Privacy Level Classifications
 */
export const PRIVACY_LEVELS = {
  HIGH: {
    label: 'High (Shielded)',
    description: 'Addresses, amounts, and transaction history are hidden',
    color: 'green.500',
  },
  MEDIUM: {
    label: 'Medium (Mixed)',
    description: 'Some transaction details may be visible',
    color: 'yellow.500',
  },
  LOW: {
    label: 'Low (Transparent)',
    description: 'All transaction details are public',
    color: 'red.500',
  },
} as const;

/**
 * Help users understand privacy features
 * Used in HelpModal and guidance components
 */
export const PRIVACY_FAQ = [
  {
    question: 'What does it mean to "make assets private"?',
    answer: 'You move your assets to Zcash, a blockchain where transactions are hidden. Your addresses, amounts, and transaction history are encrypted and visible only to you.',
  },
  {
    question: 'Do I lose access to my assets?',
    answer: 'No. Your assets move to Zcash and you receive them in a Zcash wallet (Zashi, Nighthawk, etc.). You maintain full control.',
  },
  {
    question: 'What wallet do I need?',
    answer: 'Use a wallet that is "shielded by default" like Zashi (mobile) or Nighthawk (desktop). These ensure your privacy features work correctly.',
  },
  {
    question: 'Can I bridge back to Ethereum?',
    answer: 'Yes. Exchanges like Gemini and Kraken support Zcash trading. You can sell on an exchange and bridge back if needed.',
  },
  {
    question: 'How long does bridging take?',
    answer: 'Typically 5-10 minutes. The bridge uses Axelar\'s secure cross-chain protocol.',
  },
  {
    question: 'Is this legal?',
    answer: 'Yes. Privacy is a legitimate financial right. However, regulations vary by jurisdiction - check local laws.',
  },
] as const;

/**
 * Merchant Directory Information
 * Featured merchants accepting private Zcash payments
 */
export const MERCHANT_DIRECTORY = {
  primary: {
    name: 'Pay With Z',
    description: 'Comprehensive merchant directory for Zcash payments',
    url: 'https://paywithz.cash/',
    badge: 'Official' as const,
    categories: ['Online', 'VPN', 'Hosting', 'Privacy Services'],
  },
  secondaryResources: [
    {
      name: 'Zcash Community',
      description: 'Community-curated list of Zcash-friendly merchants',
      url: 'https://z.cash/community/',
      category: 'Community',
    },
    {
      name: 'Gemini Exchange',
      description: 'Trade Zcash for other assets or fiat (regulated)',
      url: 'https://www.gemini.com/',
      category: 'Exchange',
    },
    {
      name: 'Kraken Exchange',
      description: 'Trade Zcash and bridge back to other chains',
      url: 'https://www.kraken.com/',
      category: 'Exchange',
    },
  ],
  tips: [
    'Start with Pay With Z to discover merchants accepting Zcash',
    'Privacy services (VPN, email) are common Zcash merchants',
    'Some exchanges support Zcash trading if you want to convert back',
    'Always verify merchant URLs before sending funds',
    'Use your shielded address for all Zcash transactions',
  ],
} as const;

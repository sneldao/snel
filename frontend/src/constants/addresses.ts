/* NOTE:
 *  This file must stay framework-agnostic.  No React, JSX, or component
 *  imports should exist here – only plain data structures.
 */

export interface AddressEntry {
  name: string;
  address: string;
  ens?: string;
  category: string;
  description?: string;
  /*  icon is kept as a string identifier so the UI layer can decide
   *  how to render it (e.g., mapping to an actual icon component).
   */
  icon?: string | null;
  tags?: string[];
  verified?: boolean;
}

/**
 * List of common addresses including popular protocols, ENS names, and frequently used addresses
 * Used for auto-completion in the command input
 */
export const COMMON_ADDRESSES: AddressEntry[] = [
  // Notable ENS names
  {
    name: 'Vitalik Buterin',
    address: '0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045',
    ens: 'vitalik.eth',
    category: 'Notable Individuals',
    description: 'Ethereum co-founder',
    icon: null,
    tags: ['ethereum', 'founder'],
    verified: true
  },
  {
    name: 'Ethereum Foundation',
    address: '0xde0B295669a9FD93d5F28D9Ec85E40f4cb697BAe',
    ens: 'ethereumfoundation.eth',
    category: 'Organizations',
    description: 'Non-profit organization dedicated to supporting Ethereum',
    icon: null,
    tags: ['ethereum', 'foundation', 'nonprofit'],
    verified: true
  },
  {
    name: 'ENS',
    address: '0xFe89cc7aBB2C4183683ab71653C4cdc9B02D44b7',
    ens: 'ens.eth',
    category: 'Protocols',
    description: 'Ethereum Name Service',
    icon: null,
    tags: ['ethereum', 'domains', 'naming'],
    verified: true
  },
  
  // DeFi Protocols
  {
    name: 'Uniswap',
    address: '0x1f9840a85d5aF5bf1D1762F925BDADdC4201F984',
    ens: 'uniswap.eth',
    category: 'DeFi Protocols',
    description: 'Decentralized exchange protocol',
    icon: null,
    tags: ['dex', 'swap', 'amm'],
    verified: true
  },
  {
    name: 'Aave',
    address: '0x7Fc66500c84A76Ad7e9c93437bFc5Ac33E2DDaE9',
    ens: 'aave.eth',
    category: 'DeFi Protocols',
    description: 'Decentralized lending protocol',
    icon: null,
    tags: ['lending', 'borrowing', 'defi'],
    verified: true
  },
  {
    name: 'Compound',
    address: '0xc00e94Cb662C3520282E6f5717214004A7f26888',
    ens: 'compound.eth',
    category: 'DeFi Protocols',
    description: 'Decentralized lending protocol',
    icon: null,
    tags: ['lending', 'borrowing', 'defi'],
    verified: true
  },
  {
    name: 'MakerDAO',
    address: '0x9f8F72aA9304c8B593d555F12eF6589cC3A579A2',
    ens: 'makerdao.eth',
    category: 'DeFi Protocols',
    description: 'Decentralized stablecoin protocol',
    icon: null,
    tags: ['stablecoin', 'dai', 'defi'],
    verified: true
  },
  {
    name: 'Curve Finance',
    address: '0xD533a949740bb3306d119CC777fa900bA034cd52',
    ens: 'curve.eth',
    category: 'DeFi Protocols',
    description: 'Stablecoin exchange protocol',
    icon: null,
    tags: ['dex', 'stablecoins', 'amm'],
    verified: true
  },
  {
    name: 'SushiSwap',
    address: '0x6B3595068778DD592e39A122f4f5a5cF09C90fE2',
    ens: 'sushi.eth',
    category: 'DeFi Protocols',
    description: 'Decentralized exchange protocol',
    icon: null,
    tags: ['dex', 'swap', 'amm'],
    verified: true
  },
  {
    name: 'Yearn Finance',
    address: '0x0bc529c00C6401aEF6D220BE8C6Ea1667F6Ad93e',
    ens: 'yearn.eth',
    category: 'DeFi Protocols',
    description: 'Yield aggregator protocol',
    icon: null,
    tags: ['yield', 'aggregator', 'defi'],
    verified: true
  },
  
  // Bridges and Cross-chain Protocols
  {
    name: 'Axelar Network',
    address: '0x2d5d7d31F671F86C782533cc367F14109a082712',
    ens: 'axelar.eth',
    category: 'Bridge Protocols',
    description: 'Cross-chain communication protocol',
    icon: null,
    tags: ['bridge', 'cross-chain', 'interoperability'],
    verified: true
  },
  {
    name: 'Wormhole',
    address: '0x98f3c9e6E3fAce36bAAd05FE09d375Ef1464288B',
    ens: 'wormhole.eth',
    category: 'Bridge Protocols',
    description: 'Cross-chain communication protocol',
    icon: null,
    tags: ['bridge', 'cross-chain', 'interoperability'],
    verified: true
  },
  {
    name: 'Polygon Bridge',
    address: '0xA0c68C638235ee32657e8f720a23ceC1bFc77C77',
    category: 'Bridge Protocols',
    description: 'Ethereum-Polygon bridge',
    icon: null,
    tags: ['bridge', 'polygon', 'ethereum'],
    verified: true
  },
  {
    name: 'Arbitrum Bridge',
    address: '0x8315177aB297bA92A06054cE80a67Ed4DBd7ed3a',
    category: 'Bridge Protocols',
    description: 'Ethereum-Arbitrum bridge',
    icon: null,
    tags: ['bridge', 'arbitrum', 'ethereum'],
    verified: true
  },
  {
    name: 'Optimism Bridge',
    address: '0x99C9fc46f92E8a1c0deC1b1747d010903E884bE1',
    category: 'Bridge Protocols',
    description: 'Ethereum-Optimism bridge',
    icon: null,
    tags: ['bridge', 'optimism', 'ethereum'],
    verified: true
  },
  
  // Exchanges
  {
    name: 'Binance',
    address: '0x28C6c06298d514Db089934071355E5743bf21d60',
    category: 'Exchanges',
    description: 'Centralized cryptocurrency exchange',
    icon: null,
    tags: ['cex', 'exchange', 'trading'],
    verified: true
  },
  {
    name: 'Coinbase',
    address: '0x503828976D22510aad0201ac7EC88293211D23Da',
    category: 'Exchanges',
    description: 'Centralized cryptocurrency exchange',
    icon: null,
    tags: ['cex', 'exchange', 'trading'],
    verified: true
  },
  {
    name: 'Kraken',
    address: '0x2B5634C42055806a59e9107ED44D43c426E58258',
    category: 'Exchanges',
    description: 'Centralized cryptocurrency exchange',
    icon: null,
    tags: ['cex', 'exchange', 'trading'],
    verified: true
  },
  
  // DAOs and Governance
  {
    name: 'Gitcoin',
    address: '0xde21F729137C5Af1b01d73aF1dC21eFfa2B8a0d6',
    ens: 'gitcoin.eth',
    category: 'DAOs',
    description: 'DAO for funding public goods',
    icon: null,
    tags: ['dao', 'funding', 'public goods'],
    verified: true
  },
  {
    name: 'Aragon',
    address: '0xa117000000f279D81A1D3cc75430fAA017FA5A2e',
    ens: 'aragon.eth',
    category: 'DAOs',
    description: 'DAO creation and management platform',
    icon: null,
    tags: ['dao', 'governance', 'organization'],
    verified: true
  },
  {
    name: 'ENS DAO',
    address: '0x323A76393544d5ecca80cd6ef2A560C6a395b7E3',
    category: 'DAOs',
    description: 'Governance DAO for Ethereum Name Service',
    icon: null,
    tags: ['dao', 'governance', 'ens'],
    verified: true
  },
  {
    name: 'Uniswap Governance',
    address: '0x1a9C8182C09F50C8318d769245beA52c32BE35BC',
    category: 'DAOs',
    description: 'Governance DAO for Uniswap',
    icon: null,
    tags: ['dao', 'governance', 'uniswap'],
    verified: true
  },
  
  // NFT Marketplaces
  {
    name: 'OpenSea',
    address: '0x7Be8076f4EA4A4AD08075C2508e481d6C946D12b',
    ens: 'opensea.eth',
    category: 'NFT Marketplaces',
    description: 'NFT marketplace',
    icon: null,
    tags: ['nft', 'marketplace', 'trading'],
    verified: true
  },
  {
    name: 'Rarible',
    address: '0xB66a603f4cFe17e3D27B87a8BfCaD319856518B8',
    ens: 'rarible.eth',
    category: 'NFT Marketplaces',
    description: 'NFT marketplace',
    icon: null,
    tags: ['nft', 'marketplace', 'trading'],
    verified: true
  },
  
  // Staking and Validation
  {
    name: 'Lido',
    address: '0xae7ab96520DE3A18E5e111B5EaAb095312D7fE84',
    ens: 'lido.eth',
    category: 'Staking Protocols',
    description: 'Liquid staking protocol',
    icon: null,
    tags: ['staking', 'ethereum', 'liquid staking'],
    verified: true
  },
  {
    name: 'Rocket Pool',
    address: '0xD33526068D116cE69F19A9ee46F0bd304F21A51f',
    ens: 'rocketpool.eth',
    category: 'Staking Protocols',
    description: 'Decentralized Ethereum staking protocol',
    icon: null,
    tags: ['staking', 'ethereum', 'decentralized'],
    verified: true
  },
  
  // Oracles
  {
    name: 'Chainlink',
    address: '0x514910771AF9Ca656af840dff83E8264EcF986CA',
    ens: 'chainlink.eth',
    category: 'Oracles',
    description: 'Decentralized oracle network',
    icon: null,
    tags: ['oracle', 'data', 'price feeds'],
    verified: true
  },
  {
    name: 'Band Protocol',
    address: '0xBA11D00c5f74255f56a5E366F4F77f5A186d7f55',
    category: 'Oracles',
    description: 'Cross-chain data oracle',
    icon: null,
    tags: ['oracle', 'data', 'cross-chain'],
    verified: true
  },
  
  // Layer 2 Protocols
  {
    name: 'Arbitrum',
    address: '0xB50F58D50e30dFdAAD01B1C6bcC4Ccb0DB55db13',
    category: 'Layer 2',
    description: 'Ethereum Layer 2 scaling solution',
    icon: null,
    tags: ['l2', 'scaling', 'rollup'],
    verified: true
  },
  {
    name: 'Optimism',
    address: '0x4200000000000000000000000000000000000042',
    category: 'Layer 2',
    description: 'Ethereum Layer 2 scaling solution',
    icon: null,
    tags: ['l2', 'scaling', 'rollup'],
    verified: true
  },
  {
    name: 'zkSync',
    address: '0xaBEA9132b05A70803a4E85094fD0e1800777fBEF',
    category: 'Layer 2',
    description: 'Ethereum Layer 2 scaling solution',
    icon: null,
    tags: ['l2', 'scaling', 'zk-rollup'],
    verified: true
  },
  
  // Insurance and Security
  {
    name: 'Nexus Mutual',
    address: '0xCB46C0ddc60D18eFEB0E586C17Af6ea36452Dae0',
    category: 'Insurance',
    description: 'Decentralized insurance protocol',
    icon: null,
    tags: ['insurance', 'defi', 'protection'],
    verified: true
  },
  {
    name: 'Armor Protocol',
    address: '0x1337DEF16F9B486fAEd0293eb623Dc8395dFE46a',
    category: 'Insurance',
    description: 'DeFi insurance protocol',
    icon: null,
    tags: ['insurance', 'defi', 'protection'],
    verified: true
  },
  
  // Development and Infrastructure
  {
    name: 'The Graph',
    address: '0xc944E90C64B2c07662A292be6244BDf05Cda44a7',
    ens: 'thegraph.eth',
    category: 'Infrastructure',
    description: 'Decentralized indexing protocol',
    icon: null,
    tags: ['indexing', 'data', 'api'],
    verified: true
  },
  {
    name: 'Filecoin',
    address: '0x4E1f41613c9084FdB9E34E11fAE9412427480e56',
    category: 'Infrastructure',
    description: 'Decentralized storage network',
    icon: null,
    tags: ['storage', 'data', 'decentralized'],
    verified: true
  },
  
  // SNEL-specific addresses (example)
  {
    name: 'SNEL Treasury',
    address: '0x1234567890123456789012345678901234567890',
    ens: 'snel.eth',
    category: 'SNEL',
    description: 'SNEL protocol treasury',
    icon: null,
    tags: ['snel', 'treasury', 'governance'],
    verified: true
  },
  {
    name: 'SNEL Multisig',
    address: '0x0987654321098765432109876543210987654321',
    category: 'SNEL',
    description: 'SNEL protocol multisig',
    icon: null,
    tags: ['snel', 'multisig', 'governance'],
    verified: true
  },
];

// Helper functions

/**
 * Get addresses by category
 */
export const getAddressesByCategory = (category: string): AddressEntry[] => {
  return COMMON_ADDRESSES.filter(address => address.category === category);
};

/**
 * Search addresses by name, ENS, or address
 */
export const searchAddresses = (query: string): AddressEntry[] => {
  const lowerQuery = query.toLowerCase();
  return COMMON_ADDRESSES.filter(address => 
    address.name.toLowerCase().includes(lowerQuery) ||
    (address.ens && address.ens.toLowerCase().includes(lowerQuery)) ||
    address.address.toLowerCase().includes(lowerQuery)
  );
};

/**
 * Get address by ENS name
 */
export const getAddressByENS = (ens: string): AddressEntry | undefined => {
  return COMMON_ADDRESSES.find(
    address => address.ens && address.ens.toLowerCase() === ens.toLowerCase()
  );
};

/**
 * Get address by Ethereum address
 */
export const getAddressByAddress = (address: string): AddressEntry | undefined => {
  return COMMON_ADDRESSES.find(
    entry => entry.address.toLowerCase() === address.toLowerCase()
  );
};

/**
 * Get all verified addresses
 */
export const getVerifiedAddresses = (): AddressEntry[] => {
  return COMMON_ADDRESSES.filter(address => address.verified);
};

/**
 * Get addresses by tag
 */
export const getAddressesByTag = (tag: string): AddressEntry[] => {
  return COMMON_ADDRESSES.filter(
    address => address.tags && address.tags.includes(tag.toLowerCase())
  );
};

/**
 * Protocol Configuration Matrix
 * 
 * Defines which protocols are used for each network/token combination
 */

export interface ProtocolRoute {
    protocol: 'x402' | 'mnee';
    network_name: string;
    chainId: number;
    contracts: {
        stablecoin: string;
    };
    features: string[];
}

export const PROTOCOL_CONFIG: Record<string, ProtocolRoute> = {
    // Cronos Networks → X402
    'cronos-mainnet': {
        protocol: 'x402',
        network_name: 'Cronos Mainnet',
        chainId: 25,
        contracts: {
            // USDC.e on Cronos Mainnet
            stablecoin: '0xf951eC28187D9E5Ca673Da8FE6757E6f0Be5F77C'
        },
        features: ['automation', 'conditional', 'scheduled', 'apy-triggers']
    },
    'cronos-testnet': {
        protocol: 'x402',
        network_name: 'Cronos Testnet',
        chainId: 338,
        contracts: {
            // devUSDC.e on Cronos Testnet
            stablecoin: '0xc01efAaF7C5C61bEbFAeb358E1161b537b8bC0e0'
        },
        features: ['automation', 'conditional', 'scheduled', 'apy-triggers']
    },

    // Ethereum → MNEE Relayer
    'ethereum-mainnet': {
        protocol: 'mnee',
        network_name: 'Ethereum Mainnet',
        chainId: 1,
        contracts: {
            // MNEE on Ethereum
            stablecoin: '0x8ccedbAe4916b79da7F3F612EfB2EB93A2bFD6cF'
        },
        features: ['gasless', 'relayed', 'permit2', 'instant']
    }
};

export const TOKEN_CONFIG: Record<string, string[]> = {
    'cronos-mainnet': ['USDC'],
    'cronos-testnet': ['USDC'],
    'ethereum-mainnet': ['MNEE']
};

/**
 * Get protocol configuration for a network
 */
export function getProtocolConfig(network: string): ProtocolRoute | null {
    return PROTOCOL_CONFIG[network] || null;
}

/**
 * Get supported tokens for a network
 */
export function getSupportedTokens(network: string): string[] {
    return TOKEN_CONFIG[network] || [];
}

/**
 * Check if network/token combination is supported
 */
export function isNetworkTokenSupported(network: string, token: string): boolean {
    const supportedTokens = getSupportedTokens(network);
    return supportedTokens.includes(token.toUpperCase());
}
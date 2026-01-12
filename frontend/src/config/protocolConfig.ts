/**
 * Protocol Configuration Matrix
 * 
 * Defines which protocols are used for each network/token combination
 */

export interface ProtocolRoute {
    protocol: 'x402' | 'mnee';
    network_name: string;
    features: string[];
}

export const PROTOCOL_CONFIG: Record<string, ProtocolRoute> = {
    // Cronos Networks → X402
    'cronos-mainnet': {
        protocol: 'x402',
        network_name: 'Cronos Mainnet',
        features: ['automation', 'conditional', 'scheduled', 'apy-triggers']
    },
    'cronos-testnet': {
        protocol: 'x402',
        network_name: 'Cronos Testnet',
        features: ['automation', 'conditional', 'scheduled', 'apy-triggers']
    },

    // Ethereum → MNEE Relayer
    'ethereum-mainnet': {
        protocol: 'mnee',
        network_name: 'Ethereum Mainnet',
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
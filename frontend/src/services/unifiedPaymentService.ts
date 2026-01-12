/**
 * Unified Payment Service
 * 
 * Protocol-agnostic payment service that intelligently routes to:
 * - X402 (Cronos/USDC) - Automated conditional payments
 * - MNEE Relayer (Ethereum/MNEE) - Gasless relayed payments
 * 
 * Uses the new decentralized flow: prepare → sign → submit
 */

import axios from 'axios';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export type PaymentProtocol = 'x402' | 'mnee';

export interface UnifiedPaymentRequest {
    network: string;
    user_address: string;
    recipient_address: string;
    amount: number;
    token_symbol: string;
}

export interface UnifiedPaymentResult {
    success: boolean;
    protocol: PaymentProtocol;
    network: string;
    token: string;
    txHash?: string;
    blockNumber?: number;
    timestamp?: string;
    error?: string;
}

export interface PaymentPreparationResult {
    action_type: 'sign_typed_data' | 'approve_allowance' | 'ready_to_execute';
    protocol: PaymentProtocol;

    // For X402 (EIP-712 signing)
    typed_data?: {
        domain: any;
        types: any;
        primaryType: string;
        message: any;
    };

    // For MNEE (Allowance approval)
    relayer_address?: string;
    token_address?: string;
    amount_atomic?: string;
    allowance_sufficient?: boolean;

    metadata: Record<string, any>;
}

export interface NetworkInfo {
    chain_id: number;
    name: string;
    supported_tokens: string[];
    protocols: Record<string, any>;
}

export interface ProtocolInfo {
    chain_id: number;
    token: string;
    protocol: PaymentProtocol;
    network_name: string;
    features: string[];
    description: string;
}

class UnifiedPaymentService {
    /**
     * Step 1: Prepare payment for user signing
     * Returns what action the user needs to take (sign typed data or approve allowance)
     */
    async preparePayment(request: UnifiedPaymentRequest): Promise<PaymentPreparationResult> {
        try {
            const response = await axios.post(`${API_BASE_URL}/api/v1/payment/execute/prepare`, request);
            return response.data;
        } catch (error: any) {
            console.error('Payment preparation failed:', error);
            if (error.response?.data?.detail) {
                throw new Error(error.response.data.detail);
            }
            throw new Error('Failed to prepare payment');
        }
    }

    /**
     * Step 2: Submit signed payment data
     */
    async submitPayment(
        protocol: PaymentProtocol,
        submissionData: Record<string, any>
    ): Promise<UnifiedPaymentResult> {
        try {
            const response = await axios.post(`${API_BASE_URL}/api/v1/payment/execute/submit`, {
                protocol,
                data: submissionData
            });
            return response.data;
        } catch (error: any) {
            console.error('Payment submission failed:', error);
            if (error.response?.data?.detail) {
                throw new Error(error.response.data.detail);
            }
            throw new Error('Failed to submit payment');
        }
    }

    /**
     * Helper: Get network string from chain ID
     */
    getNetworkFromChainId(chainId: number): string {
        switch (chainId) {
            case 25: return 'cronos-mainnet';
            case 338: return 'cronos-testnet';
            case 1: return 'ethereum-mainnet';
            default: throw new Error(`Unsupported chain ID: ${chainId}`);
        }
    }

    /**
     * Helper: Get token symbol from network
     */
    getTokenFromNetwork(network: string): string {
        if (network.includes('cronos')) return 'USDC';
        if (network.includes('ethereum')) return 'MNEE';
        throw new Error(`Unknown network: ${network}`);
    }

    /**
     * Helper: Determine protocol from network
     */
    getProtocolFromNetwork(network: string): PaymentProtocol {
        if (network.includes('cronos')) return 'x402';
        if (network.includes('ethereum')) return 'mnee';
        throw new Error(`Unknown network: ${network}`);
    }

    /**
     * Check if a network/token combination is supported
     */
    isSupported(network: string, token: string): boolean {
        try {
            const expectedToken = this.getTokenFromNetwork(network);
            return expectedToken.toUpperCase() === token.toUpperCase();
        } catch {
            return false;
        }
    }

    /**
     * Get protocol name for display
     */
    getProtocolName(network: string): string {
        if (network.includes('cronos')) return 'Cronos X402 Facilitator';
        if (network.includes('ethereum')) return 'Ethereum MNEE Relayer';
        return 'Unknown Protocol';
    }

    /**
     * Get protocol description for display
     */
    getProtocolDescription(network: string): string {
        if (network.includes('cronos')) {
            return 'Automated conditional payments. Sign once, execute when conditions are met.';
        }
        if (network.includes('ethereum')) {
            return 'Gasless transactions with instant settlement. No ETH needed for gas.';
        }
        return 'Unknown protocol';
    }

    /**
     * Get protocol features
     */
    getProtocolFeatures(network: string): string[] {
        if (network.includes('cronos')) {
            return ['automation', 'conditional', 'scheduled', 'apy-triggers'];
        }
        if (network.includes('ethereum')) {
            return ['gasless', 'relayed', 'permit2', 'instant'];
        }
        return [];
    }
}

// Export singleton instance
export const unifiedPaymentService = new UnifiedPaymentService();
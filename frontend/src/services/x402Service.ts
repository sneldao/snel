/**
 * X402 Agentic Payment Service
 * 
 * Handles real x402 payments on Cronos EVM using the backend API.
 */

import axios from 'axios';
import { createWalletClient, custom, parseEther } from 'viem';
import { cronos, cronosTestnet } from 'viem/chains';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export interface X402PaymentRequest {
    recipient_address: string;
    amount_usdc: number;
    network: 'cronos-mainnet' | 'cronos-testnet' | 'ethereum-mainnet';
    metadata?: Record<string, any>;
}

export interface X402PaymentResult {
    success: boolean;
    txHash?: string;
    blockNumber?: number;
    timestamp?: string;
    error?: string;
    from_address?: string;
    to_address?: string;
    value?: string;
    network: string;
    facilitator_url: string;
}

export interface X402HealthStatus {
    healthy: boolean;
    network: string;
    facilitator_url: string;
    supported_schemes: any[];
}

class X402Service {
    /**
     * Check x402 facilitator service health
     */
    async checkHealth(network: 'cronos-mainnet' | 'cronos-testnet' | 'ethereum-mainnet' = 'cronos-testnet'): Promise<X402HealthStatus> {
        try {
            const response = await axios.get(`${API_BASE_URL}/api/v1/x402/health/${network}`);
            return response.data;
        } catch (error) {
            console.error('X402 health check failed:', error);
            throw new Error('Failed to check x402 service health');
        }
    }

    /**
     * Get supported networks for x402 payments
     */
    async getSupportedNetworks() {
        try {
            const response = await axios.get(`${API_BASE_URL}/api/v1/x402/supported-networks`);
            return response.data;
        } catch (error) {
            console.error('Failed to get supported networks:', error);
            throw new Error('Failed to get supported networks');
        }
    }

    /**
     * Step 1: Prepare payment for client-side signing
     * Returns EIP-712 typed data
     */
    async preparePayment(
        userAddress: string,
        recipientAddress: string,
        amountUsdc: number,
        network: 'cronos-mainnet' | 'cronos-testnet' = 'cronos-testnet'
    ) {
        try {
            const response = await axios.post(`${API_BASE_URL}/api/v1/x402/prepare-payment`, {
                user_address: userAddress,
                recipient_address: recipientAddress,
                amount_usdc: amountUsdc,
                network
            });
            return response.data;
        } catch (error) {
            console.error('Failed to prepare x402 payment:', error);
            throw new Error('Failed to prepare payment');
        }
    }

    /**
     * Step 2: Submit signed payment to backend
     */
    async submitPayment(
        signature: string,
        userAddress: string,
        message: any,
        metadata: any
    ): Promise<X402PaymentResult> {
        try {
            const response = await axios.post(`${API_BASE_URL}/api/v1/x402/submit-payment`, {
                signature,
                user_address: userAddress,
                message,
                metadata
            });
            return response.data;
        } catch (error: any) {
            console.error('Failed to submit x402 payment:', error);
            if (error.response?.data?.detail) {
                throw new Error(error.response.data.detail);
            }
            throw new Error('Failed to submit payment');
        }
    }

    /**
     * Execute x402 payment with wallet signature
     * This is a simplified version - in production you'd integrate with wallet providers
     */
    async executePayment(
        request: X402PaymentRequest,
        walletPrivateKey?: string // In production, use wallet integration instead
    ): Promise<X402PaymentResult> {
        try {
            if (!walletPrivateKey) {
                throw new Error('Wallet integration required for x402 payments');
            }

            // Validate request
            if (!request.recipient_address.startsWith('0x') || request.recipient_address.length !== 42) {
                throw new Error('Invalid recipient address format');
            }

            if (request.amount_usdc <= 0 || request.amount_usdc > 10000) {
                throw new Error('Amount must be between 0 and 10,000 USDC');
            }

            // Execute payment via backend API
            const response = await axios.post(`${API_BASE_URL}/api/v1/x402/execute-payment`, {
                private_key: walletPrivateKey,
                recipient_address: request.recipient_address,
                amount_usdc: request.amount_usdc,
                network: request.network,
                metadata: request.metadata
            });

            return response.data;
        } catch (error: any) {
            console.error('X402 payment execution failed:', error);

            if (error.response?.data?.detail) {
                throw new Error(error.response.data.detail);
            }

            throw new Error('Failed to execute x402 payment');
        }
    }

    /**
     * Verify x402 payment header without executing
     */
    async verifyPayment(
        paymentHeader: string,
        recipientAddress: string,
        amountUsdc: number,
        network: 'cronos-mainnet' | 'cronos-testnet' | 'ethereum-mainnet' = 'cronos-testnet'
    ) {
        try {
            const response = await axios.post(`${API_BASE_URL}/api/v1/x402/verify-payment`, {
                payment_header: paymentHeader,
                recipient_address: recipientAddress,
                amount_usdc: amountUsdc,
                network
            });

            return response.data;
        } catch (error) {
            console.error('X402 payment verification failed:', error);
            throw new Error('Failed to verify x402 payment');
        }
    }

    /**
     * Get chain configuration for x402 networks
     */
    getChainConfig(network: 'cronos-mainnet' | 'cronos-testnet' | 'ethereum-mainnet') {
        if (network === 'ethereum-mainnet') {
            return { id: 1, name: 'Ethereum' };
        }
        return network === 'cronos-mainnet' ? cronos : cronosTestnet;
    }

    /**
     * Format amount for display
     */
    formatAmount(amount: number, decimals: number = 6): string {
        return (amount / Math.pow(10, decimals)).toFixed(6);
    }

    /**
     * Parse amount to atomic units
     */
    parseAmount(amount: number, decimals: number = 6): bigint {
        return BigInt(Math.floor(amount * Math.pow(10, decimals)));
    }

    /**
     * Get stablecoin contract address for network
     */
    getStablecoinContract(network: 'cronos-mainnet' | 'cronos-testnet' | 'ethereum-mainnet'): string {
        const contracts = {
            'cronos-mainnet': '0xf951eC28187D9E5Ca673Da8FE6757E6f0Be5F77C',  // USDC.e Mainnet
            'cronos-testnet': '0xc01efAaF7C5C61bEbFAeb358E1161b537b8bC0e0',   // devUSDC.e Testnet
            'ethereum-mainnet': '0x7D89c67d3c4E72E8C5c64BE201dC225F99d16aCa'  // MNEE stablecoin
        };
        return contracts[network];
    }

    /**
     * Get stablecoin symbol for network
     */
    getStablecoinSymbol(network: 'cronos-mainnet' | 'cronos-testnet' | 'ethereum-mainnet'): string {
        return network === 'ethereum-mainnet' ? 'MNEE' : 'USDC';
    }

    /**
     * Get facilitator URL for network
     */
    getFacilitatorUrl(network: 'cronos-mainnet' | 'cronos-testnet' | 'ethereum-mainnet'): string {
        return 'https://facilitator.cronoslabs.org/v2/x402';
    }
}

// Export singleton instance
export const x402Service = new X402Service();
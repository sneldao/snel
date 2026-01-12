/**
 * MNEE Relayer Service
 * 
 * Handles decentralized MNEE payments on Ethereum via Relayer.
 * Users approve the Relayer contract, and the Agent executes transfers.
 */

import axios from 'axios';
import { createWalletClient, custom, parseUnits } from 'viem';
import { mainnet } from 'viem/chains';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export interface RelayedPaymentResponse {
    success: boolean;
    tx_hash: string;
    amount_atomic: number;
}

export interface AllowanceResponse {
    allowance: string;
    allowance_atomic: number;
    relayer_address: string;
    is_sufficient: boolean;
}

class MneeService {
    /**
     * Get the Relayer address that needs approval
     */
    async getRelayerAddress(): Promise<string> {
        try {
            const response = await axios.get(`${API_BASE_URL}/api/v1/mnee/relayer-address`);
            return response.data.address;
        } catch (error) {
            console.error('Failed to get relayer address:', error);
            throw new Error('Failed to get relayer address');
        }
    }

    /**
     * Check if user has sufficient allowance for the Relayer
     */
    async checkAllowance(walletAddress: string, amountNeeded?: number): Promise<AllowanceResponse> {
        try {
            const params = amountNeeded ? `?amount_needed=${amountNeeded}` : '';
            const response = await axios.get(`${API_BASE_URL}/api/v1/mnee/allowance/${walletAddress}${params}`);
            return response.data;
        } catch (error) {
            console.error('Failed to check allowance:', error);
            throw new Error('Failed to check allowance');
        }
    }

    /**
     * Execute the relayed payment (Server-side execution using Relayer gas)
     * User must have approved the Relayer first.
     */
    async executeRelayedPayment(
        userAddress: string,
        recipientAddress: string,
        amount: number
    ): Promise<RelayedPaymentResponse> {
        try {
            const response = await axios.post(`${API_BASE_URL}/api/v1/mnee/execute-relayed-payment`, {
                user_address: userAddress,
                recipient_address: recipientAddress,
                amount: amount
            });
            return response.data;
        } catch (error: any) {
            console.error('Relayed payment execution failed:', error);
            if (error.response?.data?.detail) {
                throw new Error(error.response.data.detail);
            }
            throw new Error('Failed to execute relayed payment');
        }
    }

    /**
     * Helper to get MNEE contract address
     */
    getMneeAddress(): `0x${string}` {
        return "0x8ccedbAe4916b79da7F3F612EfB2EB93A2bFD6cF";
    }
}

export const mneeService = new MneeService();

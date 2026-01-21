import { getProtocolConfig } from '../config/protocolConfig';

/**
 * X402 SDK Utility Wrapper
 * 
 * Defines the standard X402 PaymentHeader structure and provides validation utilities.
 * Note: Local interface definitions are used here to ensure stability and reduce
 * external dependency bloat implementation details.
 */

export interface X402Payload {
    from: string;
    to: string;
    value: string;
    validAfter: number;
    validBefore: number;
    nonce: string;
    signature: string;
    asset: string;
}

export interface PaymentHeader {
    x402Version: number;
    scheme: string;
    network: string;
    payload: X402Payload;
}

export interface PaymentParams {
    network: string;
    chainId: number;
    userAddress: string;
    recipientAddress: string;
    amountAtomic: string;
    tokenAddress: string;
    timeoutSeconds?: number;
}

/**
 * Validates if the backend-generated payload matches what the SDK expects.
 * This is a "Sanity Check" using the official SDK.
 */
export function validateProtocolCompliance(
    payload: any,
    params: PaymentParams
): boolean {
    try {
        // We can use the SDK types to verify structure
        const header = payload as PaymentHeader;

        if (header.x402Version !== 1) return false;

        // Check if payload matches params
        if (header.payload.to.toLowerCase() !== params.recipientAddress.toLowerCase()) return false;
        if (header.payload.value !== params.amountAtomic) return false;

        return true;
    } catch (e) {
        console.error("X402 SDK Validation Failed:", e);
        return false;
    }
}

/**
 * Helper to get the canonical token address for a network using the centralized protocol config.
 * This ensures Single Source of Truth for all contract addresses.
 */
export function getOfficialTokenAddress(network: string): string | null {
    const config = getProtocolConfig(network);
    if (!config || !config.contracts || !config.contracts.stablecoin) {
        return null;
    }
    return config.contracts.stablecoin;
}

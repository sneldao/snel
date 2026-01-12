/**
 * Payment Action Service - Create and manage recurring payment actions
 * CLEAN: Single responsibility for Payment Action API calls
 * MODULAR: Independent service that can be used across components
 */

interface CreatePaymentActionRequest {
    name: string;
    action_type?: string;
    amount: string;
    token: string;
    recipient_address: string;
    chain_id: number;
    frequency: string;
    metadata?: Record<string, any>;
    is_pinned?: boolean;
}

interface PaymentActionResponse {
    id: string;
    name: string;
    action_type: string;
    amount: string;
    token: string;
    recipient_address: string;
    is_enabled: boolean;
    created_at: string;
    last_used?: string;
    usage_count: number;
}

class PaymentActionService {
    private baseUrl: string;

    constructor() {
        this.baseUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
    }

    async createPaymentAction(
        walletAddress: string,
        request: CreatePaymentActionRequest
    ): Promise<PaymentActionResponse> {
        const response = await fetch(`${this.baseUrl}/api/v1/payment-actions?wallet_address=${walletAddress}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(request),
        });

        if (!response.ok) {
            const error = await response.text();
            throw new Error(`Failed to create payment action: ${error}`);
        }

        return response.json();
    }

    async getPaymentActions(walletAddress: string): Promise<PaymentActionResponse[]> {
        const response = await fetch(`${this.baseUrl}/api/v1/payment-actions?wallet_address=${walletAddress}`);

        if (!response.ok) {
            const error = await response.text();
            throw new Error(`Failed to get payment actions: ${error}`);
        }

        return response.json();
    }

    async deletePaymentAction(walletAddress: string, actionId: string): Promise<void> {
        const response = await fetch(`${this.baseUrl}/api/v1/payment-actions/${actionId}?wallet_address=${walletAddress}`, {
            method: 'DELETE',
        });

        if (!response.ok) {
            const error = await response.text();
            throw new Error(`Failed to delete payment action: ${error}`);
        }
    }
}

export const paymentActionService = new PaymentActionService();
export type { CreatePaymentActionRequest, PaymentActionResponse };
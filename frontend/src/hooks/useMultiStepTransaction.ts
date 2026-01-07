/**
 * Multi-step transaction handler hook
 * Extracted from CommandResponse.tsx for modularity
 */

import { useState, useCallback, useMemo } from 'react';
import { useToast } from '@chakra-ui/react';
import { TransactionService } from '../services/transactionService';
import { ApiService } from '../services/apiService';
import type { TransactionData } from '../types/responses';
import type { AgentType } from '../utils/agentInfo';

interface MultiStepState {
    steps: any[];
    currentStep: number;
    totalSteps: number;
    isComplete: boolean;
    error?: string;
}

interface UseMultiStepTransactionProps {
    transactionService: TransactionService | null;
    address: string | undefined;
    chainId: number;
    agentType?: AgentType;
    transactionData?: TransactionData;
}

export const useMultiStepTransaction = ({
    transactionService,
    address,
    chainId,
    agentType,
    transactionData,
}: UseMultiStepTransactionProps) => {
    const [isExecuting, setIsExecuting] = useState(false);
    const [userRejected, setUserRejected] = useState(false);
    const [multiStepState, setMultiStepState] = useState<MultiStepState | null>(null);
    const toast = useToast();
    const apiService = useMemo(() => new ApiService(), []);

    const handleMultiStepTransaction = useCallback(
        async (txData: any) => {
            console.log('handleMultiStepTransaction called with txData:', txData);

            if (!transactionService || !address || !chainId) {
                toast({
                    title: 'Error',
                    description: 'Wallet not properly connected',
                    status: 'error',
                    duration: 5000,
                });
                return;
            }

            const flowInfo = txData.flow_info || {};
            const currentStepNumber = flowInfo.current_step || 1;

            try {
                setIsExecuting(true);
                setMultiStepState({
                    steps: [
                        {
                            step: flowInfo.current_step || 1,
                            stepType: flowInfo.step_type || 'approval',
                            status: 'executing',
                            description: txData.message || 'Executing transaction...',
                        },
                    ],
                    currentStep: flowInfo.current_step || 1,
                    totalSteps: flowInfo.total_steps || 1,
                    isComplete: false,
                });

                const transactionToExecute = txData.transaction || transactionData;

                if (!transactionToExecute) {
                    throw new Error('No transaction data available for execution');
                }

                const result = await transactionService.executeTransaction(transactionToExecute);

                if (result.success) {
                    setMultiStepState((prev: MultiStepState | null) =>
                        prev
                            ? {
                                ...prev,
                                steps: prev.steps.map((step: any) =>
                                    step.step === (flowInfo.current_step || 1)
                                        ? { ...step, status: 'completed', hash: result.hash }
                                        : step
                                ),
                            }
                            : null
                    );

                    const endpoint =
                        agentType === 'bridge'
                            ? '/api/v1/chat/complete-bridge-step'
                            : '/api/v1/swap/complete-step';

                    const response = await fetch(endpoint, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            wallet_address: address,
                            chain_id: chainId,
                            tx_hash: result.hash as string,
                            success: true,
                        }),
                    });

                    if (!response.ok) {
                        const errorText = await response.text();
                        console.error('Server error response:', errorText);
                        throw new Error(`Server returned ${response.status}: ${errorText.substring(0, 100)}`);
                    }

                    const nextStepResponse = await response.json();

                    if (nextStepResponse.success && nextStepResponse.has_next_step) {
                        const nextTxData = nextStepResponse.content;
                        const nextTransaction = nextStepResponse.transaction;

                        setMultiStepState((prev: MultiStepState | null) =>
                            prev
                                ? {
                                    ...prev,
                                    steps: [
                                        ...prev.steps,
                                        {
                                            step: nextTxData.flow_info.current_step,
                                            stepType: nextTxData.flow_info.step_type,
                                            status: 'pending',
                                            description: nextTxData.message,
                                        },
                                    ],
                                    currentStep: nextTxData.flow_info.current_step,
                                }
                                : null
                        );

                        setTimeout(() => {
                            handleMultiStepTransaction({
                                ...nextTxData,
                                transaction: nextTransaction,
                            });
                        }, 2000);
                    } else {
                        setMultiStepState((prev: MultiStepState | null) =>
                            prev ? { ...prev, isComplete: true } : null
                        );

                        toast({
                            title: 'Success!',
                            description: 'All transaction steps completed successfully',
                            status: 'success',
                            duration: 5000,
                        });
                    }
                } else {
                    throw new Error('Transaction failed');
                }
            } catch (error) {
                const errorMessage = error instanceof Error ? error.message : String(error);
                const isUserRejection =
                    errorMessage.toLowerCase().includes('cancelled') ||
                    errorMessage.toLowerCase().includes('rejected') ||
                    errorMessage.toLowerCase().includes('user denied');

                if (isUserRejection) {
                    setUserRejected(true);
                }

                setMultiStepState((prev: MultiStepState | null) =>
                    prev
                        ? {
                            ...prev,
                            steps: prev.steps.map((step: any) =>
                                step.step === currentStepNumber
                                    ? { ...step, status: 'failed', error: errorMessage }
                                    : step
                            ),
                            error: errorMessage,
                        }
                        : null
                );

                if (address && chainId) {
                    try {
                        await apiService.completeTransactionStep(
                            address,
                            chainId,
                            '',
                            false,
                            errorMessage
                        );
                    } catch (e) {
                        console.error('Failed to notify backend of transaction failure:', e);
                    }
                }

                toast({
                    title: isUserRejection ? 'Transaction Cancelled' : 'Transaction Failed',
                    description: isUserRejection ? 'You cancelled the transaction' : errorMessage,
                    status: isUserRejection ? 'warning' : 'error',
                    duration: 5000,
                });
            } finally {
                setIsExecuting(false);
            }
        },
        [transactionService, address, chainId, apiService, toast, agentType, transactionData]
    );

    return {
        isExecuting,
        userRejected,
        multiStepState,
        handleMultiStepTransaction,
        setUserRejected,
    };
};

/**
 * CommandResponse - Refactored and Modular
 * Orchestrates response rendering using extracted hooks and utilities
 * 
 * BEFORE: 1,388 lines (monolithic)
 * AFTER: ~400 lines (orchestration only)
 */

import * as React from 'react';
import {
    Box,
    HStack,
    VStack,
    Avatar,
    Text,
    useColorModeValue,
    useToast,
    useDisclosure,
} from '@chakra-ui/react';
import { useAccount, useChainId, useWalletClient, usePublicClient } from 'wagmi';
import { parseAbi, parseUnits } from 'viem';

// Services
import { ApiService } from '../services/apiService';
import { TransactionService } from '../services/transactionService';
import { unifiedPaymentService } from '../services/unifiedPaymentService';
import { getProtocolConfig } from '../config/protocolConfig';

// Hooks
import { useMultiStepTransaction } from '../hooks/useMultiStepTransaction';
import { useUserProfile } from '../hooks/useUserProfile';
import { useCommandActions } from '../hooks/useCommandActions';

// Utils
import { detectResponseTypes } from '../utils/responseTypeDetection';
import { getTransactionFromContent } from '../utils/transactionUtils';
import { getAgentInfo, type AgentType } from '../utils/agentInfo';
import { formatLinks } from '../utils/linkFormatting';
import { formatErrorMessage } from '../utils/errorFormatting';
import {
    isStringContent,
    getContentMessage,
    getContentError,
} from '../utils/contentTypeGuards';

// Components
import { ResponseRenderer } from './Response/ResponseRenderer';
import { PortfolioModal } from './Portfolio/PortfolioModal';
import AggregatorSelection from './AggregatorSelection';

// Types
import type {
    ResponseContent,
    ResponseMetadata,
    TransactionData,
    SwapQuote,
    Response,
} from '../types/responses';

interface CommandResponseProps {
    content: ResponseContent;
    timestamp: string;
    isCommand: boolean;
    status?: 'pending' | 'processing' | 'success' | 'error';
    awaitingConfirmation?: boolean;
    agentType?: AgentType;
    metadata?: ResponseMetadata;
    requires_selection?: boolean;
    all_quotes?: SwapQuote[];
    onQuoteSelect?: (response: Response, quote: SwapQuote) => void;
    transaction?: TransactionData;
    onActionClick?: (action: Record<string, unknown>) => void;
    onExecuteTransaction?: (transactionData: TransactionData) => Promise<void>;
    isExecuting?: boolean;
    className?: string;
}

export const CommandResponse: React.FC<CommandResponseProps> = (props) => {
    const {
        content,
        timestamp,
        isCommand,
        status = 'success',
        awaitingConfirmation = false,
        agentType = 'default',
        metadata,
        requires_selection = false,
        all_quotes = [],
        onQuoteSelect,
        transaction,
        onActionClick,
    } = props;

    // Wallet and chain info
    const { address } = useAccount();
    const chainId = useChainId();
    const { data: walletClient } = useWalletClient();
    const publicClient = usePublicClient();
    const toast = useToast();

    // Services
    const transactionService = React.useMemo(
        () =>
            walletClient && publicClient && chainId
                ? new TransactionService(walletClient as any, publicClient as any, chainId)
                : null,
        [walletClient, publicClient, chainId]
    );

    const apiService = React.useMemo(() => new ApiService(), []);

    // Extract transaction data
    const transactionData = transaction || getTransactionFromContent(content);

    // Multi-step transaction hook
    const {
        isExecuting,
        userRejected,
        multiStepState,
        handleMultiStepTransaction,
        setUserRejected,
        reset,
        retry,
    } = useMultiStepTransaction({
        transactionService,
        address,
        chainId,
        agentType,
        transactionData,
    });

    // Detect response types
    const typeChecks = detectResponseTypes({
        content,
        agentType,
        awaitingConfirmation,
        transactionData,
    });

    // Portfolio modal state
    const {
        isOpen: isPortfolioModalOpen,
        onOpen: onPortfolioModalOpen,
        onClose: onPortfolioModalClose,
    } = useDisclosure();

    // Theme colors
    const bgColor = useColorModeValue(
        isCommand ? 'blue.50' : 'gray.50',
        isCommand ? 'blue.900' : 'gray.700'
    );
    const borderColor = useColorModeValue(
        isCommand ? 'blue.200' : 'gray.200',
        isCommand ? 'blue.700' : 'gray.600'
    );
    const textColor = useColorModeValue('gray.800', 'white');

    // Command actions
    const { handleConfirm, handleCancel, handlePredefinedQuery } = useCommandActions();

    // User profile
    const { getUserDisplayName } = useUserProfile();

    // Agent info
    const { handle, avatarSrc } = getAgentInfo(agentType);

    // Handle quote selection
    const handleQuoteSelect = (quote: any) => {
        if (onQuoteSelect) {
            onQuoteSelect(
                {
                    content,
                    timestamp,
                    isCommand,
                    status,
                    awaitingConfirmation,
                    agentType,
                    metadata,
                    requires_selection,
                    all_quotes,
                },
                quote
            );
        }
    };

    // Handle transaction execution
    const handleExecuteTransaction = React.useCallback(async () => {
        if (!transactionData || !walletClient || !publicClient) {
            toast({
                title: 'Transaction Error',
                description: 'Missing transaction data or wallet connection',
                status: 'error',
                duration: 5000,
                isClosable: true,
            });
            return;
        }

        if (userRejected) {
            return;
        }

        try {
            const txService = new TransactionService(walletClient as any, publicClient as any, chainId);
            const result = await txService.executeTransaction(transactionData);

            // Handle Payment Result Submission
            if (typeChecks.isPaymentSignature && address && content && typeof content === 'object') {
                const actionId = (content as any).action_id;
                if (actionId && result?.hash) {
                    await apiService.submitPaymentResult(actionId, result.hash as string, address);
                    toast({
                        title: 'Payment Submitted',
                        description: 'Your payment has been recorded successfully.',
                        status: 'success',
                        duration: 3000,
                        isClosable: true,
                    });
                }
            } else {
                toast({
                    title: 'Transaction Sent',
                    description: `Transaction hash: ${result.hash}`,
                    status: 'success',
                    duration: 5000,
                    isClosable: true,
                });
            }
        } catch (error) {
            console.error('Failed to execute transaction:', error);
            const errorMessage = error instanceof Error ? error.message : String(error);
            const isUserRejection =
                errorMessage.toLowerCase().includes('cancelled') ||
                errorMessage.toLowerCase().includes('rejected') ||
                errorMessage.toLowerCase().includes('user denied');

            if (isUserRejection) {
                setUserRejected(true);
            }

            toast({
                title: isUserRejection ? 'Transaction Cancelled' : 'Transaction Failed',
                description: isUserRejection ? 'You cancelled the transaction' : errorMessage,
                status: isUserRejection ? 'warning' : 'error',
                duration: 5000,
                isClosable: true,
            });
        }
    }, [transactionData, walletClient, publicClient, chainId, userRejected, toast, setUserRejected, typeChecks, address, content, apiService]);

    // Handle portfolio action clicks
    const handleActionClick = React.useCallback(
        (action: any) => {
            if (action.type === 'view_full_portfolio') {
                onPortfolioModalOpen();
            } else if (onActionClick) {
                onActionClick(action);
            }
        },
        [onPortfolioModalOpen, onActionClick]
    );

    // Handle X402 Automation Execution using Unified Service
    const handleX402Execution = React.useCallback(async (overrides?: any) => {
        if (!walletClient || !address) {
            toast({ title: 'Wallet not connected', status: 'error', duration: 3000 });
            return;
        }

        const baseMetadata = (content as any).metadata || {};
        const metadata = { ...baseMetadata, ...(overrides || {}) };

        const amount = parseFloat(metadata.amount || metadata.budget || '0');
        const approvalAmount = metadata.approval_amount ? parseFloat(metadata.approval_amount) : amount;
        const asset = metadata.asset || 'USDC';
        const network = metadata.network || 'cronos-testnet';
        const recipient = metadata.recipient || metadata.payTo;
        const frequency = metadata.interval || 'monthly';
        const budgetCapMonths = metadata.budget_cap_months || 12;

        if (!recipient) {
            throw new Error('No recipient address specified in automation metadata');
        }

        // Create Payment Action with user's final parameters if this is a recurring payment
        if (metadata.automation_type === 'recurring_payment' && !metadata.action_id) {
            try {
                const { paymentActionService } = await import('../services/paymentActionService');

                const chainId = network === 'ethereum-mainnet' ? 1 :
                    network === 'cronos-mainnet' ? 25 : 338;

                const action = await paymentActionService.createPaymentAction(address, {
                    name: `${frequency.charAt(0).toUpperCase() + frequency.slice(1)} to ${recipient.slice(0, 8)}...`,
                    amount: amount.toString(),
                    token: asset,
                    recipient_address: recipient,
                    chain_id: chainId,
                    frequency: frequency,
                    metadata: {
                        network,
                        budget_cap_months: budgetCapMonths,
                        created_via: 'x402_automation_card'
                    },
                    is_pinned: true
                });

                toast({
                    title: "Payment Action Created",
                    description: `Recurring ${frequency} payment scheduled`,
                    status: "success"
                });

                // Update metadata with action ID for future reference
                metadata.action_id = action.id;

            } catch (error) {
                console.error('Failed to create Payment Action:', error);
                toast({
                    title: "Warning",
                    description: "Payment will execute but recurring schedule may not persist",
                    status: "warning"
                });
            }
        }

        try {
            // Step 1: Prepare payment
            // Calculate approval amount based on user's custom budget cap
            let finalApprovalAmount = approvalAmount;
            if (metadata.automation_type === 'recurring_payment') {
                const frequencyMultipliers = {
                    'daily': 365,
                    'weekly': 52,
                    'monthly': 12
                };
                const multiplier = frequencyMultipliers[frequency] || 12;
                finalApprovalAmount = amount * multiplier * (budgetCapMonths / 12);
            }

            toast({ title: "Preparing Payment...", status: "info", duration: 2000 });

            const preparation = await unifiedPaymentService.preparePayment({
                network,
                user_address: address,
                recipient_address: recipient,
                amount: finalApprovalAmount, // Use calculated approval amount
                token_symbol: asset
            });

            if (preparation.action_type === 'sign_typed_data' && preparation.typed_data) {
                // X402 Flow: Sign EIP-712 data
                const signature = await walletClient.signTypedData({
                    domain: preparation.typed_data.domain,
                    types: preparation.typed_data.types,
                    primaryType: preparation.typed_data.primaryType,
                    message: preparation.typed_data.message
                });

                toast({ title: "Submitting Payment...", status: "info", duration: 2000 });

                // Ensure we submit with original single payment amount metadata
                const submitMetadata = {
                    ...preparation.metadata,
                    amount: amount // Force single payment amount for execution
                };

                await unifiedPaymentService.submitPayment(preparation.protocol, {
                    signature,
                    user_address: address,
                    message: preparation.typed_data.message,
                    metadata: submitMetadata
                });

                toast({ title: "Automation Authorized!", description: "Payment executed successfully.", status: "success" });

            } else if (preparation.action_type === 'approve_allowance') {
                // MNEE Flow: Approve allowance if needed
                if (!preparation.allowance_sufficient) {
                    const durationText = budgetCapMonths === 12 ? '1-year' : `${budgetCapMonths}-month`;
                    toast({
                        title: "Approval Required",
                        description: `Please approve the ${durationText} budget cap (${finalApprovalAmount.toLocaleString()} ${asset}).`,
                        status: "warning",
                        duration: 5000
                    });

                    const hash = await walletClient.writeContract({
                        address: preparation.token_address! as `0x${string}`,
                        abi: parseAbi(['function approve(address spender, uint256 amount) returns (bool)']),
                        functionName: 'approve',
                        args: [preparation.relayer_address! as `0x${string}`, BigInt(preparation.amount_atomic!)], // This uses the annual amount
                        chain: undefined // Let wallet decide
                    });

                    toast({ title: "Approval Sent", description: "Waiting for confirmation...", status: "success", duration: 5000 });
                    if (publicClient) {
                        await publicClient.waitForTransactionReceipt({ hash });
                    }
                }

                toast({ title: "Executing Payment...", description: "Agent is processing the first transfer...", status: "info", duration: 3000 });

                // Submit execution for SINGLE payment amount
                const submitMetadata = {
                    ...preparation.metadata,
                    amount: amount // Override to single payment amount
                };

                await unifiedPaymentService.submitPayment(preparation.protocol, {
                    metadata: submitMetadata
                });

                toast({ title: "Payment Executed!", description: "First transfer completed via Relayer.", status: "success" });

            } else if (preparation.action_type === 'ready_to_execute') {
                // Already ready - just execute
                await unifiedPaymentService.submitPayment(preparation.protocol, {
                    metadata: preparation.metadata
                });

                toast({ title: "Payment Executed!", description: "Transfer completed successfully.", status: "success" });
            }

        } catch (error) {
            console.error("Automation error:", error);
            const msg = error instanceof Error ? error.message : String(error);
            toast({ title: "Execution Failed", description: msg, status: "error" });
        }
    }, [walletClient, address, content, toast, publicClient]);

    // Check if needs quote selection
    const needsSelection = requires_selection && all_quotes && all_quotes.length > 0;

    // Render quote selection if needed
    if (needsSelection) {
        return (
            <Box
                bg={bgColor}
                borderWidth="1px"
                borderColor={borderColor}
                borderRadius="lg"
                p={4}
                mb={4}
                className={props.className}
            >
                <AggregatorSelection
                    quotes={all_quotes}
                    onSelect={handleQuoteSelect}
                    isLoading={status === 'processing'}
                    tokenSymbol={
                        typeof content === 'object' && content !== null && 'tokenOut' in content
                            ? (content as any).tokenOut?.symbol || 'Tokens'
                            : 'Tokens'
                    }
                    tokenDecimals={
                        typeof content === 'object' && content !== null && 'tokenOut' in content
                            ? (content as any).tokenOut?.decimals || 18
                            : 18
                    }
                />
            </Box>
        );
    }

    // Main render
    return (
        <>
            <Box
                bg={bgColor}
                borderWidth="1px"
                borderColor={borderColor}
                borderRadius="lg"
                p={4}
                mb={4}
                className={props.className}
            >
                <HStack align="start" spacing={3}>
                    {/* Avatar */}
                    <Avatar size="sm" name={isCommand ? getUserDisplayName() : handle} src={avatarSrc} />

                    {/* Content */}
                    <VStack align="start" spacing={2} flex={1}>
                        {/* Header */}
                        <HStack justify="space-between" w="100%">
                            <Text fontSize="sm" fontWeight="bold" color={textColor}>
                                {isCommand ? getUserDisplayName() : handle}
                            </Text>
                            <Text fontSize="xs" color="gray.500">
                                {new Date(timestamp).toLocaleTimeString()}
                            </Text>
                        </HStack>

                        {/* Response Content */}
                        <Box w="100%">
                            <ResponseRenderer
                                content={content}
                                typeChecks={typeChecks}
                                agentType={agentType}
                                transactionData={transactionData}
                                metadata={metadata}
                                multiStepState={multiStepState}
                                chainId={chainId}
                                textColor={textColor}
                                isExecuting={isExecuting}
                                onExecute={(overrides?: any) => {
                                    if (typeChecks.isX402Automation) {
                                        handleX402Execution(overrides);
                                    } else if (typeof content === 'object' && content !== null &&
                                        ((content as any).flow_info || (content as any).type === 'swap_approval' || (content as any).type === 'multi_step_transaction')) {
                                        handleMultiStepTransaction(content);
                                    } else {
                                        handleExecuteTransaction();
                                    }
                                }}
                                onCancel={handleCancel}
                                onDone={reset}
                                onRetry={retry}
                                onActionClick={handleActionClick}
                            />

                            {/* Default text rendering (fallback) */}
                            {!typeChecks.isSwapConfirmation &&
                                !typeChecks.isDCAConfirmation &&
                                !typeChecks.isMultiStepTransaction &&
                                !typeChecks.isSwapTransaction &&
                                !typeChecks.isBrianTransaction &&
                                !typeChecks.isBridgeTransaction &&
                                !typeChecks.isTransferTransaction &&
                                !typeChecks.isBalanceResult &&
                                !typeChecks.isProtocolResearch &&
                                !typeChecks.isPortfolioDisabled &&
                                !typeChecks.isBridgePrivacyReady &&
                                !typeChecks.isCrossChainSuccess &&
                                !typeChecks.isX402Automation &&
                                agentType !== 'agno' &&
                                agentType !== 'portfolio' && (
                                    <Text
                                        fontSize="sm"
                                        color={textColor}
                                        whiteSpace="pre-wrap"
                                    >
                                        {formatLinks(
                                            getContentError(content) ||
                                            getContentMessage(content) ||
                                            (isStringContent(content) ? content : JSON.stringify(content))
                                        )}
                                    </Text>
                                )}
                        </Box>
                    </VStack>
                </HStack>
            </Box>

            {/* Portfolio Modal */}
            <PortfolioModal
                isOpen={isPortfolioModalOpen}
                onClose={onPortfolioModalClose}
                portfolioAnalysis={
                    typeof content === 'object' && content !== null && 'type' in content && (content as any).type === 'portfolio'
                        ? (content as any).analysis
                        : {}
                }
                metadata={metadata}
                onActionClick={handleActionClick}
            />
        </>
    );
};

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

// Services
import { ApiService } from '../services/apiService';
import { TransactionService } from '../services/transactionService';

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
                ? new TransactionService(walletClient, publicClient, chainId)
                : null,
        [walletClient, publicClient, chainId]
    );

    // Extract transaction data
    const transactionData = transaction || getTransactionFromContent(content);

    // Multi-step transaction hook
    const {
        isExecuting,
        userRejected,
        multiStepState,
        handleMultiStepTransaction,
        setUserRejected,
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
            const txService = new TransactionService(walletClient, publicClient, chainId);
            const result = await txService.executeTransaction(transactionData);

            toast({
                title: 'Transaction Sent',
                description: `Transaction hash: ${result.hash}`,
                status: 'success',
                duration: 5000,
                isClosable: true,
            });
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
    }, [transactionData, walletClient, publicClient, chainId, userRejected, toast, setUserRejected]);

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
                                onExecute={handleExecuteTransaction}
                                onCancel={handleCancel}
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
                                agentType !== 'agno' &&
                                agentType !== 'portfolio' && (
                                    <Text
                                        fontSize="sm"
                                        color={textColor}
                                        whiteSpace="pre-wrap"
                                        dangerouslySetInnerHTML={{
                                            __html: formatLinks(
                                                getContentError(content) ||
                                                getContentMessage(content) ||
                                                (isStringContent(content) ? content : JSON.stringify(content))
                                            ),
                                        }}
                                    />
                                )}
                        </Box>
                    </VStack>
                </HStack>
            </Box>

            {/* Portfolio Modal */}
            <PortfolioModal isOpen={isPortfolioModalOpen} onClose={onPortfolioModalClose} />
        </>
    );
};

/**
 * ResponseRenderer - Centralized response rendering logic
 * Extracted from CommandResponse.tsx following MODULAR and CLEAN principles
 */

import React from 'react';
import { Box, VStack, HStack, Text } from '@chakra-ui/react';
import { CheckCircleIcon } from '@chakra-ui/icons';
import { UnifiedConfirmation } from '../UnifiedConfirmation';
import { TransactionHandler } from '../Transaction/TransactionHandler';
import { MultiStepTransactionDisplay } from '../Transaction/MultiStepTransactionDisplay';
import { BalanceResult } from '../BalanceResult';
import { ProtocolResearchResult } from '../ProtocolResearchResult';
import { CrossChainResult } from '../CrossChain/CrossChainResult';
import { PortfolioEnablePrompt } from '../Portfolio/PortfolioEnablePrompt';
import { GMPTransactionCard } from '../GMP/GMPTransactionCard';
import { EnhancedPortfolioSummary } from '../EnhancedPortfolioSummary';
import { PrivacyBridgeGuidance } from '../Privacy/PrivacyBridgeGuidance';
import { BridgeStatusTracker } from '../Bridge/BridgeStatusTracker';
import { PostBridgeModal } from '../Bridge/PostBridgeModal';
import type { ResponseContent, ResponseMetadata, TransactionData, BridgeStatusContent, PostBridgeSuccessContent } from '../../types/responses';
import type { AgentType } from '../../utils/agentInfo';
import type { ResponseTypeChecks } from '../../utils/responseTypeDetection';
import {
    isObjectContent,
    getContentMessage,
    getContentAnalysis,
    isStringContent,
    isBridgePrivacyReadyContent,
    isBridgeStatusContent,
    isPostBridgeSuccessContent,
} from '../../utils/contentTypeGuards';
import { useAccount } from 'wagmi';

interface ResponseRendererProps {
    content: ResponseContent;
    typeChecks: ResponseTypeChecks;
    agentType?: AgentType;
    transactionData?: TransactionData;
    metadata?: ResponseMetadata;
    multiStepState: any;
    chainId: number;
    textColor: string;
    isExecuting: boolean;
    onExecute: () => void;
    onCancel: () => void;
    onActionClick?: (action: any) => void;
}

export const ResponseRenderer: React.FC<ResponseRendererProps> = ({
    content,
    typeChecks,
    agentType,
    transactionData,
    metadata,
    multiStepState,
    chainId,
    textColor,
    isExecuting,
    onExecute,
    onCancel,
    onActionClick,
}) => {
    const { address } = useAccount();
    const [isPostBridgeModalOpen, setIsPostBridgeModalOpen] = React.useState(false);

    const {
        isSwapConfirmation,
        isDCAConfirmation,
        isMultiStepTransaction,
        isSwapTransaction,
        isBrianTransaction,
        isBridgeTransaction,
        isTransferTransaction,
        isBalanceResult,
        isProtocolResearch,
        isPortfolioDisabled,
        isBridgePrivacyReady,
        isCrossChainSuccess,
    } = typeChecks;

    // Auto-open post-bridge modal when success content arrives
    React.useEffect(() => {
        if (isPostBridgeSuccessContent(content)) {
            setIsPostBridgeModalOpen(true);
        }
    }, [content]);

    // Swap Confirmation
    if (isSwapConfirmation) {
        return (
            <UnifiedConfirmation
                agentType="swap"
                content={{
                    message: getContentMessage(content) || 'Ready to execute swap',
                    type: 'swap_confirmation',
                    details: isObjectContent(content) ? (content as any).details || {} : {},
                }}
                transaction={transactionData}
                metadata={metadata}
                onExecute={onExecute}
                onCancel={onCancel}
                isLoading={isExecuting}
            />
        );
    }

    // DCA Confirmation
    if (isDCAConfirmation) {
        return (
            <UnifiedConfirmation
                agentType="swap"
                content={{
                    message: getContentMessage(content) || 'Ready to set up DCA',
                    type: 'dca_confirmation',
                    details: isObjectContent(content) ? (content as any).details || {} : {},
                }}
                transaction={transactionData}
                metadata={metadata}
                onExecute={onExecute}
                onCancel={onCancel}
                isLoading={isExecuting}
            />
        );
    }

    // Multi-Step Transaction
    if (isMultiStepTransaction) {
        return (
            <MultiStepTransactionDisplay
                content={content}
                multiStepState={multiStepState}
                chainId={chainId}
                textColor={textColor}
            />
        );
    }

    // Swap Transaction
    if (isSwapTransaction) {
        return (
            <TransactionHandler
                agentType="swap"
                content={content}
                transactionData={transactionData}
                metadata={metadata}
                isExecuting={isExecuting}
                onExecute={onExecute}
                onCancel={onCancel}
            />
        );
    }

    // Brian Transaction
    if (isBrianTransaction) {
        return (
            <TransactionHandler
                agentType="brian"
                content={content}
                transactionData={transactionData}
                metadata={metadata}
                isExecuting={isExecuting}
                onExecute={onExecute}
                onCancel={onCancel}
            />
        );
    }

    // Bridge Transaction
    if (isBridgeTransaction) {
        return (
            <TransactionHandler
                agentType="bridge"
                content={content}
                transactionData={transactionData}
                metadata={metadata}
                isExecuting={isExecuting}
                onExecute={onExecute}
                onCancel={onCancel}
            />
        );
    }

    // Transfer Transaction
    if (isTransferTransaction) {
        return (
            <TransactionHandler
                agentType="transfer"
                content={content}
                transactionData={transactionData}
                metadata={metadata}
                isExecuting={isExecuting}
                onExecute={onExecute}
                onCancel={onCancel}
            />
        );
    }

    // Brian Confirmation (special case)
    if (isObjectContent(content) && (content as any).type === 'brian_confirmation') {
        const brianContent = content as any;
        return (
            <UnifiedConfirmation
                agentType="bridge"
                content={{
                    message: getContentMessage(content) || 'Ready to execute bridge transaction',
                    type: 'brian_confirmation',
                    details: {
                        token: brianContent.data?.token,
                        amount: brianContent.data?.amount,
                        source_chain: brianContent.data?.from_chain?.name,
                        destination_chain: brianContent.data?.to_chain?.name,
                    },
                }}
                transaction={
                    brianContent.data?.tx_steps
                        ? {
                            to: brianContent.data.tx_steps[0]?.to,
                            data: brianContent.data.tx_steps[0]?.data,
                            value: brianContent.data.tx_steps[0]?.value || '0',
                            chain_id: brianContent.data.from_chain?.id,
                            gas_limit: brianContent.data.tx_steps[0]?.gasLimit || '500000',
                        }
                        : undefined
                }
                metadata={{
                    token_symbol: brianContent.data?.token,
                    amount: brianContent.data?.amount,
                    from_chain_id: brianContent.data?.from_chain?.id,
                    to_chain_id: brianContent.data?.to_chain?.id,
                    from_chain_name: brianContent.data?.from_chain?.name,
                    to_chain_name: brianContent.data?.to_chain?.name,
                }}
                onExecute={onExecute}
                onCancel={onCancel}
                isLoading={isExecuting}
            />
        );
    }

    // Balance Result
    if (isBalanceResult) {
        return <BalanceResult content={content} />;
    }

    // Protocol Research
    if (isProtocolResearch) {
        return <ProtocolResearchResult content={content} />;
    }

    // Portfolio Disabled
    if (isPortfolioDisabled) {
        return (
            <PortfolioEnablePrompt
                suggestion={
                    typeof content === 'object' && content !== null && 'suggestion' in content
                        ? (content as any).suggestion
                        : {
                            title: 'Enable Portfolio Analysis',
                            description: 'Get detailed insights about your holdings',
                            features: ['Holdings analysis', 'Risk assessment', 'Optimization tips'],
                            warning: 'Analysis takes 10-30 seconds',
                        }
                }
                onEnable={() => {
                    if (onActionClick) {
                        onActionClick({
                            type: 'enable_portfolio',
                            message: 'Portfolio analysis enabled',
                        });
                    }
                }}
            />
        );
    }

    // Privacy Bridge
    if (isBridgePrivacyReady && isBridgePrivacyReadyContent(content)) {
        return (
            <VStack spacing={4} mt={4} width="100%">
                <GMPTransactionCard
                    transaction={{
                        id: `privacy-${Date.now()}`,
                        type: 'bridge_to_privacy',
                        sourceChain: content.from_chain,
                        destChain: content.to_chain,
                        status: 'pending',
                        steps:
                            content.steps?.map((step: any, idx: number) => ({
                                id: `step-${idx}`,
                                title: step.description || step.type,
                                description: step.description || '',
                                status: 'pending' as const,
                                estimatedTime: idx === 0 ? content.estimated_time : undefined,
                            })) || [],
                        createdAt: new Date(),
                        metadata: {
                            amount: content.amount,
                            token: content.token,
                            protocol: content.protocol,
                        },
                        updatedAt: new Date(),
                        recipient: address || '',
                    }}
                    variant="privacy"
                    privacyLevel={content.privacy_level}
                    onExecute={onExecute}
                    onCancel={onCancel}
                    isExecuting={isExecuting}
                />
                <PrivacyBridgeGuidance content={content} isCompact={false} />
            </VStack>
        );
    }

    // Bridge Status
    if (isBridgeStatusContent(content)) {
        return (
            <BridgeStatusTracker
                status={content as BridgeStatusContent}
                isLoading={isExecuting}
            />
        );
    }

    // Post-Bridge Success
    if (isPostBridgeSuccessContent(content)) {
        return (
            <>
                <Box p={4} borderRadius="lg" bg="green.50" borderLeft="4px solid" borderColor="green.500">
                    <HStack spacing={2}>
                        <CheckCircleIcon color="green.500" w={5} h={5} />
                        <VStack align="start" spacing={0}>
                            <Text fontWeight="bold" color="green.700">
                                {content.amount} {content.token} successfully bridged to {content.to_chain}
                            </Text>
                            <Text fontSize="sm" color="green.600">
                                {content.estimated_arrival_time ? `Arriving in ${content.estimated_arrival_time}` : 'Processing'}
                            </Text>
                        </VStack>
                    </HStack>
                </Box>
                <PostBridgeModal
                    isOpen={isPostBridgeModalOpen}
                    content={content as PostBridgeSuccessContent}
                    onClose={() => setIsPostBridgeModalOpen(false)}
                />
            </>
        );
    }

    // Cross-Chain Success
    if (isCrossChainSuccess) {
        return (
            <CrossChainResult
                content={typeof content === 'object' ? content : { type: 'cross_chain_success' }}
                metadata={metadata as any}
            />
        );
    }

    // Portfolio/Agno Agent
    if (agentType === 'agno' || agentType === 'portfolio') {
        return (
            <VStack spacing={4} align="stretch" w="100%">
                <EnhancedPortfolioSummary
                    response={{
                        analysis: getContentAnalysis(content),
                        summary:
                            getContentAnalysis(content)?.summary ||
                            (isStringContent(content) ? content : undefined),
                        fullAnalysis: getContentAnalysis(content)?.fullAnalysis,
                        content: isStringContent(content) ? content : JSON.stringify(content),
                    }}
                    onActionClick={onActionClick}
                />
            </VStack>
        );
    }

    // Default: return null (parent will handle default rendering)
    return null;
};

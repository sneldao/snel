/**
 * Response type detection utilities
 * Extracted from CommandResponse.tsx for better organization
 */

import type { ResponseContent } from '../../types/responses';
import type { AgentType } from '../../utils/agentInfo';
import {
    isTransferContent,
    isBalanceResultContent,
    isProtocolResearchContent,
    isCrossChainSuccessContent,
    isPortfolioDisabledContent,
    isBridgePrivacyReadyContent,
    getContentAxelarPowered,
    hasMessageProperty,
    hasBridgeKeywords,
} from '../../utils/contentTypeGuards';

export interface ResponseTypeChecks {
    isSwapConfirmation: boolean;
    isDCAConfirmation: boolean;
    isSwapTransaction: boolean;
    isDCASuccess: boolean;
    isMultiStepTransaction: boolean;
    isBrianTransaction: boolean;
    isBridgeTransaction: boolean;
    isBridgeMultiStep: boolean;
    isTransferTransaction: boolean;
    isBalanceResult: boolean;
    isProtocolResearch: boolean;
    isCrossChainSuccess: boolean;
    isPortfolioDisabled: boolean;
    isBridgePrivacyReady: boolean;
}

interface DetectResponseTypesProps {
    content: ResponseContent;
    agentType?: AgentType;
    awaitingConfirmation?: boolean;
    transactionData?: any;
}

export const detectResponseTypes = ({
    content,
    agentType,
    awaitingConfirmation = false,
    transactionData,
}: DetectResponseTypesProps): ResponseTypeChecks => {
    const isSwapConfirmation =
        typeof content === 'object' &&
        ((content as any)?.type === 'swap_confirmation' ||
            (content as any)?.type === 'swap_ready');

    const isDCAConfirmation =
        typeof content === 'object' && (content as any)?.type === 'dca_confirmation';

    const isSwapTransaction =
        (typeof content === 'object' && (content as any)?.type === 'swap_transaction') ||
        (typeof content === 'object' &&
            (content as any)?.type === 'swap_ready' &&
            agentType === 'swap') ||
        (agentType === 'swap' && transactionData);

    const isDCASuccess =
        typeof content === 'object' &&
        ((content as any)?.type === 'dca_success' ||
            (content as any)?.type === 'dca_order_created');

    const isMultiStepTransaction =
        typeof content === 'object' && (content as any)?.type === 'multi_step_transaction';

    const isBrianTransaction =
        (typeof content === 'object' &&
            (content as any)?.type === 'transaction' &&
            agentType === 'brian') ||
        (agentType === 'brian' && transactionData);

    const isBridgeTransaction =
        (typeof content === 'object' &&
            (content as any)?.type === 'bridge_ready' &&
            agentType === 'bridge' &&
            !awaitingConfirmation) ||
        (typeof content === 'object' &&
            (content as any)?.type === 'bridge_transaction' &&
            agentType === 'bridge' &&
            !awaitingConfirmation) ||
        (agentType === 'bridge' && transactionData && !awaitingConfirmation) ||
        (typeof content === 'object' &&
            (content as any)?.requires_transaction &&
            agentType === 'bridge' &&
            !awaitingConfirmation);

    const isBridgeMultiStep =
        (agentType === 'bridge' && awaitingConfirmation && transactionData) ||
        (awaitingConfirmation && transactionData && hasBridgeKeywords(content)) ||
        (awaitingConfirmation &&
            transactionData &&
            typeof transactionData === 'object' &&
            transactionData.data &&
            transactionData.data.startsWith('0x095ea7b3')); // approve function signature

    const isTransferTransaction =
        (isTransferContent(content) && agentType === 'transfer') ||
        (agentType === 'transfer' && transactionData);

    const isBalanceResult = isBalanceResultContent(content) && agentType === 'balance';

    const isProtocolResearch =
        isProtocolResearchContent(content) && agentType === 'protocol_research';

    const isCrossChainSuccess =
        isCrossChainSuccessContent(content) && getContentAxelarPowered(content);

    const isPortfolioDisabled = isPortfolioDisabledContent(content);

    const isBridgePrivacyReady = isBridgePrivacyReadyContent(content);

    return {
        isSwapConfirmation,
        isDCAConfirmation,
        isSwapTransaction,
        isDCASuccess,
        isMultiStepTransaction,
        isBrianTransaction,
        isBridgeTransaction,
        isBridgeMultiStep,
        isTransferTransaction,
        isBalanceResult,
        isProtocolResearch,
        isCrossChainSuccess,
        isPortfolioDisabled,
        isBridgePrivacyReady,
    };
};

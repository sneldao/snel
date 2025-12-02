/**
 * Transaction execution utilities
 * Extracted from CommandResponse.tsx for better separation of concerns
 */

import type { TransactionData } from '../../types/responses';

/**
 * Extract transaction data from response content
 */
export const getTransactionFromContent = (
    content: any
): TransactionData | undefined => {
    if (typeof content === 'object' && content !== null) {
        // Check if content has transaction property
        if ('transaction' in content) {
            return content.transaction;
        }
        // Check if content has nested content with transaction
        if (
            'content' in content &&
            typeof content.content === 'object' &&
            content.content !== null &&
            'transaction' in content.content
        ) {
            return content.content.transaction;
        }
    }
    return undefined;
};

/**
 * Check if transaction should be auto-executed
 */
export const shouldAutoExecuteTransaction = (
    isBrianTransaction: boolean,
    isBridgeTransaction: boolean,
    isTransferTransaction: boolean,
    isSwapTransaction: boolean,
    contentType: string | undefined,
    transactionData: any,
    isExecuting: boolean,
    txResponse: any,
    isMultiStepTransaction: boolean
): boolean => {
    return (
        (isBrianTransaction ||
            isBridgeTransaction ||
            isTransferTransaction ||
            isSwapTransaction ||
            contentType === 'swap_quotes') &&
        !!transactionData &&
        !isExecuting &&
        !txResponse &&
        !isMultiStepTransaction
    );
};

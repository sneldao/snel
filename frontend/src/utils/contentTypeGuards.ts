// Type guards and utilities for ResponseContent union type
import {
  ResponseContent,
  BalanceContent,
  SwapContent,
  BridgeContent,
  PortfolioContent,
  ErrorContent,
  TransactionContent,
  TransferContent,
  BalanceResultContent,
  ProtocolResearchContent,
  CrossChainSuccessContent,
  PortfolioDisabledContent,
  BridgeReadyContent,
  SwapQuotesContent,
  DCAOrderCreatedContent,
  BridgePrivacyReadyContent,
  BridgeStatusContent,
  PostBridgeSuccessContent
} from '../types/responses';

// Type guard functions
export const isStringContent = (content: ResponseContent): content is string => {
  return typeof content === 'string';
};

export const isBalanceContent = (content: ResponseContent): content is BalanceContent => {
  return typeof content === 'object' && content !== null && 'type' in content && content.type === 'balance';
};

export const isSwapContent = (content: ResponseContent): content is SwapContent => {
  return typeof content === 'object' && content !== null && 'type' in content && content.type === 'swap';
};

export const isBridgeContent = (content: ResponseContent): content is BridgeContent => {
  return typeof content === 'object' && content !== null && 'type' in content && content.type === 'bridge';
};

export const isPortfolioContent = (content: ResponseContent): content is PortfolioContent => {
  return typeof content === 'object' && content !== null && 'type' in content && content.type === 'portfolio';
};

export const isErrorContent = (content: ResponseContent): content is ErrorContent => {
  return typeof content === 'object' && content !== null && 'type' in content && content.type === 'error';
};

export const isTransactionContent = (content: ResponseContent): content is TransactionContent => {
  return typeof content === 'object' && content !== null && 'type' in content && content.type === 'transaction';
};

export const isTransferContent = (content: ResponseContent): content is TransferContent => {
  return typeof content === 'object' && content !== null && 'type' in content &&
    (content.type === 'transfer_confirmation' || content.type === 'transfer_ready');
};

export const isBalanceResultContent = (content: ResponseContent): content is BalanceResultContent => {
  return typeof content === 'object' && content !== null && 'type' in content && content.type === 'balance_result';
};

export const isProtocolResearchContent = (content: ResponseContent): content is ProtocolResearchContent => {
  return typeof content === 'object' && content !== null && 'type' in content && content.type === 'protocol_research_result';
};

export const isCrossChainSuccessContent = (content: ResponseContent): content is CrossChainSuccessContent => {
  return typeof content === 'object' && content !== null && 'type' in content && content.type === 'cross_chain_success';
};

export const isPortfolioDisabledContent = (content: ResponseContent): content is PortfolioDisabledContent => {
  return typeof content === 'object' && content !== null && 'type' in content && content.type === 'portfolio_disabled';
};

export const isBridgeReadyContent = (content: ResponseContent): content is BridgeReadyContent => {
  return typeof content === 'object' && content !== null && 'type' in content && content.type === 'bridge_ready';
};

export const isSwapQuotesContent = (content: ResponseContent): content is SwapQuotesContent => {
  return typeof content === 'object' && content !== null && 'type' in content && content.type === 'swap_quotes';
};

export const isDCAOrderCreatedContent = (content: ResponseContent): content is DCAOrderCreatedContent => {
  return typeof content === 'object' && content !== null && 'type' in content && content.type === 'dca_order_created';
};

export const isBridgePrivacyReadyContent = (content: ResponseContent): content is BridgePrivacyReadyContent => {
  return typeof content === 'object' && content !== null && 'type' in content && content.type === 'bridge_privacy_ready';
};

export const isBridgeStatusContent = (content: ResponseContent): content is BridgeStatusContent => {
  return typeof content === 'object' && content !== null && 'type' in content && content.type === 'bridge_status';
};

export const isPostBridgeSuccessContent = (content: ResponseContent): content is PostBridgeSuccessContent => {
  return typeof content === 'object' && content !== null && 'type' in content && content.type === 'post_bridge_success';
};

export const isObjectContent = (content: ResponseContent): content is Exclude<ResponseContent, string> => {
  return typeof content === 'object' && content !== null;
};

// Safe property accessors
export const getContentType = (content: ResponseContent): string | undefined => {
  if (isObjectContent(content)) {
    return 'type' in content ? content.type : undefined;
  }
  return undefined;
};

export const getContentMessage = (content: ResponseContent): string | undefined => {
  if (isObjectContent(content) && 'message' in content) {
    return typeof content.message === 'string' ? content.message : undefined;
  }
  return undefined;
};

export const getContentText = (content: ResponseContent): string | undefined => {
  if (isObjectContent(content) && 'text' in content) {
    return typeof content.text === 'string' ? content.text : undefined;
  }
  return undefined;
};

export const getContentResponse = (content: ResponseContent): string | undefined => {
  if (isObjectContent(content) && 'response' in content) {
    return typeof content.response === 'string' ? content.response : undefined;
  }
  return undefined;
};

export const getContentError = (content: ResponseContent): string | undefined => {
  if (isObjectContent(content) && 'error' in content) {
    return typeof content.error === 'string' ? content.error : undefined;
  }
  return undefined;
};

export const getContentData = (content: ResponseContent): any => {
  if (isObjectContent(content) && 'data' in content) {
    return content.data;
  }
  return undefined;
};

export const getContentAnalysis = (content: ResponseContent): any => {
  if (isObjectContent(content) && 'analysis' in content) {
    return content.analysis;
  }
  return undefined;
};

export const getContentSuggestion = (content: ResponseContent): any => {
  if (isObjectContent(content) && 'suggestion' in content) {
    return content.suggestion;
  }
  return undefined;
};

export const getContentAxelarPowered = (content: ResponseContent): boolean | undefined => {
  if (isObjectContent(content) && 'axelar_powered' in content) {
    return typeof content.axelar_powered === 'boolean' ? content.axelar_powered : undefined;
  }
  return undefined;
};

// Content type detection for specific use cases
export const isConfirmationType = (content: ResponseContent, type: string): boolean => {
  if (isObjectContent(content)) {
    return 'type' in content && content.type === type;
  }
  return false;
};

export const hasMessageProperty = (content: ResponseContent): boolean => {
  return isObjectContent(content) && 'message' in content && typeof content.message === 'string';
};

export const hasBridgeKeywords = (content: ResponseContent): boolean => {
  const message = getContentMessage(content);
  if (message) {
    return message.toLowerCase().includes('bridge') || message.toLowerCase().includes('axelar');
  }
  return false;
};

// Transaction data extraction
export const getTransactionData = (content: ResponseContent): any => {
  if (isObjectContent(content)) {
    if ('transaction' in content) {
      return content.transaction;
    }
    if ('data' in content && typeof content.data === 'object' && content.data !== null && 'transaction' in content.data) {
      return (content.data as any).transaction;
    }
  }
  return undefined;
};

// Quote data extraction
export const getQuotes = (content: ResponseContent): any[] => {
  if (isObjectContent(content) && 'quotes' in content && Array.isArray(content.quotes)) {
    return content.quotes;
  }
  return [];
};

// Flow info extraction
export const getFlowInfo = (content: ResponseContent): any => {
  if (isObjectContent(content) && 'flow_info' in content) {
    return content.flow_info;
  }
  return undefined;
};
export type TransactionData = {
  to: string;
  data?: string;
  value: string;
  chain_id: number;
  method?: string;
  gas_limit?: string;
  gas_price?: string;
  max_fee_per_gas?: string;
  max_priority_fee_per_gas?: string;
  error?: string;
  error_code?: string;
  needs_approval?: boolean;
  token_to_approve?: string;
  spender?: string;
  pending_command?: string;
  skip_approval?: boolean;
  metadata?: {
    token_in_address?: string;
    token_in_symbol?: string;
    token_in_name?: string;
    token_in_verified?: boolean;
    token_in_source?: string;
    token_out_address?: string;
    token_out_symbol?: string;
    token_out_name?: string;
    token_out_verified?: boolean;
    token_out_source?: string;
  };
  from_address?: string;
};

// Structured content types for different response types
export interface BalanceContent {
  type: 'balance';
  tokens: TokenBalance[];
  totalValue: string;
  chainId: number;
}

export interface SwapContent {
  type: 'swap';
  quotes: SwapQuote[];
  selectedQuote?: SwapQuote;
  tokenIn: TokenInfo;
  tokenOut: TokenInfo;
  amount: string;
}

export interface BridgeContent {
  type: 'bridge';
  sourceChain: number;
  destinationChain: number;
  token: TokenInfo;
  amount: string;
  estimatedTime: string;
  fees: BridgeFees;
}

export interface PortfolioContent {
  type: 'portfolio';
  analysis: PortfolioAnalysis;
  tokens: TokenBalance[];
  totalValue: string;
  performance: PerformanceMetrics;
}

export interface ErrorContent {
  type: 'error';
  message: string;
  code?: string;
  details?: Record<string, unknown>;
}

export interface TransactionContent {
  type: 'transaction';
  transactionData: TransactionData;
  status: 'pending' | 'confirmed' | 'failed';
  hash?: string;
}

export interface TransferContent {
  type: 'transfer_confirmation' | 'transfer_ready';
  token: TokenInfo;
  amount: string;
  to: string;
  chainId: number;
}

export interface BalanceResultContent {
  type: 'balance_result';
  tokens: TokenBalance[];
  totalValue: string;
  chainId: number;
}

export interface ProtocolResearchContent {
  type: 'protocol_research_result';
  protocol: string;
  analysis: Record<string, unknown>;
  recommendations: string[];
}

export interface CrossChainSuccessContent {
  type: 'cross_chain_success';
  transactionHash: string;
  sourceChain: number;
  destinationChain: number;
  axelar_powered: boolean;
}

export interface PortfolioDisabledContent {
  type: 'portfolio_disabled';
  suggestion: {
    title: string;
    description: string;
    features: string[];
    warning: string;
  };
}

export interface BridgeReadyContent {
  type: 'bridge_ready';
  sourceChain: number;
  destinationChain: number;
  token: TokenInfo;
  amount: string;
  estimatedTime: string;
  fees: BridgeFees;
}

export interface SwapQuotesContent {
  type: 'swap_quotes';
  quotes: SwapQuote[];
  tokenIn: TokenInfo;
  tokenOut: TokenInfo;
  amount: string;
}

export interface DCAOrderCreatedContent {
  type: 'dca_order_created';
  order_id: string;
  frequency: string;
  duration: string;
  amount: string;
  token_in: TokenInfo;
  token_out: TokenInfo;
}

export type ResponseContent =
  | string
  | BalanceContent
  | SwapContent
  | BridgeContent
  | PortfolioContent
  | ErrorContent
  | TransactionContent
  | TransferContent
  | BalanceResultContent
  | ProtocolResearchContent
  | CrossChainSuccessContent
  | PortfolioDisabledContent
  | BridgeReadyContent
  | SwapQuotesContent
  | DCAOrderCreatedContent;

// Supporting interfaces
export interface TokenBalance {
  address: string;
  symbol: string;
  name: string;
  balance: string;
  value: string;
  change24h: string;
  verified: boolean;
  decimals: number;
}

export interface TokenInfo {
  address: string;
  symbol: string;
  name: string;
  decimals: number;
  verified: boolean;
  logoURI?: string;
}

export interface SwapQuote {
  to: string;
  data: string;
  value: string;
  gas: string;
  buyAmount: string;
  sellAmount: string;
  protocol: string;
  aggregator: string;
  priceImpact: string;
  estimatedGas: string;
}

export interface BridgeFees {
  networkFee: string;
  protocolFee: string;
  totalFee: string;
}

export interface PortfolioAnalysis {
  totalValue: string;
  change24h: string;
  topHoldings: TokenBalance[];
  riskScore: number;
  diversificationScore: number;
}

export interface PerformanceMetrics {
  totalReturn: string;
  dailyChange: string;
  weeklyChange: string;
  monthlyChange: string;
}

export interface ResponseMetadata {
  executionTime?: number;
  chainId?: number;
  blockNumber?: number;
  gasUsed?: string;
  transactionHash?: string;
  [key: string]: unknown;
}

export type Response = {
  content: ResponseContent;
  timestamp: string;
  isCommand: boolean;
  pendingCommand?: string;
  awaitingConfirmation?: boolean;
  confirmation_type?: "token_confirmation" | "quote_selection";
  status?: "pending" | "processing" | "success" | "error";
  agentType?: "default" | "swap" | "dca" | "brian" | "bridge" | "transfer" | "agno" | "balance" | "protocol_research" | "portfolio" | "settings";
  metadata?: ResponseMetadata;
  requires_selection?: boolean;
  all_quotes?: SwapQuote[];
  selected_quote?: SwapQuote;
  transaction?: TransactionData;
  summary?: string;
  fullAnalysis?: string;
};

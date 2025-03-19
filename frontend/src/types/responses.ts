export type TransactionData = {
  to: string;
  data: string;
  value: string;
  chainId: number;
  method: string;
  gasLimit: string;
  gasPrice?: string;
  maxFeePerGas?: string;
  maxPriorityFeePerGas?: string;
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
  gas_limit?: string;
  gas_price?: string;
  max_fee_per_gas?: string;
  max_priority_fee_per_gas?: string;
};

export type Response = {
  content: string | any;
  timestamp: string;
  isCommand: boolean;
  pendingCommand?: string;
  awaitingConfirmation?: boolean;
  confirmation_type?: "token_confirmation" | "quote_selection";
  status?: "pending" | "processing" | "success" | "error";
  agentType?: "default" | "swap" | "dca" | "brian";
  metadata?: any;
  requires_selection?: boolean;
  all_quotes?: any[];
  selected_quote?: {
    to: string;
    data: string;
    value: string;
    gas: string;
    buy_amount: string;
    sell_amount: string;
    protocol: string;
    aggregator: string;
  };
  transaction?: TransactionData;
};

import React from "react";
import { UnifiedConfirmation } from "../UnifiedConfirmation";

interface TransactionHandlerProps {
  agentType: string;
  content: any;
  transactionData: any;
  metadata: any;
  isExecuting: boolean;
  onExecute: () => void;
  onCancel: () => void;
}

export const TransactionHandler: React.FC<TransactionHandlerProps> = ({
  agentType,
  content,
  transactionData,
  metadata,
  isExecuting,
  onExecute,
  onCancel,
}) => {
  const getTransactionType = () => {
    if (agentType === "swap") return "swap_transaction";
    if (agentType === "brian") return "transaction";
    if (agentType === "bridge") return "bridge_transaction";
    if (agentType === "transfer") return "transfer_transaction";
    return "transaction";
  };

  const getTransactionMessage = () => {
    if (typeof content === "object" && content.message) {
      return content.message;
    }

    switch (agentType) {
      case "swap": return "Ready to execute swap transaction";
      case "brian": return "Ready to execute transaction";
      case "bridge": return "Ready to execute bridge transaction";
      case "transfer": return "Ready to execute transfer transaction";
      default: return "Ready to execute transaction";
    }
  };

  const getTransactionDetails = () => {
    if (agentType === "bridge") {
      return {
        token: typeof content === "object" ? content.token : undefined,
        amount: typeof content === "object" ? content.amount : undefined,
        source_chain: typeof content === "object" ? content.from_chain : undefined,
        destination_chain: typeof content === "object" ? content.to_chain : undefined,
        protocol: typeof content === "object" ? content.protocol : undefined,
        ...(typeof content === "object" ? content.details || {} : {}),
      };
    }

    if (agentType === "transfer" && typeof content === "object" && content.details) {
      return {
        token: content.details.token,
        amount: content.details.amount,
        destination: content.details.destination,
        resolved_address: content.details.resolved_address,
        chain: content.details.chain,
        ...content.details,
      };
    }

    return typeof content === "object" ? content.details || {} : {};
  };

  const getTransactionMetadata = () => {
    if (agentType === "bridge") {
      return {
        ...metadata,
        token_symbol: typeof content === "object" ? content.token : undefined,
        amount: typeof content === "object" ? content.amount : undefined,
        from_chain_name: typeof content === "object" ? content.from_chain : undefined,
        to_chain_name: typeof content === "object" ? content.to_chain : undefined,
        protocol: typeof content === "object" ? content.protocol : undefined,
        estimated_time: typeof content === "object" ? content.estimated_time : undefined,
      };
    }

    if (agentType === "transfer") {
      return {
        ...metadata,
        token_symbol: typeof content === "object" && content.details ? content.details.token : undefined,
        amount: typeof content === "object" && content.details ? content.details.amount : undefined,
        recipient: typeof content === "object" && content.details
          ? content.details.resolved_address || content.details.destination
          : undefined,
        chain_name: typeof content === "object" && content.details ? content.details.chain : undefined,
        estimated_gas: typeof content === "object" && content.details ? content.details.estimated_gas : undefined,
      };
    }

    return metadata;
  };

  return (
    <UnifiedConfirmation
      agentType={agentType as any}
      content={{
        ...(typeof content === "object" ? content : {}),
        message: getTransactionMessage(),
        type: getTransactionType(),
        details: getTransactionDetails(),
      }}
      transaction={transactionData}
      metadata={getTransactionMetadata()}
      onExecute={onExecute}
      onCancel={onCancel}
      isLoading={isExecuting}
    />
  );
};
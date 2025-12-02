/**
 * Unified Transaction Flow Service
 * Consolidates transactionService and multiStepTransactionService
 * Single source of truth for all transaction execution logic
 */

import { TransactionData } from "../types/responses";
import { BLOCK_EXPLORERS } from "../constants/chains";
import { type WalletClient, type PublicClient } from "viem";
import { withAsyncRecursionGuard } from "../utils/recursionGuard";
import { safeWalletOperation } from "../utils/walletErrorHandler";

// ============================================================================
// TYPES & INTERFACES
// ============================================================================

export interface TransactionStep {
  to: string;
  data: string;
  value: string;
  gasLimit: string;
  chainId?: number;
  description?: string;
  stepType?: "approval" | "swap" | "bridge" | "other";
}

export interface TransactionExecutionResult {
  hash: string;
  receipt: any;
  success: boolean;
}

export interface MultiStepTransactionResult {
  success: boolean;
  completedSteps: number;
  totalSteps: number;
  results: Array<{
    step: number;
    hash?: string;
    success: boolean;
    error?: string;
    stepType?: string;
  }>;
  finalHash?: string;
  error?: string;
}

// ============================================================================
// UTILITY FUNCTIONS
// ============================================================================

/**
 * Converts a decimal ETH value to wei (BigInt)
 * Handles both string and number inputs
 */
function parseEthToWei(value: string | number | undefined): bigint {
  if (!value || value === "0" || value === 0) {
    return BigInt(0);
  }

  const valueStr = String(value);

  // If it's already an integer string (no decimal point), convert directly
  if (!valueStr.includes(".")) {
    try {
      return BigInt(valueStr);
    } catch (error) {
      console.warn(`Failed to parse integer value "${valueStr}", defaulting to 0:`, error);
      return BigInt(0);
    }
  }

  try {
    const ethValue = parseFloat(valueStr);
    if (isNaN(ethValue)) {
      console.warn(`Invalid ETH value "${valueStr}", defaulting to 0`);
      return BigInt(0);
    }

    // Convert ETH to wei (1 ETH = 10^18 wei)
    // Use string manipulation to avoid floating point precision issues
    const [integerPart, decimalPart = ""] = valueStr.split(".");
    const paddedDecimal = decimalPart.padEnd(18, "0").slice(0, 18);
    const weiString = (integerPart || "0") + paddedDecimal;

    return BigInt(weiString);
  } catch (error) {
    console.warn(`Failed to parse ETH value "${valueStr}", defaulting to 0:`, error);
    return BigInt(0);
  }
}

// ============================================================================
// TRANSACTION FLOW SERVICE
// ============================================================================

export class TransactionFlowService {
  constructor(
    private walletClient: WalletClient,
    private publicClient: PublicClient,
    private chainId: number
  ) { }

  // ========== BLOCK EXPLORER ==========

  getBlockExplorerLink(hash: string): string {
    return `${BLOCK_EXPLORERS[this.chainId as keyof typeof BLOCK_EXPLORERS] ||
      BLOCK_EXPLORERS[8453]
      }${hash}`;
  }

  // ========== TRANSACTION TYPE DETECTION ==========

  /**
   * Detect transaction type based on function signature.
   * Single source of truth for transaction type detection.
   */
  detectTransactionType(txData: TransactionStep | TransactionData): "approval" | "swap" | "bridge" | "other" {
    if (!txData.data) {
      return "other";
    }

    const functionSig = txData.data.slice(0, 10).toLowerCase();

    // Approval: approve(address,uint256)
    if (functionSig === "0x095ea7b3") {
      return "approval";
    }

    // Swap functions: Uniswap V2/V3 and other DEX patterns
    const swapSelectors = ["0x38ed1739", "0x7ff36ab5", "0x18cbafe5", "0x8803dbee", "0x2213bc0b"];
    if (swapSelectors.includes(functionSig)) {
      return "swap";
    }

    // Bridge functions: Axelar and other bridge patterns
    const bridgeSelectors = ["0x26ef699d", "0x442a21e8", "0x12e4d8d1"];
    if (bridgeSelectors.includes(functionSig)) {
      return "bridge";
    }

    // Fallback: assume complex data is swap
    if (txData.data.length > 10) {
      return "swap";
    }

    return "other";
  }

  /**
   * Check if transaction is an approval.
   * @deprecated Use detectTransactionType() instead
   */
  isApprovalTransaction(txData: TransactionData): boolean {
    return this.detectTransactionType(txData) === "approval";
  }

  /**
   * Determine if operation requires multiple steps.
   */
  isMultiStepOperation(agentType: string, awaitingConfirmation: boolean): boolean {
    return (agentType === "bridge" || agentType === "swap") && awaitingConfirmation;
  }

  // ========== SINGLE TRANSACTION EXECUTION ==========

  /**
   * Execute a single transaction
   */
  async executeTransaction(txData: TransactionData): Promise<TransactionExecutionResult> {
    return safeWalletOperation(async () => {
      return withAsyncRecursionGuard(async () => {
        if (!this.walletClient) {
          throw new Error("Wallet not connected");
        }

        console.log("Original transaction data:", JSON.stringify(txData, null, 2));

        // Create abort controller for cancellations
        const abortController = new AbortController();

        // Validate transaction data
        if (!txData || typeof txData !== "object") {
          throw new Error("Invalid transaction data: transaction data is missing or invalid");
        }

        if ("error" in txData && txData.error) {
          throw new Error(txData.error);
        }

        if (!txData.to || !txData.data) {
          const errorMsg = `Invalid transaction data: missing required fields (to: ${txData.to}, data: ${txData.data})`;
          console.error("Invalid transaction data:", txData);
          throw new Error(errorMsg);
        }

        try {
          // Get account
          const [account] = await this.walletClient.getAddresses();
          if (!account) {
            throw new Error("No account available");
          }

          // Format transaction
          const gas = txData.gas_limit || "300000";
          const transaction = {
            account,
            chain: null,
            to: txData.to as `0x${string}`,
            data: txData.data as `0x${string}`,
            value: parseEthToWei(txData.value),
            chainId: txData.chain_id || this.chainId,
            gas: BigInt(gas),
          };

          // Ensure proper formatting
          if (transaction.value < BigInt(0)) {
            transaction.value = BigInt(0);
          }
          if (!transaction.to.startsWith("0x")) {
            transaction.to = `0x${transaction.to}` as `0x${string}`;
          }
          if (!transaction.data.startsWith("0x")) {
            transaction.data = `0x${transaction.data}` as `0x${string}`;
          }

          console.log(
            "Formatted transaction:",
            JSON.stringify(
              {
                ...transaction,
                value: transaction.value.toString(),
                gas: transaction.gas.toString(),
                account: transaction.account,
              },
              null,
              2
            )
          );

          // Verify chain ID
          if (transaction.chainId !== this.chainId) {
            console.warn(
              `Transaction chain ID (${transaction.chainId}) doesn't match current chain (${this.chainId}). Updating to current chain.`
            );
            transaction.chainId = this.chainId;
          }

          console.log("Sending transaction...");

          // Send transaction
          const sendTransactionPromise = this.walletClient.sendTransaction(transaction);

          const hash = await Promise.race([
            sendTransactionPromise,
            new Promise((_, reject) => {
              abortController.signal.addEventListener("abort", () => {
                reject(new Error("Transaction cancelled by user"));
              });
            }),
            new Promise((_, reject) => {
              setTimeout(() => {
                reject(new Error("Transaction timeout - please try again"));
              }, 60000);
            }),
          ]) as string;

          console.log("Transaction sent with hash:", hash);

          // Wait for receipt
          console.log("Waiting for transaction receipt...");
          const receipt = await this.publicClient.waitForTransactionReceipt({
            hash: hash as `0x${string}`,
          });

          if (!receipt) {
            throw new Error("Failed to get transaction receipt");
          }

          console.log("Transaction receipt received:", receipt);
          return {
            hash,
            receipt,
            success: Boolean(receipt.status),
          };
        } catch (error) {
          console.error("Transaction error:", error);

          if (error instanceof Error && this.isUserRejection(error)) {
            abortController.abort();
            console.log("User rejected transaction - aborting to prevent retries");
          }

          throw this.formatTransactionError(error);
        }
      }, `executeTransaction_${this.chainId}`)();
    }, `executeTransaction_${this.chainId}`);
  }

  // ========== MULTI-STEP TRANSACTION EXECUTION ==========

  /**
   * Execute multiple transaction steps in sequence
   */
  async executeMultiStepTransaction(
    steps: TransactionStep[],
    onStepComplete?: (step: number, result: any) => void,
    onStepStart?: (step: number, stepType: string) => void
  ): Promise<MultiStepTransactionResult> {
    const results: MultiStepTransactionResult["results"] = [];
    let completedSteps = 0;

    try {
      for (let i = 0; i < steps.length; i++) {
        const step = steps[i];
        const stepType = this.detectTransactionType(step);

        if (onStepStart) {
          onStepStart(i + 1, stepType);
        }

        try {
          // Add delay between steps
          if (i > 0) {
            await new Promise((resolve) => setTimeout(resolve, 2000));
          }

          // Convert step to transaction data
          const txData: TransactionData = {
            to: step.to,
            data: step.data,
            value: step.value,
            chain_id: step.chainId || this.chainId,
            method: stepType,
            gas_limit: step.gasLimit,
          };

          const result = await this.executeTransaction(txData);

          results.push({
            step: i + 1,
            hash: result.hash as string,
            success: result.success,
            stepType,
          });

          completedSteps++;

          if (onStepComplete) {
            onStepComplete(i + 1, result);
          }

          if (!result.success) {
            throw new Error(`Step ${i + 1} failed`);
          }
        } catch (error) {
          const errorMessage = error instanceof Error ? error.message : String(error);

          results.push({
            step: i + 1,
            success: false,
            error: errorMessage,
            stepType,
          });

          // Stop on user rejection or error
          if (errorMessage.includes("cancelled") || errorMessage.includes("rejected")) {
            return {
              success: false,
              completedSteps,
              totalSteps: steps.length,
              results,
              error: errorMessage,
            };
          }

          throw error;
        }
      }

      return {
        success: true,
        completedSteps,
        totalSteps: steps.length,
        results,
        finalHash: results[results.length - 1]?.hash,
      };
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : String(error);

      return {
        success: false,
        completedSteps,
        totalSteps: steps.length,
        results,
        error: errorMessage,
      };
    }
  }

  // ========== ERROR HANDLING ==========

  private isUserRejection(error: Error): boolean {
    const message = error.message.toLowerCase();
    return (
      message.includes("user rejected") ||
      message.includes("user denied") ||
      message.includes("rejected the request") ||
      message.includes("transaction signature") ||
      message.includes("user cancelled") ||
      message.includes("cancelled by user") ||
      message.includes("user canceled") ||
      message.includes("canceled by user") ||
      message.includes("transaction cancelled") ||
      message.includes("transaction canceled") ||
      message.includes("request rejected") ||
      message.includes("denied transaction") ||
      message.includes("signature denied") ||
      message.includes("user abort") ||
      message.includes("spam filter") ||
      message.includes("request blocked") ||
      message.includes("too many requests") ||
      message.includes("rate limit")
    );
  }

  private formatTransactionError(error: unknown): Error {
    if (!(error instanceof Error)) {
      return new Error(String(error));
    }

    if (this.isUserRejection(error)) {
      return new Error("Transaction cancelled");
    }

    if (error.message.includes("Cannot convert") && error.message.includes("to a BigInt")) {
      return new Error("Invalid transaction amount format. Please check the transaction value.");
    }

    if (error.message.includes("insufficient funds")) {
      return new Error("You don't have enough funds for this transaction");
    }

    if (error.message.includes("TRANSFER_FROM_FAILED")) {
      return new Error("Token transfer failed. Please check your balance and token approval.");
    }

    if (error.message.includes("gas required exceeds allowance")) {
      return new Error("Gas required exceeds your ETH balance");
    }

    if (error.message.includes("nonce too low")) {
      return new Error("Transaction nonce issue. Please try again.");
    }

    if (error.message.includes("execution reverted")) {
      const revertMatch = error.message.match(/execution reverted: (.*?)(?:")/);
      return new Error(
        revertMatch ? `Transaction reverted: ${revertMatch[1]}` : "Transaction reverted by the contract"
      );
    }

    let errorMessage = error.message;
    if (errorMessage.includes("Request Arguments:")) {
      errorMessage = errorMessage.split("Request Arguments:")[0].trim();
    } else {
      errorMessage = errorMessage.split("\n")[0];
      if (errorMessage.length > 100) {
        errorMessage = errorMessage.substring(0, 100) + "...";
      }
    }

    return new Error(errorMessage);
  }
}

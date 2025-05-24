import { TransactionData } from "../types/responses";
import { TransactionService } from "./transactionService";

export interface TransactionStep {
  to: string;
  data: string;
  value: string;
  gasLimit: string;
  chainId?: number;
  description?: string;
  stepType?: "approval" | "swap" | "bridge" | "other";
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

export class MultiStepTransactionService {
  constructor(private transactionService: TransactionService) {}

  /**
   * Detect if transaction data is an approval transaction
   */
  private isApprovalTransaction(txData: TransactionData): boolean {
    return txData.data.startsWith("0x095ea7b3"); // approve(address,uint256)
  }

  /**
   * Detect transaction type based on function signature
   */
  private detectTransactionType(txData: TransactionStep | TransactionData): "approval" | "swap" | "bridge" | "other" {
    const functionSig = txData.data.slice(0, 10);

    switch (functionSig) {
      case "0x095ea7b3": // approve(address,uint256)
        return "approval";
      case "0x38ed1739": // swapExactTokensForTokens
      case "0x7ff36ab5": // swapExactETHForTokens
      case "0x18cbafe5": // swapExactTokensForETH
      case "0x8803dbee": // swapTokensForExactTokens
        return "swap";
      default:
        // Check if it's a complex swap (many DEX aggregators use different signatures)
        if (txData.data.length > 10) {
          return "swap"; // Assume complex data is a swap
        }
        return "other";
    }
  }

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

        // Notify step start
        if (onStepStart) {
          onStepStart(i + 1, stepType);
        }

        try {
          // Add delay between steps to ensure proper sequencing
          if (i > 0) {
            await new Promise(resolve => setTimeout(resolve, 2000));
          }

          // Convert TransactionStep to TransactionData format
          const txData: TransactionData = {
            to: step.to,
            data: step.data,
            value: step.value,
            chainId: step.chainId || 1, // Default to mainnet if not specified
            method: stepType, // Use detected step type as method
            gasLimit: step.gasLimit,
          };

          const result = await this.transactionService.executeTransaction(txData);

          results.push({
            step: i + 1,
            hash: result.hash as string,
            success: result.success,
            stepType
          });

          completedSteps++;

          // Notify step completion
          if (onStepComplete) {
            onStepComplete(i + 1, result);
          }

          // If this step failed, stop execution
          if (!result.success) {
            throw new Error(`Step ${i + 1} failed`);
          }

        } catch (error) {
          const errorMessage = error instanceof Error ? error.message : String(error);

          results.push({
            step: i + 1,
            success: false,
            error: errorMessage,
            stepType
          });

          // If it's a user rejection, stop immediately
          if (errorMessage.includes("cancelled") || errorMessage.includes("rejected")) {
            throw new Error("Transaction cancelled by user");
          }

          // For other errors, also stop (could be made configurable)
          throw error;
        }
      }

      return {
        success: true,
        completedSteps,
        totalSteps: steps.length,
        results,
        finalHash: results[results.length - 1]?.hash as string
      };

    } catch (error) {
      return {
        success: false,
        completedSteps,
        totalSteps: steps.length,
        results,
        error: error instanceof Error ? error.message : String(error)
      };
    }
  }

  /**
   * Execute a single transaction but check if it needs to be followed by additional steps
   */
  async executeTransactionWithFollowUp(
    txData: TransactionData,
    onProgress?: (message: string, step?: number, total?: number) => void
  ): Promise<MultiStepTransactionResult> {
    // Check if this is an approval transaction
    if (this.isApprovalTransaction(txData)) {
      if (onProgress) {
        onProgress("Executing token approval...", 1, 2);
      }

      try {
        // Execute approval
        const approvalResult = await this.transactionService.executeTransaction(txData);

        if (!approvalResult.success) {
          return {
            success: false,
            completedSteps: 0,
            totalSteps: 2,
            results: [{
              step: 1,
              success: false,
              error: "Approval transaction failed",
              stepType: "approval"
            }],
            error: "Approval transaction failed"
          };
        }

        if (onProgress) {
          onProgress("Approval successful! Preparing swap transaction...", 2, 2);
        }

        // Check if there's a pending swap command to execute
        if (txData.pending_command) {
          // This would trigger the next step - in practice, this should be handled
          // by the backend returning the next transaction to execute
          if (onProgress) {
            onProgress("Waiting for swap transaction...", 2, 2);
          }
        }

        return {
          success: true,
          completedSteps: 1,
          totalSteps: 2,
          results: [{
            step: 1,
            hash: approvalResult.hash as string,
            success: true,
            stepType: "approval"
          }],
          finalHash: approvalResult.hash as string
        };

      } catch (error) {
        return {
          success: false,
          completedSteps: 0,
          totalSteps: 2,
          results: [{
            step: 1,
            success: false,
            error: error instanceof Error ? error.message : String(error),
            stepType: "approval"
          }],
          error: error instanceof Error ? error.message : String(error)
        };
      }
    }

    // For non-approval transactions, execute normally
    try {
      const result = await this.transactionService.executeTransaction(txData);
      const stepType = this.detectTransactionType(txData);

      return {
        success: result.success,
        completedSteps: result.success ? 1 : 0,
        totalSteps: 1,
        results: [{
          step: 1,
          hash: result.hash as string,
          success: result.success,
          stepType
        }],
        finalHash: result.hash as string
      };
    } catch (error) {
      return {
        success: false,
        completedSteps: 0,
        totalSteps: 1,
        results: [{
          step: 1,
          success: false,
          error: error instanceof Error ? error.message : String(error),
          stepType: this.detectTransactionType(txData)
        }],
        error: error instanceof Error ? error.message : String(error)
      };
    }
  }
}

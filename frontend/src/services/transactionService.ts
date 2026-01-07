import { TransactionData } from "../types/responses";
import { BLOCK_EXPLORERS } from "../constants/chains";
import { type WalletClient, type PublicClient } from "viem";
import { withAsyncRecursionGuard, recursionGuard } from "../utils/recursionGuard";
import { safeWalletOperation } from "../utils/walletErrorHandler";

/**
 * Converts a decimal ETH value to wei (BigInt)
 * Handles both string and number inputs
 * @param value - ETH value as string or number (e.g., "0.001", 0.001)
 * @returns BigInt value in wei
 */
function parseEthToWei(value: string | number | undefined): bigint {
  if (!value || value === "0" || value === 0) {
    return BigInt(0);
  }

  const valueStr = String(value);

  // If it's already an integer string (no decimal point), convert directly
  if (!valueStr.includes('.')) {
    try {
      return BigInt(valueStr);
    } catch (error) {
      console.warn(`Failed to parse integer value "${valueStr}", defaulting to 0:`, error);
      return BigInt(0);
    }
  }

  try {
    // Handle decimal values by converting to wei
    const ethValue = parseFloat(valueStr);
    if (isNaN(ethValue)) {
      console.warn(`Invalid ETH value "${valueStr}", defaulting to 0`);
      return BigInt(0);
    }

    // Convert ETH to wei (1 ETH = 10^18 wei)
    // Use string manipulation to avoid floating point precision issues
    const [integerPart, decimalPart = ''] = valueStr.split('.');
    const paddedDecimal = decimalPart.padEnd(18, '0').slice(0, 18);
    const weiString = (integerPart || '0') + paddedDecimal;

    return BigInt(weiString);
  } catch (error) {
    console.warn(`Failed to parse ETH value "${valueStr}", defaulting to 0:`, error);
    return BigInt(0);
  }
}

export class TransactionService {
  constructor(
    private walletClient: WalletClient,
    private publicClient: PublicClient,
    private chainId: number
  ) { }

  getBlockExplorerLink(hash: string): string {
    return `${BLOCK_EXPLORERS[this.chainId as keyof typeof BLOCK_EXPLORERS] ||
      BLOCK_EXPLORERS[8453]
      }${hash}`;
  }

  async executeTransaction(txData: TransactionData) {
    return safeWalletOperation(async () => {
      return withAsyncRecursionGuard(async () => {
        if (!this.walletClient) {
          throw new Error("Wallet not connected");
        }

        // Debug logging for transaction data
        console.log("Original transaction data:", JSON.stringify(txData, null, 2));

        // Create an abort controller to handle cancellations
        const abortController = new AbortController();

        // Validate transaction data exists
        if (!txData || typeof txData !== 'object') {
          throw new Error("Invalid transaction data: transaction data is missing or invalid");
        }

        // Check if the transaction data contains an error
        if ("error" in txData && txData.error) {
          throw new Error(txData.error);
        }

        // Validate required transaction fields
        if (!txData.to || !txData.data) {
          const errorMsg = `Invalid transaction data: missing required fields (to: ${txData.to}, data: ${txData.data})`;
          console.error("Invalid transaction data:", txData);
          throw new Error(errorMsg);
        }

        try {
          // Get the account address
          const [account] = await this.walletClient.getAddresses();
          if (!account) {
            throw new Error("No account available");
          }

          // Format transaction parameters - handle both gasLimit and gas_limit
          // Pydantic models often use camelCase while legacy code might use snake_case
          const gas = txData.gasLimit || txData.gas_limit || "300000";

          // Format transaction parameters
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

          // Debug logging for formatted transaction
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

          // Send transaction with immediate cancellation detection
          console.log("Sending transaction...");

          // Wrap in a promise that can be cancelled immediately
          const sendTransactionPromise = this.walletClient.sendTransaction(transaction);

          // Race the transaction against the abort signal and timeout
          const hash = await Promise.race([
            sendTransactionPromise,
            new Promise((_, reject) => {
              abortController.signal.addEventListener('abort', () => {
                reject(new Error('Transaction cancelled by user'));
              });
            }),
            // Add a timeout to prevent hanging on user rejection
            new Promise((_, reject) => {
              setTimeout(() => {
                reject(new Error('Transaction timeout - please try again'));
              }, 60000); // 60 second timeout (increased for user consideration time)
            })
          ]);

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

          // If it's a user rejection, immediately abort to prevent retries
          if (error instanceof Error && this.isUserRejection(error)) {
            abortController.abort();
            console.log("User rejected transaction - aborting to prevent retries");
          }

          throw this.formatTransactionError(error);
        }
      }, `executeTransaction_${this.chainId}`)();
    }, `executeTransaction_${this.chainId}`);
  }

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

    // Check for user rejection
    if (this.isUserRejection(error)) {
      return new Error("Transaction cancelled");
    }

    // Check for BigInt conversion errors (the root cause of the recursion)
    if (error.message.includes("Cannot convert") && error.message.includes("to a BigInt")) {
      return new Error("Invalid transaction amount format. Please check the transaction value.");
    }

    // Check for common errors
    if (error.message.includes("insufficient funds")) {
      return new Error("You don't have enough funds for this transaction");
    }
    if (error.message.includes("TRANSFER_FROM_FAILED")) {
      return new Error(
        "Token transfer failed. Please check your balance and token approval."
      );
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
        revertMatch
          ? `Transaction reverted: ${revertMatch[1]}`
          : "Transaction reverted by the contract"
      );
    }

    // For other errors, simplify the message
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

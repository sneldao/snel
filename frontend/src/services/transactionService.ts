import { TransactionData } from "../types/responses";
import { BLOCK_EXPLORERS } from "../constants/chains";
import { type WalletClient, type PublicClient } from "viem";

export class TransactionService {
  constructor(
    private walletClient: WalletClient,
    private publicClient: PublicClient,
    private chainId: number
  ) {}

  getBlockExplorerLink(hash: string): string {
    return `${
      BLOCK_EXPLORERS[this.chainId as keyof typeof BLOCK_EXPLORERS] ||
      BLOCK_EXPLORERS[8453]
    }${hash}`;
  }

  async executeTransaction(txData: TransactionData) {
    if (!this.walletClient) {
      throw new Error("Wallet not connected");
    }

    // Debug logging for transaction data
    console.log("Original transaction data:", JSON.stringify(txData, null, 2));

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
      const gas = txData.gasLimit || txData.gas_limit || "300000";

      // Format transaction parameters
      const transaction = {
        account,
        chain: null,
        to: txData.to as `0x${string}`,
        data: txData.data as `0x${string}`,
        value: BigInt(txData.value || "0"),
        chainId: txData.chainId || this.chainId,
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

      // Send transaction
      console.log("Sending transaction...");
      const hash = await this.walletClient.sendTransaction(transaction);
      console.log("Transaction sent with hash:", hash);

      // Wait for receipt
      console.log("Waiting for transaction receipt...");
      const receipt = await this.publicClient.waitForTransactionReceipt({
        hash,
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
      throw this.formatTransactionError(error);
    }
  }

  private formatTransactionError(error: unknown): Error {
    if (!(error instanceof Error)) {
      return new Error(String(error));
    }

    // Check for user rejection
    if (
      error.message.includes("user rejected") ||
      error.message.includes("User rejected") ||
      error.message.includes("User denied") ||
      error.message.includes("user denied") ||
      error.message.includes("rejected the request") ||
      error.message.includes("transaction signature")
    ) {
      return new Error("Transaction cancelled");
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

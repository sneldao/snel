import { 
  AxelarAssetTransfer, 
  AxelarQueryAPI, 
  AxelarGMPRecoveryAPI,
  CHAINS,
  Environment 
} from "@axelar-network/axelarjs-sdk";
import { ethers } from "ethers";

export interface AxelarTransferOptions {
  fromChain: string;
  toChain: string;
  fromToken: string;
  toToken: string;
  amount: string;
  recipientAddress: string;
  userAddress: string;
}

export interface AxelarTransferResult {
  success: boolean;
  depositAddress?: string;
  txHash?: string;
  error?: string;
  estimatedTime?: string;
  fees?: string;
}

export class AxelarService {
  private assetTransfer: AxelarAssetTransfer;
  private queryAPI: AxelarQueryAPI;
  private recoveryAPI: AxelarGMPRecoveryAPI;
  private environment: Environment;

  constructor() {
    // Use testnet for development, mainnet for production
    this.environment = process.env.NODE_ENV === 'production' ? Environment.MAINNET : Environment.TESTNET;
    
    this.assetTransfer = new AxelarAssetTransfer({ environment: this.environment });
    this.queryAPI = new AxelarQueryAPI({ environment: this.environment });
    this.recoveryAPI = new AxelarGMPRecoveryAPI({ environment: this.environment });
  }

  /**
   * Get quote for cross-chain transfer
   */
  async getTransferQuote(options: AxelarTransferOptions): Promise<{
    fee: string;
    estimatedTime: string;
    depositAddress?: string;
  }> {
    try {
      // Get transfer fee
      const fee = await this.queryAPI.getTransferFee(
        options.fromChain,
        options.toChain,
        options.fromToken,
        parseFloat(options.amount)
      );

      // Get deposit address for token transfer
      const depositAddress = await this.assetTransfer.getDepositAddress(
        options.fromChain,
        options.toChain,
        options.recipientAddress,
        options.fromToken,
        { 
          shouldUnwrapIntoNative: options.toToken === "ETH" || options.toToken === "MATIC" 
        }
      );

      return {
        fee: fee.toString(),
        estimatedTime: this.getEstimatedTime(options.fromChain, options.toChain),
        depositAddress
      };
    } catch (error) {
      console.error("Axelar quote error:", error);
      throw new Error(`Failed to get transfer quote: ${error}`);
    }
  }

  /**
   * Execute cross-chain token transfer
   */
  async executeTransfer(
    options: AxelarTransferOptions,
    signer: ethers.Signer
  ): Promise<AxelarTransferResult> {
    try {
      // Get deposit address
      const depositAddress = await this.assetTransfer.getDepositAddress(
        options.fromChain,
        options.toChain,
        options.recipientAddress,
        options.fromToken,
        { 
          shouldUnwrapIntoNative: options.toToken === "ETH" || options.toToken === "MATIC" 
        }
      );

      // For native tokens (ETH), send directly to deposit address
      if (options.fromToken === "ETH" || this.isNativeToken(options.fromToken, options.fromChain)) {
        const tx = await signer.sendTransaction({
          to: depositAddress,
          value: ethers.utils.parseEther(options.amount)
        });

        return {
          success: true,
          depositAddress,
          txHash: tx.hash,
          estimatedTime: this.getEstimatedTime(options.fromChain, options.toChain)
        };
      } 
      // For ERC20 tokens, transfer to deposit address
      else {
        const tokenContract = new ethers.Contract(
          this.getTokenAddress(options.fromToken, options.fromChain),
          [
            "function transfer(address to, uint256 amount) returns (bool)",
            "function decimals() view returns (uint8)"
          ],
          signer
        );

        const decimals = await tokenContract.decimals();
        const amount = ethers.utils.parseUnits(options.amount, decimals);

        const tx = await tokenContract.transfer(depositAddress, amount);

        return {
          success: true,
          depositAddress,
          txHash: tx.hash,
          estimatedTime: this.getEstimatedTime(options.fromChain, options.toChain)
        };
      }
    } catch (error) {
      console.error("Axelar transfer error:", error);
      return {
        success: false,
        error: error instanceof Error ? error.message : String(error)
      };
    }
  }

  /**
   * Track transaction status
   */
  async trackTransfer(txHash: string, fromChain: string): Promise<{
    status: string;
    link?: string;
    error?: string;
  }> {
    try {
      const status = await this.recoveryAPI.queryTransactionStatus(txHash);
      
      return {
        status: status.status || "pending",
        link: this.getAxelarscanLink(txHash)
      };
    } catch (error) {
      console.error("Axelar tracking error:", error);
      return {
        status: "unknown",
        error: error instanceof Error ? error.message : String(error)
      };
    }
  }

  /**
   * Check if Axelar supports the chain
   */
  isChainSupported(chainName: string): boolean {
    try {
      const chains = (CHAINS as any)[this.environment];
      if (!chains) return false;
      const supportedChains = Object.values(chains);
      return supportedChains.includes(chainName as any);
    } catch (error) {
      console.warn('Error checking Axelar chain support:', error);
      return false;
    }
  }

  /**
   * Get supported chains
   */
  getSupportedChains(): string[] {
    try {
      const chains = (CHAINS as any)[this.environment];
      if (!chains) return [];
      return Object.values(chains);
    } catch (error) {
      console.warn('Error getting Axelar supported chains:', error);
      return [];
    }
  }

  /**
   * Map chain ID to Axelar chain name
   */
  getAxelarChainName(chainId: number): string | null {
    const chainMap: { [key: number]: string } = {
      1: "Ethereum",
      56: "binance",
      137: "Polygon", 
      43114: "Avalanche",
      42161: "Arbitrum",
      10: "optimism",
      8453: "base",
      59144: "linea"
    };
    
    return chainMap[chainId] || null;
  }

  // Private helper methods
  private getEstimatedTime(fromChain: string, toChain: string): string {
    // Rough estimates based on Axelar documentation
    if (fromChain === "Ethereum" || toChain === "Ethereum") {
      return "15-20 minutes";
    }
    return "5-10 minutes";
  }

  private isNativeToken(token: string, chain: string): boolean {
    const nativeTokens: { [key: string]: string } = {
      "Ethereum": "ETH",
      "Polygon": "MATIC",
      "Avalanche": "AVAX",
      "binance": "BNB"
    };
    
    return nativeTokens[chain] === token;
  }

  private getTokenAddress(token: string, chain: string): string {
    // This would be populated with actual token addresses
    // For now, return common USDC addresses as example
    const tokenAddresses: { [key: string]: { [key: string]: string } } = {
      "USDC": {
        "Ethereum": "0xA0b86a33E6441b8C8A008c85c9c8B99c5b5a3c3b",
        "Polygon": "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174",
        "Avalanche": "0xB97EF9Ef8734C71904D8002F8b6Bc66Dd9c48a6E"
      }
    };
    
    return tokenAddresses[token]?.[chain] || "";
  }

  private getAxelarscanLink(txHash: string): string {
    const baseUrl = this.environment === Environment.MAINNET 
      ? "https://axelarscan.io" 
      : "https://testnet.axelarscan.io";
    return `${baseUrl}/tx/${txHash}`;
  }
}

// Export singleton instance
export const axelarService = new AxelarService();
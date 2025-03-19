import { openoceanLimitOrderSdk } from "@openocean.finance/limitorder-sdk";
import { ethers } from "ethers";
import { type WalletClient } from "viem";

export class DCAService {
  constructor(private chainId: number) {}

  async createDCAOrder(
    provider: WalletClient,
    account: string,
    makerToken: {
      address: string;
      decimals: number;
      symbol: string;
    },
    takerToken: {
      address: string;
      decimals: number;
      symbol: string;
    },
    makerAmount: string,
    takerAmount: string,
    frequency: string,
    times: number
  ) {
    try {
      // Validate chain - OpenOcean DCA currently only works on Base (chainId 8453)
      if (this.chainId !== 8453) {
        return {
          success: false,
          error: "DCA functionality is currently only supported on Base chain",
        };
      }

      // Validate minimum amount - $5 per transaction
      const amountInDecimal =
        parseFloat(makerAmount) / 10 ** makerToken.decimals;
      const totalAmount = amountInDecimal * times;

      // Assuming USDC/USDT with 6 decimals, minimum $5 per transaction
      const minimumPerDay = 5 * 10 ** (makerToken.decimals - 6); // Adjust for token decimals

      if (amountInDecimal < minimumPerDay) {
        return {
          success: false,
          error: `Minimum amount per transaction is $5 (${minimumPerDay} ${makerToken.symbol})`,
        };
      }

      // Map chain ID to chain key
      const chainKeyMap: Record<number, string> = {
        1: "eth",
        10: "optimism",
        56: "bsc",
        137: "polygon",
        42161: "arbitrum",
        8453: "base",
        534352: "scroll",
        43114: "avalanche",
      };

      const chainKey = chainKeyMap[this.chainId] || "base";

      // Map frequency to expire option
      const frequencyToExpire: Record<string, string> = {
        "86400": "1D", // 1 day
        "604800": "7D", // 7 days
        "2592000": "30D", // 30 days
      };

      // Calculate total duration in seconds
      const totalDurationSeconds = parseInt(frequency) * times;

      // Choose appropriate expire option
      let expireOption = "30D"; // Default to 30 days
      if (totalDurationSeconds <= 86400) {
        expireOption = "1D";
      } else if (totalDurationSeconds <= 604800) {
        expireOption = "7D";
      } else if (totalDurationSeconds <= 2592000) {
        expireOption = "30D";
      } else {
        expireOption = "1Y";
      }

      // Convert viem provider to ethers provider
      let ethersProvider;
      try {
        if (provider && provider.request) {
          // Create a provider adapter that matches what the SDK expects
          const providerAdapter = {
            request: provider.request,
            send: provider.request,
            sendAsync: provider.request,
          };
          ethersProvider = new ethers.providers.Web3Provider(
            providerAdapter as any
          );
        } else {
          // Fallback to a window.ethereum provider if available
          if (typeof window !== "undefined" && window.ethereum) {
            ethersProvider = new ethers.providers.Web3Provider(
              window.ethereum as any
            );
          } else {
            // Last resort: create a minimal provider object
            ethersProvider = {
              getSigner: () => ({
                getAddress: async () => account,
                signMessage: async () => "0x",
                _signTypedData: async () => "0x",
              }),
              getNetwork: async () => ({ chainId: this.chainId }),
            } as any;
          }
        }
      } catch (error) {
        console.error("Error initializing ethers provider:", error);
        return {
          success: false,
          error: "Failed to initialize ethers provider",
        };
      }

      // Create the order using the SDK
      const order = await openoceanLimitOrderSdk.createLimitOrder(
        {
          provider: ethersProvider,
          chainKey: chainKey,
          account: account,
          chainId: this.chainId.toString(),
          mode: "Dca",
        },
        {
          makerTokenAddress: makerToken.address,
          makerTokenDecimals: makerToken.decimals,
          takerTokenAddress: takerToken.address,
          takerTokenDecimals: takerToken.decimals,
          makerAmount: makerAmount,
          takerAmount: takerAmount,
          gasPrice: 3000000000,
          expire: expireOption,
          receiver: "0x0000000000000000000000000000000000000000",
          receiverInputData: "0x",
          mode: "Dca",
        }
      );

      // Add DCA-specific parameters
      const dcaOrder = {
        ...order,
        expireTime: (parseInt(frequency) * times).toString(),
        time: parseInt(frequency).toString(),
        times: Number(times),
        version: "v2",
        minPrice: "0.9",
        maxPrice: "1.1",
      };

      // Submit the order to the OpenOcean API
      const response = await fetch(
        `https://open-api.openocean.finance/v1/${this.chainId}/dca/swap`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify(dcaOrder),
        }
      );

      const result = await response.json();

      return {
        success: result.code === 200,
        data: result,
        order: dcaOrder,
      };
    } catch (error) {
      console.error("Error creating DCA order:", error);
      return {
        success: false,
        error: error instanceof Error ? error.message : String(error),
      };
    }
  }
}

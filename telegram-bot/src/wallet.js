// Simple wallet module for MVP
// In a real implementation, this would use account abstraction libraries

import fetch from "node-fetch";
import dotenv from "dotenv";
import crypto from "crypto";

dotenv.config();

const API_URL = process.env.API_URL || "http://localhost:8000";
const SCROLL_SEPOLIA_RPC = "https://sepolia-rpc.scroll.io";
const SCROLL_SEPOLIA_CHAIN_ID = 534351;

/**
 * Generate a deterministic wallet address for a user
 * @param {string} userId - Telegram user ID
 * @returns {string} - Wallet address
 */
export function generateWalletAddress(userId) {
  // Create a deterministic address based on the user ID
  const hash = crypto.createHash("sha256").update(userId).digest("hex");
  return `0x${hash.substring(0, 40)}`;
}

/**
 * Create a random wallet address and private key
 * @returns {Object} - Wallet with address and private key
 */
function createRandomWallet() {
  const privateKey = `0x${crypto.randomBytes(32).toString("hex")}`;
  const address = `0x${crypto.randomBytes(20).toString("hex")}`;

  return {
    address,
    privateKey,
  };
}

/**
 * Format ether value from wei
 * @param {string} wei - Wei value as string
 * @returns {string} - Formatted ether value
 */
function formatEther(wei) {
  // Simple implementation for MVP
  const etherValue = BigInt(wei) / BigInt(1e18);
  return etherValue.toString();
}

/**
 * Store wallet information for a user
 * @param {string} userId - Telegram user ID
 * @param {string} walletAddress - Wallet address
 * @returns {boolean} - Success status
 */
export function storeWalletInfo(userId, walletAddress) {
  // For MVP, we'll just log the information
  // In a real implementation, this would store in a database
  console.log(`Storing wallet info for user ${userId}: ${walletAddress}`);

  // Simulate successful storage
  return true;
}

/**
 * Get wallet information for a user
 * @param {string} userId - Telegram user ID
 * @returns {string|null} - Wallet address or null if not found
 */
export function getWalletInfo(userId) {
  // For MVP, we'll just regenerate the address
  // In a real implementation, this would fetch from a database
  return generateWalletAddress(userId);
}

/**
 * Simulate a wallet balance check
 * @param {string} walletAddress - Wallet address
 * @returns {Object} - Balance information
 */
export function getWalletBalance(walletAddress) {
  // For MVP, we'll return mock data
  // In a real implementation, this would query the blockchain

  return {
    eth: (Math.random() * 10).toFixed(4),
    usdc: (Math.random() * 1000).toFixed(2),
    usdt: (Math.random() * 1000).toFixed(2),
    dai: (Math.random() * 1000).toFixed(2),
  };
}

/**
 * Create a new wallet and store it in Redis
 * @param {string} userId - Telegram user ID
 * @returns {Promise<Object>} - Wallet information
 */
export async function createWallet(userId) {
  try {
    // Generate a new random wallet
    const wallet = createRandomWallet();
    const walletAddress = wallet.address;
    const privateKey = wallet.privateKey;

    // Store wallet data in Redis via API
    const response = await fetch(`${API_URL}/api/messaging/link-wallet`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        platform: "telegram",
        user_id: userId,
        wallet_address: walletAddress,
        wallet_data: {
          address: walletAddress,
          privateKey: privateKey, // Note: In production, this should be encrypted
          chainId: SCROLL_SEPOLIA_CHAIN_ID,
          created_at: new Date().toISOString(),
        },
      }),
    });

    if (!response.ok) {
      throw new Error(`Failed to store wallet: ${response.statusText}`);
    }

    return {
      address: walletAddress,
      privateKey: privateKey,
      chainId: SCROLL_SEPOLIA_CHAIN_ID,
    };
  } catch (error) {
    console.error("Error creating wallet:", error);
    throw error;
  }
}

/**
 * Get wallet information for a user
 * @param {string} userId - Telegram user ID
 * @returns {Promise<Object|null>} - Wallet information or null if not found
 */
export async function getWallet(userId) {
  try {
    const response = await fetch(
      `${API_URL}/api/messaging/linked-wallets/telegram/${userId}`
    );

    if (!response.ok) {
      if (response.status === 404) {
        return null;
      }
      throw new Error(`Failed to get wallet: ${response.statusText}`);
    }

    const data = await response.json();

    if (!data.linked) {
      return null;
    }

    // Get wallet data from Redis
    const walletDataResponse = await fetch(
      `${API_URL}/api/wallet/${data.wallet_address}`
    );

    if (!walletDataResponse.ok) {
      if (walletDataResponse.status === 404) {
        // Wallet address exists but no wallet data
        return {
          address: data.wallet_address,
          chainId: SCROLL_SEPOLIA_CHAIN_ID,
        };
      }
      throw new Error(
        `Failed to get wallet data: ${walletDataResponse.statusText}`
      );
    }

    const walletData = await walletDataResponse.json();

    return {
      address: data.wallet_address,
      privateKey: walletData.privateKey,
      chainId: walletData.chainId || SCROLL_SEPOLIA_CHAIN_ID,
    };
  } catch (error) {
    console.error("Error getting wallet:", error);
    throw error;
  }
}

/**
 * Check if a user has a wallet
 * @param {string} userId - Telegram user ID
 * @returns {Promise<boolean>} - True if user has a wallet
 */
export async function hasWallet(userId) {
  try {
    const wallet = await getWallet(userId);
    return wallet !== null;
  } catch (error) {
    console.error("Error checking wallet:", error);
    return false;
  }
}

/**
 * Disconnect a wallet from a user
 * @param {string} userId - Telegram user ID
 * @returns {Promise<boolean>} - True if successful
 */
export async function disconnectWallet(userId) {
  try {
    const response = await fetch(
      `${API_URL}/api/messaging/unlink-wallet/telegram/${userId}`,
      {
        method: "DELETE",
      }
    );

    if (!response.ok) {
      throw new Error(`Failed to disconnect wallet: ${response.statusText}`);
    }

    return true;
  } catch (error) {
    console.error("Error disconnecting wallet:", error);
    throw error;
  }
}

/**
 * Get wallet balance
 * @param {string} walletAddress - Wallet address
 * @returns {Promise<Object>} - Balance information
 */
export async function getBalance(walletAddress) {
  try {
    // For MVP, return mock ETH balance
    const mockEthBalance = (Math.random() * 2 + 0.1).toFixed(4);

    // Get token balances via API
    const response = await fetch(
      `${API_URL}/api/wallet/${walletAddress}/balances?chain_id=${SCROLL_SEPOLIA_CHAIN_ID}`
    );

    if (!response.ok) {
      // If API fails, return just ETH balance
      return {
        ETH: mockEthBalance,
        tokens: [],
      };
    }

    const tokenBalances = await response.json();

    return {
      ETH: mockEthBalance,
      tokens: tokenBalances.tokens || [],
    };
  } catch (error) {
    console.error("Error getting balance:", error);
    // Return mock data in case of error
    return {
      ETH: (Math.random() * 2 + 0.1).toFixed(4),
      tokens: [],
    };
  }
}

/**
 * Send a transaction
 * @param {Object} walletData - Wallet data
 * @param {Object} transaction - Transaction data
 * @returns {Promise<Object>} - Transaction receipt
 */
export async function sendTransaction(walletData, transaction) {
  try {
    // For MVP, just simulate a transaction
    console.log("Simulating transaction:", transaction);

    // Return a mock transaction hash
    return {
      hash: `0x${crypto.randomBytes(32).toString("hex")}`,
      success: true,
    };
  } catch (error) {
    console.error("Error sending transaction:", error);
    throw error;
  }
}

/**
 * Get a swap transaction
 * @param {string} fromToken - From token symbol
 * @param {string} toToken - To token symbol
 * @param {string} amount - Amount to swap
 * @param {string} walletAddress - Wallet address
 * @returns {Promise<Object>} - Swap transaction data
 */
export async function getSwapTransaction(
  fromToken,
  toToken,
  amount,
  walletAddress
) {
  try {
    // For MVP, just return mock data
    return {
      from: walletAddress,
      to: "0x1234567890123456789012345678901234567890", // Mock swap contract
      data: "0x", // Mock transaction data
      value: fromToken.toLowerCase() === "eth" ? amount : "0",
      gasLimit: "300000",
    };
  } catch (error) {
    console.error("Error getting swap transaction:", error);
    throw error;
  }
}

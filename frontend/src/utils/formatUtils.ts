/**
 * Utility functions for formatting token amounts and other values
 */

/**
 * Format token amount for display, handling scientific notation.
 *
 * @param amount The amount in smallest units
 * @param decimals The token decimals
 * @returns A formatted string representation of the amount
 */
export function formatAmountForDisplay(
  amount: string,
  decimals: number
): string {
  try {
    // Convert to integer
    const amountInt = BigInt(amount);

    // Convert to decimal
    const amountDecimal = Number(amountInt) / 10 ** decimals;

    // Format based on size
    if (amountDecimal < 0.000001) {
      // Very small amount
      return `${amountDecimal.toExponential(6)}`; // Scientific notation with 6 decimal places
    } else if (amountDecimal < 0.001) {
      // Small amount
      return `${amountDecimal.toFixed(10)}`.replace(/\.?0+$/, ""); // Up to 10 decimal places
    } else if (amountDecimal < 1) {
      // Medium amount
      return `${amountDecimal.toFixed(6)}`.replace(/\.?0+$/, ""); // Up to 6 decimal places
    } else {
      // Large amount
      return `${amountDecimal.toFixed(4)}`.replace(/\.?0+$/, ""); // Up to 4 decimal places
    }
  } catch (error) {
    return amount; // Return original if conversion fails
  }
}

/**
 * Validate and fix unreasonable gas USD estimates.
 *
 * @param gasUsd The gas USD estimate
 * @returns A reasonable gas USD estimate
 */
export function validateGasUsd(gasUsd: string): string {
  try {
    // Handle scientific notation and extremely large numbers
    if (gasUsd.includes("e") || gasUsd.length > 15) {
      return "2.50"; // Use a reasonable default
    }

    // Try to convert to float
    const gasFloat = parseFloat(gasUsd);

    // If it's not a valid number, use default
    if (isNaN(gasFloat)) {
      return "3.00"; // Use a reasonable default
    }

    // Check for absurdly high values (likely wrong format or unit conversion issue)
    if (gasFloat > 1000000) {
      return "2.00"; // Use a conservative default
    }

    // Check if the gas USD estimate is unreasonably high
    // More aggressive capping for UniswapX/0x which tend to overestimate
    if (gasFloat > 100) {
      // More than $100 for gas is likely an overestimation
      return "5.00"; // Use a reasonable default
    } else if (gasFloat > 30) {
      // Still high but not as extreme
      return "15.00"; // Cap at a more reasonable value
    } else if (gasFloat > 20) {
      // Moderately high

      return "10.00"; // Cap at a reasonable value
    }

    // Check if the gas USD estimate is negative or zero
    if (gasFloat <= 0) {
      return "1.50"; // Use a reasonable default
    }

    // For Polygon network and some other L2s, gas is often very cheap
    // Less than $0.01 is suspicious even for L2s, use a minimum value
    if (gasFloat < 0.01) {
      return "0.05"; // Set a reasonable minimum ($0.05)
    }

    // Round to 2 decimal places for consistency
    return gasFloat.toFixed(2);
  } catch (error) {
    return "2.00"; // Use a reasonable default
  }
}

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
export function formatAmountForDisplay(amount: string, decimals: number): string {
  try {
    // Convert to integer
    const amountInt = BigInt(amount);
    
    // Convert to decimal
    const amountDecimal = Number(amountInt) / (10 ** decimals);
    
    // Format based on size
    if (amountDecimal < 0.000001) { // Very small amount
      return `${amountDecimal.toExponential(6)}`; // Scientific notation with 6 decimal places
    } else if (amountDecimal < 0.001) { // Small amount
      return `${amountDecimal.toFixed(10)}`.replace(/\.?0+$/, ''); // Up to 10 decimal places
    } else if (amountDecimal < 1) { // Medium amount
      return `${amountDecimal.toFixed(6)}`.replace(/\.?0+$/, ''); // Up to 6 decimal places
    } else { // Large amount
      return `${amountDecimal.toFixed(4)}`.replace(/\.?0+$/, ''); // Up to 4 decimal places
    }
  } catch (error) {
    console.error("Error formatting amount:", error);
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
    // Try to convert to float
    const gasFloat = parseFloat(gasUsd);
    
    // Check if the gas USD estimate is unreasonably high
    if (gasFloat > 1000) { // More than $1000 for gas is unreasonable
      console.warn(`Unreasonable gas USD estimate: ${gasFloat}, using default`);
      return "5.00"; // Use a reasonable default
    }
    
    // Check if the gas USD estimate is negative
    if (gasFloat < 0) {
      console.warn(`Negative gas USD estimate: ${gasFloat}, using default`);
      return "1.00"; // Use a reasonable default
    }
    
    return gasUsd;
  } catch (error) {
    console.error("Error validating gas USD:", error);
    return "1.00"; // Use a reasonable default
  }
}

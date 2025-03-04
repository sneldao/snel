/**
 * Utilities for token operations in the frontend
 */

/**
 * Convert a token amount to smallest units (wei)
 * @param amount Human-readable token amount
 * @param decimals Token decimals
 * @returns Amount in smallest units (wei)
 */
export function amountToSmallestUnits(
  amount: number,
  decimals: number
): string {
  // Use BigInt to avoid floating point precision issues
  try {
    // Convert to string and handle decimal places
    const amountStr = amount.toString();
    let [integerPart, fractionPart = ""] = amountStr.split(".");

    // Pad the fraction part with zeros if needed
    fractionPart = fractionPart.padEnd(decimals, "0");

    // Truncate if longer than needed
    fractionPart = fractionPart.substring(0, decimals);

    // Combine the parts without the decimal point
    const combinedStr = integerPart + fractionPart;

    // Remove leading zeros
    const trimmedStr = combinedStr.replace(/^0+/, "") || "0";

    return trimmedStr;
  } catch (error) {
    console.error("Error converting to smallest units:", error);
    return "0";
  }
}

/**
 * Convert from smallest units (wei) to human-readable amount
 * @param amountInSmallestUnits Amount in smallest units (wei)
 * @param decimals Token decimals
 * @returns Human-readable amount
 */
export function smallestUnitsToAmount(
  amountInSmallestUnits: string | bigint,
  decimals: number
): number {
  try {
    // Convert to string if it's a BigInt
    let amountStr =
      typeof amountInSmallestUnits === "bigint"
        ? amountInSmallestUnits.toString()
        : String(amountInSmallestUnits);

    // Handle "0x" prefixed hex strings
    if (amountStr.startsWith("0x")) {
      try {
        amountStr = BigInt(amountStr).toString();
      } catch (error) {
        console.error("Error converting hex string to BigInt:", error);
        return 0;
      }
    }

    // Handle empty or invalid input
    if (!amountStr || amountStr === "0" || amountStr === "0x0") {
      return 0;
    }

    // Remove any non-numeric characters (except for scientific notation)
    amountStr = amountStr.replace(/[^0-9.eE+-]/g, "");

    // String-based decimal placement to avoid BigInt division
    const amountLength = amountStr.length;

    if (amountLength <= decimals) {
      // Amount is smaller than 1
      // Example: "123" with 18 decimals = 0.000000000000000123
      const zeros = decimals - amountLength;
      return parseFloat(`0.${"0".repeat(zeros)}${amountStr}`);
    } else {
      // Amount is greater than or equal to 1
      // Insert decimal point at the right position
      const wholePartStr = amountStr.slice(0, amountLength - decimals);
      const fractionalPartStr = amountStr.slice(amountLength - decimals);
      return parseFloat(`${wholePartStr}.${fractionalPartStr}`);
    }
  } catch (error) {
    console.error("Error converting from smallest units:", error, {
      input: amountInSmallestUnits,
      decimals,
    });
    return 0;
  }
}

/**
 * Format a token amount for display
 * @param amount Token amount (human-readable)
 * @param decimals Token decimals (optional, defaults to 18)
 * @param maxDecimals Maximum decimal places to show (optional, defaults to 6)
 * @returns Formatted string representation
 */
export function formatTokenAmount(
  amount: number,
  decimals: number = 18,
  maxDecimals: number = 6
): string {
  try {
    // If the amount is very small, use exponential notation
    if (amount > 0 && amount < 0.000001) {
      return amount.toExponential(4);
    }

    // For normal values, format with appropriate decimal places
    const decimalPlaces = Math.min(maxDecimals, decimals);

    return amount.toLocaleString(undefined, {
      maximumFractionDigits: decimalPlaces,
      minimumFractionDigits: amount < 0.01 ? decimalPlaces : 2,
    });
  } catch (error) {
    console.error("Error formatting token amount:", error);
    return amount.toString();
  }
}

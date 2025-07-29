/**
 * Utility functions for formatting addresses, token amounts, and other values
 * Used throughout the application, particularly in the EnhancedCommandInput component
 */

import { ethers } from 'ethers';

/**
 * Format an Ethereum address by shortening it (showing first and last few characters)
 * 
 * @param address The Ethereum address to format
 * @param prefixLength Number of characters to show at the beginning (default: 6)
 * @param suffixLength Number of characters to show at the end (default: 4)
 * @returns Formatted address string
 */
export function formatAddress(
  address: string,
  prefixLength: number = 6,
  suffixLength: number = 4
): string {
  // Return as is if it's an ENS name
  if (address && address.includes('.')) {
    return address;
  }
  
  // Return as is if address is too short
  if (!address || address.length < prefixLength + suffixLength + 3) {
    return address;
  }
  
  // Format the address
  return `${address.substring(0, prefixLength)}...${address.substring(
    address.length - suffixLength
  )}`;
}

/**
 * Format a token amount for display with appropriate decimal places
 * 
 * @param amount The token amount (can be string, number, or BigNumber)
 * @param decimals The number of decimals for the token (default: 18)
 * @param displayDecimals Maximum number of decimal places to display (default: 6)
 * @param symbol Optional token symbol to append
 * @returns Formatted token amount string
 */
export function formatTokenAmount(
  amount: string | number | ethers.BigNumber,
  decimals: number = 18,
  displayDecimals: number = 6,
  symbol?: string
): string {
  if (amount === undefined || amount === null) {
    return symbol ? `0 ${symbol}` : '0';
  }
  
  try {
    let value: number;
    
    // Convert amount to number based on its type
    if (typeof amount === 'string') {
      // Handle scientific notation or large numbers in string form
      if (amount.includes('e') || amount.length > 15) {
        // Use ethers to parse large numbers safely
        const bn = ethers.utils.parseUnits(amount, 0);
        value = parseFloat(ethers.utils.formatUnits(bn, decimals));
      } else {
        value = parseFloat(amount);
      }
    } else if (typeof amount === 'number') {
      value = amount;
    } else {
      // Handle BigNumber
      value = parseFloat(ethers.utils.formatUnits(amount, decimals));
    }
    
    // Determine appropriate decimal places based on value
    let decimalPlaces = displayDecimals;
    if (value === 0) {
      decimalPlaces = 0;
    } else if (value < 0.0001) {
      decimalPlaces = 8; // Show more decimals for very small values
    } else if (value < 0.01) {
      decimalPlaces = 6;
    } else if (value < 1) {
      decimalPlaces = 4;
    } else if (value >= 1000) {
      decimalPlaces = 2;
    }
    
    // Format the number
    const formattedValue = value.toLocaleString(undefined, {
      minimumFractionDigits: 0,
      maximumFractionDigits: decimalPlaces,
    });
    
    // Remove trailing zeros after decimal point
    const cleanedValue = formattedValue.replace(/\.?0+$/, '');
    
    // Add symbol if provided
    return symbol ? `${cleanedValue} ${symbol}` : cleanedValue;
  } catch (error) {
    console.error('Error formatting token amount:', error);
    return symbol ? `0 ${symbol}` : '0';
  }
}

/**
 * Format a percentage value
 * 
 * @param value The percentage value (0-100)
 * @param decimals Number of decimal places (default: 2)
 * @param includeSymbol Whether to include the % symbol (default: true)
 * @returns Formatted percentage string
 */
export function formatPercentage(
  value: number,
  decimals: number = 2,
  includeSymbol: boolean = true
): string {
  if (value === undefined || value === null || isNaN(value)) {
    return includeSymbol ? '0%' : '0';
  }
  
  // Handle very small values
  if (value !== 0 && Math.abs(value) < 0.01) {
    return includeSymbol ? '<0.01%' : '<0.01';
  }
  
  // Format the percentage
  const formatted = value.toFixed(decimals).replace(/\.?0+$/, '');
  
  return includeSymbol ? `${formatted}%` : formatted;
}

/**
 * Format a currency value
 * 
 * @param value The currency value
 * @param currency The currency code (default: 'USD')
 * @param decimals Number of decimal places (default: 2)
 * @returns Formatted currency string
 */
export function formatCurrency(
  value: number,
  currency: string = 'USD',
  decimals: number = 2
): string {
  if (value === undefined || value === null || isNaN(value)) {
    return `$0.00`;
  }
  
  // Handle very small values
  if (value !== 0 && Math.abs(value) < 0.01) {
    return `<$0.01`;
  }
  
  // Format based on value size
  let formattedValue: string;
  if (value >= 1000000000) {
    // Billions
    formattedValue = `${(value / 1000000000).toFixed(decimals)}B`;
  } else if (value >= 1000000) {
    // Millions
    formattedValue = `${(value / 1000000).toFixed(decimals)}M`;
  } else if (value >= 1000) {
    // Thousands
    formattedValue = `${(value / 1000).toFixed(decimals)}K`;
  } else {
    // Regular format
    formattedValue = value.toFixed(decimals);
  }
  
  // Remove trailing zeros
  formattedValue = formattedValue.replace(/\.?0+$/, '');
  
  // Add currency symbol
  if (currency === 'USD') {
    return `$${formattedValue}`;
  } else {
    return `${formattedValue} ${currency}`;
  }
}

/**
 * Format a number with appropriate suffixes (K, M, B, etc.)
 * 
 * @param value The number to format
 * @param decimals Number of decimal places (default: 2)
 * @returns Formatted number string
 */
export function formatNumber(
  value: number,
  decimals: number = 2
): string {
  if (value === undefined || value === null || isNaN(value)) {
    return '0';
  }
  
  // Format based on value size
  let formattedValue: string;
  if (value >= 1000000000) {
    // Billions
    formattedValue = `${(value / 1000000000).toFixed(decimals)}B`;
  } else if (value >= 1000000) {
    // Millions
    formattedValue = `${(value / 1000000).toFixed(decimals)}M`;
  } else if (value >= 1000) {
    // Thousands
    formattedValue = `${(value / 1000).toFixed(decimals)}K`;
  } else {
    // Regular format
    formattedValue = value.toFixed(decimals);
  }
  
  // Remove trailing zeros
  return formattedValue.replace(/\.?0+$/, '');
}

/**
 * Format a time duration in seconds to a human-readable string
 * 
 * @param seconds The duration in seconds
 * @param shortFormat Whether to use short format (default: false)
 * @returns Formatted duration string
 */
export function formatDuration(
  seconds: number,
  shortFormat: boolean = false
): string {
  if (seconds === undefined || seconds === null || isNaN(seconds) || seconds < 0) {
    return shortFormat ? '0s' : '0 seconds';
  }
  
  if (seconds < 60) {
    // Seconds
    return shortFormat ? `${Math.round(seconds)}s` : `${Math.round(seconds)} second${seconds === 1 ? '' : 's'}`;
  } else if (seconds < 3600) {
    // Minutes
    const minutes = Math.floor(seconds / 60);
    return shortFormat ? `${minutes}m` : `${minutes} minute${minutes === 1 ? '' : 's'}`;
  } else if (seconds < 86400) {
    // Hours
    const hours = Math.floor(seconds / 3600);
    if (!shortFormat) {
      const minutes = Math.floor((seconds % 3600) / 60);
      return minutes > 0 
        ? `${hours} hour${hours === 1 ? '' : 's'} ${minutes} minute${minutes === 1 ? '' : 's'}`
        : `${hours} hour${hours === 1 ? '' : 's'}`;
    }
    return `${hours}h`;
  } else {
    // Days
    const days = Math.floor(seconds / 86400);
    if (!shortFormat) {
      const hours = Math.floor((seconds % 86400) / 3600);
      return hours > 0 
        ? `${days} day${days === 1 ? '' : 's'} ${hours} hour${hours === 1 ? '' : 's'}`
        : `${days} day${days === 1 ? '' : 's'}`;
    }
    return `${days}d`;
  }
}

/**
 * Format a date to a human-readable string
 * 
 * @param date The date to format (Date object or timestamp)
 * @param includeTime Whether to include the time (default: false)
 * @returns Formatted date string
 */
export function formatDate(
  date: Date | number | string,
  includeTime: boolean = false
): string {
  if (!date) {
    return '';
  }
  
  // Convert to Date object if needed
  const dateObj = typeof date === 'object' ? date : new Date(date);
  
  // Format date
  const options: Intl.DateTimeFormatOptions = {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  };
  
  // Add time options if requested
  if (includeTime) {
    options.hour = '2-digit';
    options.minute = '2-digit';
  }
  
  return dateObj.toLocaleDateString(undefined, options);
}

/**
 * Format a timestamp to a relative time string (e.g., "2 hours ago")
 * 
 * @param timestamp The timestamp to format
 * @returns Relative time string
 */
export function formatRelativeTime(timestamp: number | Date): string {
  const now = Date.now();
  const date = timestamp instanceof Date ? timestamp.getTime() : timestamp;
  const diffSeconds = Math.floor((now - date) / 1000);
  
  if (diffSeconds < 60) {
    return 'just now';
  } else if (diffSeconds < 3600) {
    const minutes = Math.floor(diffSeconds / 60);
    return `${minutes} minute${minutes === 1 ? '' : 's'} ago`;
  } else if (diffSeconds < 86400) {
    const hours = Math.floor(diffSeconds / 3600);
    return `${hours} hour${hours === 1 ? '' : 's'} ago`;
  } else if (diffSeconds < 604800) {
    const days = Math.floor(diffSeconds / 86400);
    return `${days} day${days === 1 ? '' : 's'} ago`;
  } else if (diffSeconds < 2592000) {
    const weeks = Math.floor(diffSeconds / 604800);
    return `${weeks} week${weeks === 1 ? '' : 's'} ago`;
  } else if (diffSeconds < 31536000) {
    const months = Math.floor(diffSeconds / 2592000);
    return `${months} month${months === 1 ? '' : 's'} ago`;
  } else {
    const years = Math.floor(diffSeconds / 31536000);
    return `${years} year${years === 1 ? '' : 's'} ago`;
  }
}

/**
 * Format a gas price in gwei
 * 
 * @param gweiValue The gas price in gwei
 * @returns Formatted gas price string
 */
export function formatGasPrice(gweiValue: number): string {
  if (gweiValue === undefined || gweiValue === null || isNaN(gweiValue)) {
    return '0 gwei';
  }
  
  if (gweiValue < 0.01) {
    return '<0.01 gwei';
  }
  
  if (gweiValue < 1) {
    return `${gweiValue.toFixed(2)} gwei`;
  }
  
  if (gweiValue < 10) {
    return `${gweiValue.toFixed(1)} gwei`;
  }
  
  return `${Math.round(gweiValue)} gwei`;
}

/**
 * Truncate text with ellipsis if it exceeds maxLength
 * 
 * @param text The text to truncate
 * @param maxLength Maximum length before truncation (default: 30)
 * @returns Truncated text
 */
export function truncateText(text: string, maxLength: number = 30): string {
  if (!text) return '';
  
  if (text.length <= maxLength) {
    return text;
  }
  
  return `${text.substring(0, maxLength)}...`;
}

/**
 * Format a file size
 * 
 * @param bytes The file size in bytes
 * @returns Formatted file size string
 */
export function formatFileSize(bytes: number): string {
  if (bytes === 0) return '0 Bytes';
  
  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(2))} ${sizes[i]}`;
}

/**
 * Format a transaction hash
 * 
 * @param hash The transaction hash
 * @param prefixLength Number of characters to show at the beginning (default: 6)
 * @param suffixLength Number of characters to show at the end (default: 4)
 * @returns Formatted transaction hash
 */
export function formatTxHash(
  hash: string,
  prefixLength: number = 6,
  suffixLength: number = 4
): string {
  return formatAddress(hash, prefixLength, suffixLength);
}

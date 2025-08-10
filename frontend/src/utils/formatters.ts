/**
 * Utility functions for formatting values
 */

export const formatCurrency = (value: number | string, currency = 'USD'): string => {
  const numValue = typeof value === 'string' ? parseFloat(value) : value;
  
  if (isNaN(numValue)) return '$0.00';
  
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: currency,
    minimumFractionDigits: 2,
    maximumFractionDigits: 2
  }).format(numValue);
};

export const formatNumber = (value: number | string, decimals = 2): string => {
  const numValue = typeof value === 'string' ? parseFloat(value) : value;
  
  if (isNaN(numValue)) return '0';
  
  return new Intl.NumberFormat('en-US', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals
  }).format(numValue);
};

export const formatTokenAmount = (amount: number | string, symbol: string): string => {
  const numAmount = typeof amount === 'string' ? parseFloat(amount) : amount;
  
  if (isNaN(numAmount)) return `0 ${symbol}`;
  
  return `${formatNumber(numAmount, 6)} ${symbol}`;
};

export const formatAddress = (address: string, chars = 4): string => {
  if (!address) return '';
  const parsed = address; // Assuming address is already a string
  return `${parsed.substring(0, chars + 2)}...${parsed.substring(parsed.length - chars)}`;
};
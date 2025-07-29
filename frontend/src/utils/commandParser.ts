import { SUPPORTED_CHAINS } from '../constants/chains';
import { POPULAR_TOKENS } from '../constants/tokens';
import { COMMON_ADDRESSES } from '../constants/addresses';

/**
 * Represents a parsed command with extracted parameters
 */
export interface ParsedCommand {
  // Core command properties
  type: CommandType;
  rawCommand: string;
  
  // Token and amount properties
  sourceToken?: string;
  sourceAmount?: number;
  sourceAmountIsPercentage?: boolean;
  sourceAmountIsAll?: boolean;
  targetToken?: string;
  targetAmount?: number;
  minTargetAmount?: number;
  
  // Address properties
  recipientAddress?: string;
  
  // Chain properties
  sourceChain?: number;
  targetChain?: number;
  
  // Additional parameters
  slippage?: number;
  gasAmount?: number;
  message?: string;
  dex?: string;
  
  // Portfolio and analysis properties
  timeframe?: string;
  metric?: string;
  
  // Settings
  setting?: string;
  value?: string | number | boolean;
  
  // Additional extracted parameters
  params: Record<string, any>;
}

/**
 * Supported command types
 */
export type CommandType = 
  | 'swap'
  | 'bridge'
  | 'send'
  | 'analyze'
  | 'check'
  | 'info'
  | 'set'
  | 'connect'
  | 'disconnect'
  | 'help'
  | 'stake'
  | 'unstake'
  | 'provide'
  | 'remove'
  | 'borrow'
  | 'repay'
  | 'claim'
  | 'alert'
  | 'schedule'
  | 'switch'
  | 'generate'
  | 'verify'
  | 'decode'
  | 'find'
  | 'join'
  | 'share'
  | 'follow'
  | 'calculate'
  | 'show'
  | 'compare'
  | 'estimate'
  | 'unknown';

/**
 * Parse a natural language command into structured data
 * 
 * @param command The command string to parse
 * @returns A structured representation of the command
 */
export function parseCommand(command: string): ParsedCommand {
  // Normalize command text
  const normalizedCommand = normalizeCommand(command);
  const words = normalizedCommand.split(' ');
  
  // Initialize result with default type and raw command
  const result: ParsedCommand = {
    type: 'unknown',
    rawCommand: command,
    params: {}
  };
  
  // Determine command type based on first word
  result.type = determineCommandType(words[0], normalizedCommand);
  
  // Extract parameters based on command type
  switch (result.type) {
    case 'swap':
      parseSwapCommand(normalizedCommand, result);
      break;
    case 'bridge':
      parseBridgeCommand(normalizedCommand, result);
      break;
    case 'send':
      parseSendCommand(normalizedCommand, result);
      break;
    case 'analyze':
    case 'check':
      parseAnalysisCommand(normalizedCommand, result);
      break;
    case 'set':
      parseSettingCommand(normalizedCommand, result);
      break;
    case 'stake':
    case 'unstake':
      parseStakingCommand(normalizedCommand, result);
      break;
    case 'provide':
    case 'remove':
      parseLiquidityCommand(normalizedCommand, result);
      break;
    case 'borrow':
    case 'repay':
      parseLendingCommand(normalizedCommand, result);
      break;
    default:
      // For other command types, extract common parameters
      extractCommonParameters(normalizedCommand, result);
  }
  
  return result;
}

/**
 * Normalize command text for easier parsing
 */
function normalizeCommand(command: string): string {
  return command
    .trim()
    .toLowerCase()
    .replace(/\s+/g, ' ') // Replace multiple spaces with a single space
    .replace(/,/g, '') // Remove commas
    .replace(/\$/g, ''); // Remove dollar signs
}

/**
 * Determine the command type based on the first word and context
 */
function determineCommandType(firstWord: string, fullCommand: string): CommandType {
  // Direct matches
  const directMatches: Record<string, CommandType> = {
    'swap': 'swap',
    'bridge': 'bridge',
    'send': 'send',
    'transfer': 'send',
    'analyze': 'analyze',
    'check': 'check',
    'show': 'check',
    'set': 'set',
    'connect': 'connect',
    'disconnect': 'disconnect',
    'help': 'help',
    'stake': 'stake',
    'unstake': 'unstake',
    'provide': 'provide',
    'add': 'provide',
    'remove': 'remove',
    'withdraw': 'remove',
    'borrow': 'borrow',
    'repay': 'repay',
    'claim': 'claim',
    'alert': 'alert',
    'schedule': 'schedule',
    'switch': 'switch',
    'generate': 'generate',
    'verify': 'verify',
    'decode': 'decode',
    'find': 'find',
    'join': 'join',
    'share': 'share',
    'follow': 'follow',
    'calculate': 'calculate',
    'convert': 'calculate',
    'compare': 'compare',
    'estimate': 'estimate',
    'tell': 'info',
    'info': 'info',
    'fast': 'bridge', // "fast bridge" commands
  };
  
  // Check for direct match
  if (directMatches[firstWord]) {
    // Special case for "fast bridge" to return 'bridge' type
    if (firstWord === 'fast' && fullCommand.includes('fast bridge')) {
      return 'bridge';
    }
    return directMatches[firstWord];
  }
  
  // Check for context-based matches
  if (fullCommand.includes('portfolio')) {
    return 'analyze';
  }
  
  if (fullCommand.includes('balance')) {
    return 'check';
  }
  
  if (fullCommand.includes('price')) {
    return 'check';
  }
  
  if (fullCommand.includes('gas')) {
    return 'check';
  }
  
  if (fullCommand.includes('network')) {
    return 'check';
  }
  
  // Default to unknown if no match found
  return 'unknown';
}

/**
 * Parse swap command parameters
 */
function parseSwapCommand(command: string, result: ParsedCommand): void {
  // Extract source amount and token
  const amountTokenPattern = /swap\s+(?:(all|[\d.]+%?)\s+(?:of\s+my\s+)?)?([a-z0-9]+)(?:\s+for|$)/i;
  const amountTokenMatch = command.match(amountTokenPattern);
  
  if (amountTokenMatch) {
    // Handle "all" keyword
    if (amountTokenMatch[1] === 'all') {
      result.sourceAmountIsAll = true;
    } 
    // Handle percentage
    else if (amountTokenMatch[1] && amountTokenMatch[1].includes('%')) {
      result.sourceAmount = parseFloat(amountTokenMatch[1]);
      result.sourceAmountIsPercentage = true;
    } 
    // Handle numeric amount
    else if (amountTokenMatch[1]) {
      result.sourceAmount = parseFloat(amountTokenMatch[1]);
    }
    
    result.sourceToken = amountTokenMatch[2].toUpperCase();
  }
  
  // Extract target token
  const targetTokenPattern = /for\s+(?:at\s+least\s+)?([\d.]+)?\s*([a-z0-9]+)(?:\s|$)/i;
  const targetTokenMatch = command.match(targetTokenPattern);
  
  if (targetTokenMatch) {
    if (targetTokenMatch[1]) {
      result.minTargetAmount = parseFloat(targetTokenMatch[1]);
    }
    result.targetToken = targetTokenMatch[2].toUpperCase();
  }
  
  // Extract slippage
  const slippagePattern = /(?:with|slippage)\s+([\d.]+)%\s+slippage/i;
  const slippageMatch = command.match(slippagePattern);
  
  if (slippageMatch) {
    result.slippage = parseFloat(slippageMatch[1]);
  }
  
  // Extract DEX
  const dexPattern = /on\s+([a-z0-9]+)(?:\s|$)/i;
  const dexMatch = command.match(dexPattern);
  
  if (dexMatch) {
    result.dex = dexMatch[1].toLowerCase();
  }
  
  // Extract common parameters
  extractCommonParameters(command, result);
}

/**
 * Parse bridge command parameters
 */
function parseBridgeCommand(command: string, result: ParsedCommand): void {
  // Extract source amount and token
  const amountTokenPattern = /bridge\s+(?:(all|[\d.]+%?)\s+(?:of\s+my\s+)?)?([a-z0-9]+)(?:\s+from|\s+to|$)/i;
  const amountTokenMatch = command.match(amountTokenPattern);
  
  if (amountTokenMatch) {
    // Handle "all" keyword
    if (amountTokenMatch[1] === 'all') {
      result.sourceAmountIsAll = true;
    } 
    // Handle percentage
    else if (amountTokenMatch[1] && amountTokenMatch[1].includes('%')) {
      result.sourceAmount = parseFloat(amountTokenMatch[1]);
      result.sourceAmountIsPercentage = true;
    } 
    // Handle numeric amount
    else if (amountTokenMatch[1]) {
      result.sourceAmount = parseFloat(amountTokenMatch[1]);
    }
    
    result.sourceToken = amountTokenMatch[2].toUpperCase();
  }
  
  // Extract source chain
  const sourceChainPattern = /from\s+([a-z0-9]+)(?:\s|$)/i;
  const sourceChainMatch = command.match(sourceChainPattern);
  
  if (sourceChainMatch) {
    result.sourceChain = getChainIdByName(sourceChainMatch[1]);
  }
  
  // Extract target chain
  const targetChainPattern = /to\s+([a-z0-9]+)(?:\s|$)/i;
  const targetChainMatch = command.match(targetChainPattern);
  
  if (targetChainMatch) {
    result.targetChain = getChainIdByName(targetChainMatch[1]);
  }
  
  // Extract gas amount for destination
  const gasPattern = /with\s+([\d.]+)\s+([a-z0-9]+)\s+for\s+gas/i;
  const gasMatch = command.match(gasPattern);
  
  if (gasMatch) {
    result.gasAmount = parseFloat(gasMatch[1]);
    result.params.gasToken = gasMatch[2].toUpperCase();
  }
  
  // Extract recipient address if specified
  const recipientPattern = /to\s+([a-z0-9]+\.[a-z]+|0x[a-f0-9]{40})(?:\s|$)/i;
  const recipientMatch = command.match(recipientPattern);
  
  if (recipientMatch && !getChainIdByName(recipientMatch[1])) {
    result.recipientAddress = recipientMatch[1];
  }
  
  // Extract common parameters
  extractCommonParameters(command, result);
}

/**
 * Parse send command parameters
 */
function parseSendCommand(command: string, result: ParsedCommand): void {
  // Extract source amount and token
  const amountTokenPattern = /send\s+(?:(all|[\d.]+%?)\s+(?:of\s+my\s+)?)?([a-z0-9]+)(?:\s+to|$)/i;
  const amountTokenMatch = command.match(amountTokenPattern);
  
  if (amountTokenMatch) {
    // Handle "all" keyword
    if (amountTokenMatch[1] === 'all') {
      result.sourceAmountIsAll = true;
    } 
    // Handle percentage
    else if (amountTokenMatch[1] && amountTokenMatch[1].includes('%')) {
      result.sourceAmount = parseFloat(amountTokenMatch[1]);
      result.sourceAmountIsPercentage = true;
    } 
    // Handle numeric amount
    else if (amountTokenMatch[1]) {
      result.sourceAmount = parseFloat(amountTokenMatch[1]);
    }
    
    result.sourceToken = amountTokenMatch[2].toUpperCase();
  }
  
  // Extract recipient address
  const recipientPattern = /to\s+([a-z0-9]+\.[a-z]+|0x[a-f0-9]{40})(?:\s|$)/i;
  const recipientMatch = command.match(recipientPattern);
  
  if (recipientMatch) {
    result.recipientAddress = recipientMatch[1];
  }
  
  // Extract message
  const messagePattern = /with\s+message\s+"([^"]+)"/i;
  const messageMatch = command.match(messagePattern);
  
  if (messageMatch) {
    result.message = messageMatch[1];
  }
  
  // Extract target chain for cross-chain sends
  const targetChainPattern = /on\s+([a-z0-9]+)(?:\s|$)/i;
  const targetChainMatch = command.match(targetChainPattern);
  
  if (targetChainMatch) {
    result.targetChain = getChainIdByName(targetChainMatch[1]);
  }
  
  // Extract common parameters
  extractCommonParameters(command, result);
}

/**
 * Parse analysis command parameters
 */
function parseAnalysisCommand(command: string, result: ParsedCommand): void {
  // Check if this is a portfolio analysis
  if (command.includes('portfolio')) {
    result.params.analysisType = 'portfolio';
    
    // Extract timeframe
    const timeframePattern = /(day|week|month|year|all time)/i;
    const timeframeMatch = command.match(timeframePattern);
    
    if (timeframeMatch) {
      result.timeframe = timeframeMatch[1].toLowerCase();
    }
    
    // Extract specific metrics
    if (command.includes('risk')) {
      result.metric = 'risk';
    } else if (command.includes('yield')) {
      result.metric = 'yield';
    } else if (command.includes('diversification')) {
      result.metric = 'diversification';
    } else if (command.includes('history')) {
      result.metric = 'history';
    }
    
    // Extract chain if specified
    const chainPattern = /on\s+([a-z0-9]+)(?:\s|$)/i;
    const chainMatch = command.match(chainPattern);
    
    if (chainMatch) {
      result.sourceChain = getChainIdByName(chainMatch[1]);
    }
  }
  // Check if this is a balance check
  else if (command.includes('balance')) {
    result.params.analysisType = 'balance';
    
    // Extract specific token
    const tokenPattern = /my\s+([a-z0-9]+)\s+balance/i;
    const tokenMatch = command.match(tokenPattern);
    
    if (tokenMatch) {
      result.sourceToken = tokenMatch[1].toUpperCase();
    }
    
    // Extract chain if specified
    const chainPattern = /on\s+([a-z0-9]+)(?:\s|$)/i;
    const chainMatch = command.match(chainPattern);
    
    if (chainMatch) {
      result.sourceChain = getChainIdByName(chainMatch[1]);
    }
    
    // Check if this is for another address
    const addressPattern = /of\s+([a-z0-9]+\.[a-z]+|0x[a-f0-9]{40})(?:\s|$)/i;
    const addressMatch = command.match(addressPattern);
    
    if (addressMatch) {
      result.params.targetAddress = addressMatch[1];
    }
  }
  // Check if this is a price check
  else if (command.includes('price')) {
    result.params.analysisType = 'price';
    
    // Extract token
    const tokenPattern = /([a-z0-9]+)\s+price/i;
    const tokenMatch = command.match(tokenPattern);
    
    if (tokenMatch) {
      result.sourceToken = tokenMatch[1].toUpperCase();
    }
    
    // Check if this is historical
    if (command.includes('history')) {
      result.params.historical = true;
      
      // Extract timeframe
      const timeframePattern = /(day|week|month|year|all time)/i;
      const timeframeMatch = command.match(timeframePattern);
      
      if (timeframeMatch) {
        result.timeframe = timeframeMatch[1].toLowerCase();
      }
    }
  }
  // Check if this is a gas price check
  else if (command.includes('gas')) {
    result.params.analysisType = 'gas';
    
    // Extract chain if specified
    const chainPattern = /on\s+([a-z0-9]+)(?:\s|$)/i;
    const chainMatch = command.match(chainPattern);
    
    if (chainMatch) {
      result.sourceChain = getChainIdByName(chainMatch[1]);
    }
  }
  // Check if this is a network status check
  else if (command.includes('network')) {
    result.params.analysisType = 'network';
    
    // Extract chain if specified
    const chainPattern = /([a-z0-9]+)\s+network/i;
    const chainMatch = command.match(chainPattern);
    
    if (chainMatch) {
      result.sourceChain = getChainIdByName(chainMatch[1]);
    }
  }
  
  // Extract common parameters
  extractCommonParameters(command, result);
}

/**
 * Parse setting command parameters
 */
function parseSettingCommand(command: string, result: ParsedCommand): void {
  // Extract setting type
  if (command.includes('slippage')) {
    result.setting = 'slippage';
    
    // Extract value
    const valuePattern = /to\s+([\d.]+)%/i;
    const valueMatch = command.match(valuePattern);
    
    if (valueMatch) {
      result.value = parseFloat(valueMatch[1]);
    }
  }
  else if (command.includes('gas price')) {
    result.setting = 'gasPrice';
    
    // Extract value
    const valuePattern = /to\s+(fast|average|slow)/i;
    const valueMatch = command.match(valuePattern);
    
    if (valueMatch) {
      result.value = valueMatch[1].toLowerCase();
    }
  }
  else if (command.includes('theme') || command.includes('mode')) {
    result.setting = 'theme';
    
    // Extract value
    if (command.includes('dark')) {
      result.value = 'dark';
    } else if (command.includes('light')) {
      result.value = 'light';
    }
  }
  
  // Extract common parameters
  extractCommonParameters(command, result);
}

/**
 * Parse staking command parameters
 */
function parseStakingCommand(command: string, result: ParsedCommand): void {
  // Extract amount and token
  const amountTokenPattern = /(stake|unstake)\s+(?:(all|[\d.]+%?)\s+(?:of\s+my\s+)?)?([a-z0-9]+)(?:\s|$)/i;
  const amountTokenMatch = command.match(amountTokenPattern);
  
  if (amountTokenMatch) {
    // Handle "all" keyword
    if (amountTokenMatch[2] === 'all') {
      result.sourceAmountIsAll = true;
    } 
    // Handle percentage
    else if (amountTokenMatch[2] && amountTokenMatch[2].includes('%')) {
      result.sourceAmount = parseFloat(amountTokenMatch[2]);
      result.sourceAmountIsPercentage = true;
    } 
    // Handle numeric amount
    else if (amountTokenMatch[2]) {
      result.sourceAmount = parseFloat(amountTokenMatch[2]);
    }
    
    result.sourceToken = amountTokenMatch[3].toUpperCase();
  }
  
  // Extract common parameters
  extractCommonParameters(command, result);
}

/**
 * Parse liquidity provision command parameters
 */
function parseLiquidityCommand(command: string, result: ParsedCommand): void {
  // Extract token pair
  const tokenPairPattern = /(provide|add|remove|withdraw)\s+(?:liquidity\s+)?(?:for|from)?\s+([a-z0-9]+)\/([a-z0-9]+)(?:\s|$)/i;
  const tokenPairMatch = command.match(tokenPairPattern);
  
  if (tokenPairMatch) {
    result.sourceToken = tokenPairMatch[2].toUpperCase();
    result.targetToken = tokenPairMatch[3].toUpperCase();
  }
  
  // Extract amount for providing liquidity
  if (result.type === 'provide') {
    const amountPattern = /provide\s+([\d.]+)\s+([a-z0-9]+)(?:\s|$)/i;
    const amountMatch = command.match(amountPattern);
    
    if (amountMatch) {
      result.sourceAmount = parseFloat(amountMatch[1]);
      // If token wasn't extracted from pair pattern
      if (!result.sourceToken) {
        result.sourceToken = amountMatch[2].toUpperCase();
      }
    }
  }
  
  // Extract percentage for removing liquidity
  if (result.type === 'remove') {
    const percentPattern = /remove\s+([\d.]+)%/i;
    const percentMatch = command.match(percentPattern);
    
    if (percentMatch) {
      result.sourceAmount = parseFloat(percentMatch[1]);
      result.sourceAmountIsPercentage = true;
    } else if (command.includes('all')) {
      result.sourceAmountIsAll = true;
    }
  }
  
  // Extract common parameters
  extractCommonParameters(command, result);
}

/**
 * Parse lending command parameters
 */
function parseLendingCommand(command: string, result: ParsedCommand): void {
  if (result.type === 'borrow') {
    // Extract amount and token for borrowing
    const amountTokenPattern = /borrow\s+([\d.]+)\s+([a-z0-9]+)(?:\s|$)/i;
    const amountTokenMatch = command.match(amountTokenPattern);
    
    if (amountTokenMatch) {
      result.sourceAmount = parseFloat(amountTokenMatch[1]);
      result.sourceToken = amountTokenMatch[2].toUpperCase();
    }
    
    // Extract collateral token
    const collateralPattern = /against\s+([a-z0-9]+)(?:\s|$)/i;
    const collateralMatch = command.match(collateralPattern);
    
    if (collateralMatch) {
      result.params.collateralToken = collateralMatch[1].toUpperCase();
    }
  }
  
  if (result.type === 'repay') {
    // Extract amount and token for repaying
    const amountTokenPattern = /repay\s+([\d.]+)\s+([a-z0-9]+)(?:\s|$)/i;
    const amountTokenMatch = command.match(amountTokenPattern);
    
    if (amountTokenMatch) {
      result.sourceAmount = parseFloat(amountTokenMatch[1]);
      result.sourceToken = amountTokenMatch[2].toUpperCase();
    }
    
    // Check for "all" keyword
    if (command.includes('all')) {
      result.sourceAmountIsAll = true;
    }
  }
  
  // Extract common parameters
  extractCommonParameters(command, result);
}

/**
 * Extract common parameters that might appear in any command
 */
function extractCommonParameters(command: string, result: ParsedCommand): void {
  // Extract any chain references not already captured
  if (!result.sourceChain && !result.targetChain) {
    // Look for chain references
    for (const [chainId, chainName] of Object.entries(SUPPORTED_CHAINS)) {
      const chainNameLower = chainName.toLowerCase();
      if (command.includes(chainNameLower)) {
        // If we already found a source chain, this might be a target chain
        if (result.sourceChain) {
          result.targetChain = parseInt(chainId);
          break;
        } else {
          result.sourceChain = parseInt(chainId);
        }
      }
    }
  }
  
  // Extract any token references not already captured
  if (!result.sourceToken && !result.targetToken) {
    // Look for token references
    for (const token of POPULAR_TOKENS) {
      const tokenSymbolLower = token.symbol.toLowerCase();
      if (command.includes(tokenSymbolLower)) {
        // If we already found a source token, this might be a target token
        if (result.sourceToken) {
          result.targetToken = token.symbol;
          break;
        } else {
          result.sourceToken = token.symbol;
        }
      }
    }
  }
  
  // Extract any address references not already captured
  if (!result.recipientAddress) {
    // Look for ENS addresses
    const ensPattern = /([a-z0-9]+\.eth)(?:\s|$)/i;
    const ensMatch = command.match(ensPattern);
    
    if (ensMatch) {
      result.recipientAddress = ensMatch[1];
    }
    
    // Look for Ethereum addresses
    const addressPattern = /(0x[a-f0-9]{40})(?:\s|$)/i;
    const addressMatch = command.match(addressPattern);
    
    if (addressMatch) {
      result.recipientAddress = addressMatch[1];
    }
    
    // Look for common address names
    for (const address of COMMON_ADDRESSES) {
      const nameLower = address.name.toLowerCase();
      if (command.includes(nameLower)) {
        result.recipientAddress = address.ens || address.address;
        break;
      }
    }
  }
}

/**
 * Helper function to get chain ID by name
 */
function getChainIdByName(name: string): number | undefined {
  const normalizedName = name.toLowerCase();
  
  for (const [chainId, chainName] of Object.entries(SUPPORTED_CHAINS)) {
    if (chainName.toLowerCase() === normalizedName) {
      return parseInt(chainId);
    }
  }
  
  // Handle common chain name variations
  const chainAliases: Record<string, number> = {
    'eth': 1,
    'ethereum': 1,
    'matic': 137,
    'polygon': 137,
    'arb': 42161,
    'arbitrum': 42161,
    'op': 10,
    'optimism': 10,
    'avax': 43114,
    'avalanche': 43114,
    'bsc': 56,
    'binance': 56,
    'ftm': 250,
    'fantom': 250,
  };
  
  return chainAliases[normalizedName];
}

/**
 * Helper function to format a parsed command back to a string (for debugging)
 */
export function formatParsedCommand(parsed: ParsedCommand): string {
  let result = `Command Type: ${parsed.type}\n`;
  
  if (parsed.sourceToken) {
    let amount = 'all of';
    if (parsed.sourceAmount !== undefined) {
      amount = parsed.sourceAmountIsPercentage 
        ? `${parsed.sourceAmount}% of` 
        : `${parsed.sourceAmount}`;
    }
    
    result += `Source: ${parsed.sourceAmountIsAll ? 'all' : amount} ${parsed.sourceToken}\n`;
  }
  
  if (parsed.targetToken) {
    if (parsed.minTargetAmount !== undefined) {
      result += `Target: at least ${parsed.minTargetAmount} ${parsed.targetToken}\n`;
    } else {
      result += `Target: ${parsed.targetToken}\n`;
    }
  }
  
  if (parsed.recipientAddress) {
    result += `Recipient: ${parsed.recipientAddress}\n`;
  }
  
  if (parsed.sourceChain) {
    result += `Source Chain: ${SUPPORTED_CHAINS[parsed.sourceChain] || parsed.sourceChain}\n`;
  }
  
  if (parsed.targetChain) {
    result += `Target Chain: ${SUPPORTED_CHAINS[parsed.targetChain] || parsed.targetChain}\n`;
  }
  
  if (parsed.slippage !== undefined) {
    result += `Slippage: ${parsed.slippage}%\n`;
  }
  
  if (parsed.dex) {
    result += `DEX: ${parsed.dex}\n`;
  }
  
  if (parsed.message) {
    result += `Message: "${parsed.message}"\n`;
  }
  
  if (parsed.timeframe) {
    result += `Timeframe: ${parsed.timeframe}\n`;
  }
  
  if (parsed.metric) {
    result += `Metric: ${parsed.metric}\n`;
  }
  
  if (parsed.setting) {
    result += `Setting: ${parsed.setting} = ${parsed.value}\n`;
  }
  
  // Add any additional parameters
  for (const [key, value] of Object.entries(parsed.params)) {
    result += `${key}: ${value}\n`;
  }
  
  return result;
}

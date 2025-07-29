import { parseCommand, ParsedCommand, CommandType } from './commandParser';
import { POPULAR_TOKENS, getTokenBySymbol } from '../constants/tokens';
import { SUPPORTED_CHAINS, ChainId } from '../constants/chains';
import { COMMON_ADDRESSES, getAddressByENS, getAddressByAddress } from '../constants/addresses';

/**
 * Result of command validation
 */
export interface ValidationResult {
  isValid: boolean;
  message?: string;
  suggestion?: string;
  errorType?: ValidationErrorType;
  errorField?: string;
}

/**
 * Types of validation errors
 */
export type ValidationErrorType = 
  | 'missing_parameter'
  | 'invalid_token'
  | 'invalid_chain'
  | 'invalid_address'
  | 'invalid_amount'
  | 'insufficient_balance'
  | 'unsupported_operation'
  | 'syntax_error'
  | 'unknown_command';

/**
 * Validates a natural language command and provides helpful feedback
 * 
 * @param command The command string to validate
 * @returns Validation result with feedback
 */
export function validateCommand(command: string): ValidationResult {
  // Empty command is valid (no validation needed)
  if (!command.trim()) {
    return { isValid: true };
  }
  
  // Parse the command
  const parsed = parseCommand(command);
  
  // Unknown command type
  if (parsed.type === 'unknown') {
    return {
      isValid: false,
      message: "I don't recognize this command.",
      suggestion: "Try starting with actions like 'swap', 'send', 'bridge', 'check', or 'analyze'.",
      errorType: 'unknown_command'
    };
  }
  
  // Validate based on command type
  switch (parsed.type) {
    case 'swap':
      return validateSwapCommand(parsed);
    case 'bridge':
      return validateBridgeCommand(parsed);
    case 'send':
      return validateSendCommand(parsed);
    case 'analyze':
    case 'check':
      return validateAnalysisCommand(parsed);
    case 'set':
      return validateSettingCommand(parsed);
    case 'stake':
    case 'unstake':
      return validateStakingCommand(parsed);
    case 'provide':
    case 'remove':
      return validateLiquidityCommand(parsed);
    case 'borrow':
    case 'repay':
      return validateLendingCommand(parsed);
    default:
      // Basic validation for other command types
      return validateGenericCommand(parsed);
  }
}

/**
 * Validate swap command
 */
function validateSwapCommand(parsed: ParsedCommand): ValidationResult {
  // Check for source token
  if (!parsed.sourceToken) {
    return {
      isValid: false,
      message: "Please specify which token you want to swap.",
      suggestion: "For example: 'swap 0.1 ETH for USDC'",
      errorType: 'missing_parameter',
      errorField: 'sourceToken'
    };
  }
  
  // Check for target token
  if (!parsed.targetToken) {
    return {
      isValid: false,
      message: "Please specify which token you want to receive.",
      suggestion: `For example: 'swap ${parsed.sourceAmount || 0.1} ${parsed.sourceToken} for USDC'`,
      errorType: 'missing_parameter',
      errorField: 'targetToken'
    };
  }
  
  // Check if source token is valid
  const sourceTokenValid = isValidToken(parsed.sourceToken);
  if (!sourceTokenValid) {
    return {
      isValid: false,
      message: `'${parsed.sourceToken}' doesn't appear to be a valid token.`,
      suggestion: getSimilarTokenSuggestion(parsed.sourceToken),
      errorType: 'invalid_token',
      errorField: 'sourceToken'
    };
  }
  
  // Check if target token is valid
  const targetTokenValid = isValidToken(parsed.targetToken);
  if (!targetTokenValid) {
    return {
      isValid: false,
      message: `'${parsed.targetToken}' doesn't appear to be a valid token.`,
      suggestion: getSimilarTokenSuggestion(parsed.targetToken),
      errorType: 'invalid_token',
      errorField: 'targetToken'
    };
  }
  
  // Check for amount (unless using "all")
  if (!parsed.sourceAmountIsAll && parsed.sourceAmount === undefined) {
    return {
      isValid: false,
      message: "Please specify how much you want to swap.",
      suggestion: `For example: 'swap 0.1 ${parsed.sourceToken} for ${parsed.targetToken}'`,
      errorType: 'missing_parameter',
      errorField: 'sourceAmount'
    };
  }
  
  // Check for valid amount
  if (parsed.sourceAmount !== undefined && (parsed.sourceAmount <= 0 || !isFinite(parsed.sourceAmount))) {
    return {
      isValid: false,
      message: "Please enter a valid positive amount.",
      suggestion: `For example: 'swap 0.1 ${parsed.sourceToken} for ${parsed.targetToken}'`,
      errorType: 'invalid_amount',
      errorField: 'sourceAmount'
    };
  }
  
  // Check for valid slippage
  if (parsed.slippage !== undefined && (parsed.slippage < 0 || parsed.slippage > 100 || !isFinite(parsed.slippage))) {
    return {
      isValid: false,
      message: "Please enter a valid slippage percentage (between 0 and 100).",
      suggestion: `For example: 'swap ${parsed.sourceAmount || 0.1} ${parsed.sourceToken} for ${parsed.targetToken} with 0.5% slippage'`,
      errorType: 'invalid_amount',
      errorField: 'slippage'
    };
  }
  
  // Check for same source and target token
  if (parsed.sourceToken === parsed.targetToken) {
    return {
      isValid: false,
      message: "You can't swap a token for itself.",
      suggestion: `Try swapping ${parsed.sourceToken} for a different token.`,
      errorType: 'invalid_token',
      errorField: 'targetToken'
    };
  }
  
  // All checks passed
  return { isValid: true };
}

/**
 * Validate bridge command
 */
function validateBridgeCommand(parsed: ParsedCommand): ValidationResult {
  // Check for source token
  if (!parsed.sourceToken) {
    return {
      isValid: false,
      message: "Please specify which token you want to bridge.",
      suggestion: "For example: 'bridge 100 USDC from Ethereum to Polygon'",
      errorType: 'missing_parameter',
      errorField: 'sourceToken'
    };
  }
  
  // Check if source token is valid
  const sourceTokenValid = isValidToken(parsed.sourceToken);
  if (!sourceTokenValid) {
    return {
      isValid: false,
      message: `'${parsed.sourceToken}' doesn't appear to be a valid token.`,
      suggestion: getSimilarTokenSuggestion(parsed.sourceToken),
      errorType: 'invalid_token',
      errorField: 'sourceToken'
    };
  }
  
  // Check for amount (unless using "all")
  if (!parsed.sourceAmountIsAll && parsed.sourceAmount === undefined) {
    return {
      isValid: false,
      message: "Please specify how much you want to bridge.",
      suggestion: `For example: 'bridge 100 ${parsed.sourceToken} from Ethereum to Polygon'`,
      errorType: 'missing_parameter',
      errorField: 'sourceAmount'
    };
  }
  
  // Check for valid amount
  if (parsed.sourceAmount !== undefined && (parsed.sourceAmount <= 0 || !isFinite(parsed.sourceAmount))) {
    return {
      isValid: false,
      message: "Please enter a valid positive amount.",
      suggestion: `For example: 'bridge 100 ${parsed.sourceToken} from Ethereum to Polygon'`,
      errorType: 'invalid_amount',
      errorField: 'sourceAmount'
    };
  }
  
  // Check for source chain
  if (!parsed.sourceChain) {
    return {
      isValid: false,
      message: "Please specify the source chain.",
      suggestion: `For example: 'bridge ${parsed.sourceAmount || 100} ${parsed.sourceToken} from Ethereum to Polygon'`,
      errorType: 'missing_parameter',
      errorField: 'sourceChain'
    };
  }
  
  // Check for target chain
  if (!parsed.targetChain) {
    return {
      isValid: false,
      message: "Please specify the destination chain.",
      suggestion: `For example: 'bridge ${parsed.sourceAmount || 100} ${parsed.sourceToken} from ${SUPPORTED_CHAINS[parsed.sourceChain] || 'Ethereum'} to Polygon'`,
      errorType: 'missing_parameter',
      errorField: 'targetChain'
    };
  }
  
  // Check if source chain is valid
  if (!isValidChain(parsed.sourceChain)) {
    return {
      isValid: false,
      message: `'${parsed.sourceChain}' doesn't appear to be a supported chain.`,
      suggestion: getSimilarChainSuggestion(parsed.sourceChain),
      errorType: 'invalid_chain',
      errorField: 'sourceChain'
    };
  }
  
  // Check if target chain is valid
  if (!isValidChain(parsed.targetChain)) {
    return {
      isValid: false,
      message: `'${parsed.targetChain}' doesn't appear to be a supported chain.`,
      suggestion: getSimilarChainSuggestion(parsed.targetChain),
      errorType: 'invalid_chain',
      errorField: 'targetChain'
    };
  }
  
  // Check for same source and target chain
  if (parsed.sourceChain === parsed.targetChain) {
    return {
      isValid: false,
      message: "Source and destination chains can't be the same.",
      suggestion: `Try bridging from ${SUPPORTED_CHAINS[parsed.sourceChain]} to a different chain.`,
      errorType: 'invalid_chain',
      errorField: 'targetChain'
    };
  }
  
  // Check if recipient address is valid (if specified)
  if (parsed.recipientAddress && !isValidAddress(parsed.recipientAddress)) {
    return {
      isValid: false,
      message: `'${parsed.recipientAddress}' doesn't appear to be a valid address.`,
      suggestion: "Please provide a valid Ethereum address or ENS name.",
      errorType: 'invalid_address',
      errorField: 'recipientAddress'
    };
  }
  
  // All checks passed
  return { isValid: true };
}

/**
 * Validate send command
 */
function validateSendCommand(parsed: ParsedCommand): ValidationResult {
  // Check for source token
  if (!parsed.sourceToken) {
    return {
      isValid: false,
      message: "Please specify which token you want to send.",
      suggestion: "For example: 'send 0.1 ETH to vitalik.eth'",
      errorType: 'missing_parameter',
      errorField: 'sourceToken'
    };
  }
  
  // Check if source token is valid
  const sourceTokenValid = isValidToken(parsed.sourceToken);
  if (!sourceTokenValid) {
    return {
      isValid: false,
      message: `'${parsed.sourceToken}' doesn't appear to be a valid token.`,
      suggestion: getSimilarTokenSuggestion(parsed.sourceToken),
      errorType: 'invalid_token',
      errorField: 'sourceToken'
    };
  }
  
  // Check for amount (unless using "all")
  if (!parsed.sourceAmountIsAll && parsed.sourceAmount === undefined) {
    return {
      isValid: false,
      message: "Please specify how much you want to send.",
      suggestion: `For example: 'send 0.1 ${parsed.sourceToken} to vitalik.eth'`,
      errorType: 'missing_parameter',
      errorField: 'sourceAmount'
    };
  }
  
  // Check for valid amount
  if (parsed.sourceAmount !== undefined && (parsed.sourceAmount <= 0 || !isFinite(parsed.sourceAmount))) {
    return {
      isValid: false,
      message: "Please enter a valid positive amount.",
      suggestion: `For example: 'send 0.1 ${parsed.sourceToken} to vitalik.eth'`,
      errorType: 'invalid_amount',
      errorField: 'sourceAmount'
    };
  }
  
  // Check for recipient address
  if (!parsed.recipientAddress) {
    return {
      isValid: false,
      message: "Please specify a recipient address.",
      suggestion: `For example: 'send ${parsed.sourceAmount || 0.1} ${parsed.sourceToken} to vitalik.eth'`,
      errorType: 'missing_parameter',
      errorField: 'recipientAddress'
    };
  }
  
  // Check if recipient address is valid
  if (!isValidAddress(parsed.recipientAddress)) {
    return {
      isValid: false,
      message: `'${parsed.recipientAddress}' doesn't appear to be a valid address.`,
      suggestion: "Please provide a valid Ethereum address or ENS name.",
      errorType: 'invalid_address',
      errorField: 'recipientAddress'
    };
  }
  
  // Check if target chain is valid (if specified)
  if (parsed.targetChain && !isValidChain(parsed.targetChain)) {
    return {
      isValid: false,
      message: `'${parsed.targetChain}' doesn't appear to be a supported chain.`,
      suggestion: getSimilarChainSuggestion(parsed.targetChain),
      errorType: 'invalid_chain',
      errorField: 'targetChain'
    };
  }
  
  // All checks passed
  return { isValid: true };
}

/**
 * Validate analysis command
 */
function validateAnalysisCommand(parsed: ParsedCommand): ValidationResult {
  // Check analysis type
  const analysisType = parsed.params.analysisType;
  
  if (!analysisType) {
    return {
      isValid: false,
      message: "Please specify what you want to analyze or check.",
      suggestion: "For example: 'analyze my portfolio' or 'check ETH price'",
      errorType: 'missing_parameter',
      errorField: 'analysisType'
    };
  }
  
  // Specific validations based on analysis type
  switch (analysisType) {
    case 'portfolio':
      // Portfolio analysis is generally valid without additional parameters
      break;
      
    case 'balance':
      // If specific token is mentioned, validate it
      if (parsed.sourceToken && !isValidToken(parsed.sourceToken)) {
        return {
          isValid: false,
          message: `'${parsed.sourceToken}' doesn't appear to be a valid token.`,
          suggestion: getSimilarTokenSuggestion(parsed.sourceToken),
          errorType: 'invalid_token',
          errorField: 'sourceToken'
        };
      }
      
      // If specific address is mentioned, validate it
      if (parsed.params.targetAddress && !isValidAddress(parsed.params.targetAddress)) {
        return {
          isValid: false,
          message: `'${parsed.params.targetAddress}' doesn't appear to be a valid address.`,
          suggestion: "Please provide a valid Ethereum address or ENS name.",
          errorType: 'invalid_address',
          errorField: 'targetAddress'
        };
      }
      break;
      
    case 'price':
      // Check for token
      if (!parsed.sourceToken) {
        return {
          isValid: false,
          message: "Please specify which token's price you want to check.",
          suggestion: "For example: 'check ETH price'",
          errorType: 'missing_parameter',
          errorField: 'sourceToken'
        };
      }
      
      // Check if token is valid
      if (!isValidToken(parsed.sourceToken)) {
        return {
          isValid: false,
          message: `'${parsed.sourceToken}' doesn't appear to be a valid token.`,
          suggestion: getSimilarTokenSuggestion(parsed.sourceToken),
          errorType: 'invalid_token',
          errorField: 'sourceToken'
        };
      }
      break;
      
    case 'gas':
    case 'network':
      // If specific chain is mentioned, validate it
      if (parsed.sourceChain && !isValidChain(parsed.sourceChain)) {
        return {
          isValid: false,
          message: `'${parsed.sourceChain}' doesn't appear to be a supported chain.`,
          suggestion: getSimilarChainSuggestion(parsed.sourceChain),
          errorType: 'invalid_chain',
          errorField: 'sourceChain'
        };
      }
      break;
  }
  
  // All checks passed
  return { isValid: true };
}

/**
 * Validate setting command
 */
function validateSettingCommand(parsed: ParsedCommand): ValidationResult {
  // Check for setting type
  if (!parsed.setting) {
    return {
      isValid: false,
      message: "Please specify which setting you want to change.",
      suggestion: "For example: 'set default slippage to 0.5%'",
      errorType: 'missing_parameter',
      errorField: 'setting'
    };
  }
  
  // Check for setting value
  if (parsed.value === undefined) {
    return {
      isValid: false,
      message: "Please specify the value for this setting.",
      suggestion: `For example: 'set ${parsed.setting} to [value]'`,
      errorType: 'missing_parameter',
      errorField: 'value'
    };
  }
  
  // Specific validations based on setting type
  switch (parsed.setting) {
    case 'slippage':
      // Check for valid slippage value
      const slippage = Number(parsed.value);
      if (isNaN(slippage) || slippage < 0 || slippage > 100) {
        return {
          isValid: false,
          message: "Please enter a valid slippage percentage (between 0 and 100).",
          suggestion: "For example: 'set default slippage to 0.5%'",
          errorType: 'invalid_amount',
          errorField: 'value'
        };
      }
      break;
      
    case 'gasPrice':
      // Check for valid gas price option
      const validGasPriceOptions = ['fast', 'average', 'slow'];
      if (typeof parsed.value === 'string' && !validGasPriceOptions.includes(parsed.value)) {
        return {
          isValid: false,
          message: "Please enter a valid gas price option (fast, average, or slow).",
          suggestion: "For example: 'set gas price to fast'",
          errorType: 'invalid_amount',
          errorField: 'value'
        };
      }
      break;
      
    case 'theme':
      // Check for valid theme option
      const validThemeOptions = ['dark', 'light'];
      if (typeof parsed.value === 'string' && !validThemeOptions.includes(parsed.value)) {
        return {
          isValid: false,
          message: "Please enter a valid theme option (dark or light).",
          suggestion: "For example: 'switch to dark mode'",
          errorType: 'invalid_amount',
          errorField: 'value'
        };
      }
      break;
  }
  
  // All checks passed
  return { isValid: true };
}

/**
 * Validate staking command
 */
function validateStakingCommand(parsed: ParsedCommand): ValidationResult {
  // Check for source token
  if (!parsed.sourceToken) {
    return {
      isValid: false,
      message: `Please specify which token you want to ${parsed.type}.`,
      suggestion: `For example: '${parsed.type} 100 SNEL'`,
      errorType: 'missing_parameter',
      errorField: 'sourceToken'
    };
  }
  
  // Check if source token is valid
  const sourceTokenValid = isValidToken(parsed.sourceToken);
  if (!sourceTokenValid) {
    return {
      isValid: false,
      message: `'${parsed.sourceToken}' doesn't appear to be a valid token.`,
      suggestion: getSimilarTokenSuggestion(parsed.sourceToken),
      errorType: 'invalid_token',
      errorField: 'sourceToken'
    };
  }
  
  // Check for amount (unless using "all")
  if (!parsed.sourceAmountIsAll && parsed.sourceAmount === undefined) {
    return {
      isValid: false,
      message: `Please specify how much you want to ${parsed.type}.`,
      suggestion: `For example: '${parsed.type} 100 ${parsed.sourceToken}'`,
      errorType: 'missing_parameter',
      errorField: 'sourceAmount'
    };
  }
  
  // Check for valid amount
  if (parsed.sourceAmount !== undefined && (parsed.sourceAmount <= 0 || !isFinite(parsed.sourceAmount))) {
    return {
      isValid: false,
      message: "Please enter a valid positive amount.",
      suggestion: `For example: '${parsed.type} 100 ${parsed.sourceToken}'`,
      errorType: 'invalid_amount',
      errorField: 'sourceAmount'
    };
  }
  
  // All checks passed
  return { isValid: true };
}

/**
 * Validate liquidity command
 */
function validateLiquidityCommand(parsed: ParsedCommand): ValidationResult {
  // Check for source token
  if (!parsed.sourceToken) {
    return {
      isValid: false,
      message: "Please specify the first token in the pair.",
      suggestion: `For example: '${parsed.type} liquidity for ETH/USDC'`,
      errorType: 'missing_parameter',
      errorField: 'sourceToken'
    };
  }
  
  // Check for target token
  if (!parsed.targetToken) {
    return {
      isValid: false,
      message: "Please specify the second token in the pair.",
      suggestion: `For example: '${parsed.type} liquidity for ${parsed.sourceToken}/USDC'`,
      errorType: 'missing_parameter',
      errorField: 'targetToken'
    };
  }
  
  // Check if source token is valid
  const sourceTokenValid = isValidToken(parsed.sourceToken);
  if (!sourceTokenValid) {
    return {
      isValid: false,
      message: `'${parsed.sourceToken}' doesn't appear to be a valid token.`,
      suggestion: getSimilarTokenSuggestion(parsed.sourceToken),
      errorType: 'invalid_token',
      errorField: 'sourceToken'
    };
  }
  
  // Check if target token is valid
  const targetTokenValid = isValidToken(parsed.targetToken);
  if (!targetTokenValid) {
    return {
      isValid: false,
      message: `'${parsed.targetToken}' doesn't appear to be a valid token.`,
      suggestion: getSimilarTokenSuggestion(parsed.targetToken),
      errorType: 'invalid_token',
      errorField: 'targetToken'
    };
  }
  
  // Check for same source and target token
  if (parsed.sourceToken === parsed.targetToken) {
    return {
      isValid: false,
      message: "The two tokens in a liquidity pair must be different.",
      suggestion: `Try a different pair like ${parsed.sourceToken}/USDC.`,
      errorType: 'invalid_token',
      errorField: 'targetToken'
    };
  }
  
  // For remove liquidity, check for amount or "all"
  if (parsed.type === 'remove' && !parsed.sourceAmountIsAll && parsed.sourceAmount === undefined) {
    return {
      isValid: false,
      message: "Please specify how much liquidity you want to remove (or 'all').",
      suggestion: `For example: 'remove 50% liquidity from ${parsed.sourceToken}/${parsed.targetToken}'`,
      errorType: 'missing_parameter',
      errorField: 'sourceAmount'
    };
  }
  
  // Check for valid percentage (if specified)
  if (parsed.sourceAmountIsPercentage && (parsed.sourceAmount! <= 0 || parsed.sourceAmount! > 100 || !isFinite(parsed.sourceAmount!))) {
    return {
      isValid: false,
      message: "Please enter a valid percentage (between 0 and 100).",
      suggestion: `For example: 'remove 50% liquidity from ${parsed.sourceToken}/${parsed.targetToken}'`,
      errorType: 'invalid_amount',
      errorField: 'sourceAmount'
    };
  }
  
  // All checks passed
  return { isValid: true };
}

/**
 * Validate lending command
 */
function validateLendingCommand(parsed: ParsedCommand): ValidationResult {
  // Check for source token
  if (!parsed.sourceToken) {
    return {
      isValid: false,
      message: `Please specify which token you want to ${parsed.type}.`,
      suggestion: `For example: '${parsed.type} 1000 USDC${parsed.type === 'borrow' ? ' against ETH' : ''}'`,
      errorType: 'missing_parameter',
      errorField: 'sourceToken'
    };
  }
  
  // Check if source token is valid
  const sourceTokenValid = isValidToken(parsed.sourceToken);
  if (!sourceTokenValid) {
    return {
      isValid: false,
      message: `'${parsed.sourceToken}' doesn't appear to be a valid token.`,
      suggestion: getSimilarTokenSuggestion(parsed.sourceToken),
      errorType: 'invalid_token',
      errorField: 'sourceToken'
    };
  }
  
  // Check for amount (unless using "all")
  if (!parsed.sourceAmountIsAll && parsed.sourceAmount === undefined) {
    return {
      isValid: false,
      message: `Please specify how much you want to ${parsed.type}.`,
      suggestion: `For example: '${parsed.type} 1000 ${parsed.sourceToken}${parsed.type === 'borrow' ? ' against ETH' : ''}'`,
      errorType: 'missing_parameter',
      errorField: 'sourceAmount'
    };
  }
  
  // Check for valid amount
  if (parsed.sourceAmount !== undefined && (parsed.sourceAmount <= 0 || !isFinite(parsed.sourceAmount))) {
    return {
      isValid: false,
      message: "Please enter a valid positive amount.",
      suggestion: `For example: '${parsed.type} 1000 ${parsed.sourceToken}${parsed.type === 'borrow' ? ' against ETH' : ''}'`,
      errorType: 'invalid_amount',
      errorField: 'sourceAmount'
    };
  }
  
  // For borrow commands, check for collateral token
  if (parsed.type === 'borrow' && !parsed.params.collateralToken) {
    return {
      isValid: false,
      message: "Please specify which token you want to use as collateral.",
      suggestion: `For example: 'borrow ${parsed.sourceAmount || 1000} ${parsed.sourceToken} against ETH'`,
      errorType: 'missing_parameter',
      errorField: 'collateralToken'
    };
  }
  
  // Check if collateral token is valid
  if (parsed.params.collateralToken && !isValidToken(parsed.params.collateralToken)) {
    return {
      isValid: false,
      message: `'${parsed.params.collateralToken}' doesn't appear to be a valid token.`,
      suggestion: getSimilarTokenSuggestion(parsed.params.collateralToken),
      errorType: 'invalid_token',
      errorField: 'collateralToken'
    };
  }
  
  // All checks passed
  return { isValid: true };
}

/**
 * Validate generic command (basic validation for other command types)
 */
function validateGenericCommand(parsed: ParsedCommand): ValidationResult {
  // Validate any tokens mentioned
  if (parsed.sourceToken && !isValidToken(parsed.sourceToken)) {
    return {
      isValid: false,
      message: `'${parsed.sourceToken}' doesn't appear to be a valid token.`,
      suggestion: getSimilarTokenSuggestion(parsed.sourceToken),
      errorType: 'invalid_token',
      errorField: 'sourceToken'
    };
  }
  
  if (parsed.targetToken && !isValidToken(parsed.targetToken)) {
    return {
      isValid: false,
      message: `'${parsed.targetToken}' doesn't appear to be a valid token.`,
      suggestion: getSimilarTokenSuggestion(parsed.targetToken),
      errorType: 'invalid_token',
      errorField: 'targetToken'
    };
  }
  
  // Validate any chains mentioned
  if (parsed.sourceChain && !isValidChain(parsed.sourceChain)) {
    return {
      isValid: false,
      message: `'${parsed.sourceChain}' doesn't appear to be a supported chain.`,
      suggestion: getSimilarChainSuggestion(parsed.sourceChain),
      errorType: 'invalid_chain',
      errorField: 'sourceChain'
    };
  }
  
  if (parsed.targetChain && !isValidChain(parsed.targetChain)) {
    return {
      isValid: false,
      message: `'${parsed.targetChain}' doesn't appear to be a supported chain.`,
      suggestion: getSimilarChainSuggestion(parsed.targetChain),
      errorType: 'invalid_chain',
      errorField: 'targetChain'
    };
  }
  
  // Validate any addresses mentioned
  if (parsed.recipientAddress && !isValidAddress(parsed.recipientAddress)) {
    return {
      isValid: false,
      message: `'${parsed.recipientAddress}' doesn't appear to be a valid address.`,
      suggestion: "Please provide a valid Ethereum address or ENS name.",
      errorType: 'invalid_address',
      errorField: 'recipientAddress'
    };
  }
  
  // All checks passed
  return { isValid: true };
}

/**
 * Check if a token symbol is valid
 */
function isValidToken(symbol: string): boolean {
  if (!symbol) return false;
  
  // Normalize symbol
  const normalizedSymbol = symbol.toUpperCase();
  
  // Check if token exists in our list
  return POPULAR_TOKENS.some(token => token.symbol.toUpperCase() === normalizedSymbol);
}

/**
 * Check if a chain ID is valid
 */
function isValidChain(chainId: number): boolean {
  if (!chainId) return false;
  
  // Check if chain exists in our supported chains
  return Object.keys(SUPPORTED_CHAINS).includes(chainId.toString());
}

/**
 * Check if an address is valid
 */
function isValidAddress(address: string): boolean {
  if (!address) return false;
  
  // Check if it's a valid ENS name
  if (address.endsWith('.eth')) {
    return true;
  }
  
  // Check if it's a valid Ethereum address
  if (/^0x[a-fA-F0-9]{40}$/.test(address)) {
    return true;
  }
  
  // Check if it's a known address name
  return COMMON_ADDRESSES.some(
    addr => addr.name.toLowerCase() === address.toLowerCase()
  );
}

/**
 * Get suggestion for similar token
 */
function getSimilarTokenSuggestion(invalidToken: string): string {
  const normalizedInvalid = invalidToken.toUpperCase();
  
  // Find similar tokens based on string similarity
  const similarTokens = POPULAR_TOKENS
    .filter(token => {
      const similarity = calculateStringSimilarity(normalizedInvalid, token.symbol.toUpperCase());
      return similarity > 0.5; // Threshold for similarity
    })
    .slice(0, 3) // Get top 3 similar tokens
    .map(token => token.symbol);
  
  if (similarTokens.length > 0) {
    return `Did you mean ${similarTokens.join(', ')}?`;
  }
  
  // If no similar tokens found, suggest popular tokens
  const popularTokens = POPULAR_TOKENS
    .filter(token => token.isPopular)
    .slice(0, 3)
    .map(token => token.symbol);
  
  return `Try using a popular token like ${popularTokens.join(', ')}.`;
}

/**
 * Get suggestion for similar chain
 */
function getSimilarChainSuggestion(invalidChain: number | string): string {
  const chainName = typeof invalidChain === 'number' 
    ? invalidChain.toString()
    : invalidChain;
  
  const normalizedInvalid = chainName.toLowerCase();
  
  // Find similar chains based on string similarity
  const similarChains = Object.entries(SUPPORTED_CHAINS)
    .filter(([_, name]) => {
      const similarity = calculateStringSimilarity(normalizedInvalid, name.toLowerCase());
      return similarity > 0.5; // Threshold for similarity
    })
    .slice(0, 3) // Get top 3 similar chains
    .map(([_, name]) => name);
  
  if (similarChains.length > 0) {
    return `Did you mean ${similarChains.join(', ')}?`;
  }
  
  // If no similar chains found, suggest popular chains
  return `Try using a supported chain like Ethereum, Polygon, or Arbitrum.`;
}

/**
 * Calculate string similarity (simple Levenshtein distance-based similarity)
 */
function calculateStringSimilarity(a: string, b: string): number {
  if (a === b) return 1;
  if (a.length === 0 || b.length === 0) return 0;
  
  const matrix = Array(a.length + 1).fill(null).map(() => Array(b.length + 1).fill(null));
  
  for (let i = 0; i <= a.length; i++) {
    matrix[i][0] = i;
  }
  
  for (let j = 0; j <= b.length; j++) {
    matrix[0][j] = j;
  }
  
  for (let i = 1; i <= a.length; i++) {
    for (let j = 1; j <= b.length; j++) {
      const cost = a[i - 1] === b[j - 1] ? 0 : 1;
      matrix[i][j] = Math.min(
        matrix[i - 1][j] + 1,      // deletion
        matrix[i][j - 1] + 1,      // insertion
        matrix[i - 1][j - 1] + cost // substitution
      );
    }
  }
  
  const distance = matrix[a.length][b.length];
  const maxLength = Math.max(a.length, b.length);
  
  // Return similarity as a value between 0 and 1
  return 1 - distance / maxLength;
}

/**
 * Get a user-friendly validation message
 */
export function getValidationMessage(result: ValidationResult): string {
  if (result.isValid) {
    return "Command is valid.";
  }
  
  let message = result.message || "Invalid command.";
  
  if (result.suggestion) {
    message += ` ${result.suggestion}`;
  }
  
  return message;
}

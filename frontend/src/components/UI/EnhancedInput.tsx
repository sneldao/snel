import React, { useState, useEffect, useRef, forwardRef } from 'react';
import {
  Input,
  InputGroup,
  InputLeftElement,
  InputRightElement,
  InputLeftAddon,
  InputRightAddon,
  FormControl,
  FormLabel,
  FormErrorMessage,
  FormHelperText,
  Box,
  Text,
  Flex,
  Icon,
  Button,
  Tooltip,
  Spinner,
  IconButton,
  useColorModeValue,
  InputProps as ChakraInputProps,
  FormControlProps,
  Collapse,
  Progress,
  useClipboard,
  Popover,
  PopoverTrigger,
  PopoverContent,
  PopoverBody,
  PopoverArrow,
  List,
  ListItem,
  VisuallyHidden,
  useTheme,
  chakra,
  ThemingProps,
} from '@chakra-ui/react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  FaCheck,
  FaTimes,
  FaExclamationTriangle,
  FaEye,
  FaEyeSlash,
  FaSearch,
  FaCopy,
  FaPaste,
  FaWallet,
  FaCoins,
  FaPercentage,
  FaDollarSign,
  FaEthereum,
} from 'react-icons/fa';
import { useForm, Controller, UseFormReturn, FieldValues, FieldPath } from 'react-hook-form';
import { ethers } from 'ethers';

// ========== Types & Interfaces ==========

export type InputVariant = 'default' | 'filled' | 'outlined' | 'flushed' | 'floating';
export type InputSize = 'sm' | 'md' | 'lg';
export type ValidationState = 'valid' | 'invalid' | 'warning' | 'none';
export type InputType = 
  | 'text'
  | 'password'
  | 'number'
  | 'email'
  | 'search'
  | 'token'
  | 'address'
  | 'currency'
  | 'percentage';

export interface ValidationRule {
  test: (value: any) => boolean;
  message: string;
  type?: ValidationState;
}

export interface ValidationResult {
  isValid: boolean;
  message?: string;
  type?: ValidationState;
}

export interface TokenData {
  symbol: string;
  name: string;
  decimals: number;
  balance?: string;
  icon?: string;
  address?: string;
}

export interface AutocompleteOption {
  value: string;
  label: string;
  icon?: React.ReactNode;
  description?: string;
}

export interface EnhancedInputProps extends Omit<ChakraInputProps, 'size' | 'variant'> {
  // Base props
  name: string;
  label?: string;
  helperText?: string;
  errorText?: string;
  warningText?: string;
  successText?: string;
  placeholder?: string;
  
  // Styling props
  variant?: InputVariant;
  size?: InputSize;
  validationState?: ValidationState;
  isRequired?: boolean;
  isReadOnly?: boolean;
  isFullWidth?: boolean;
  
  // Icon props
  leftIcon?: React.ReactElement;
  rightIcon?: React.ReactElement;
  leftAddon?: React.ReactNode;
  rightAddon?: React.ReactNode;
  
  // Validation props
  validationRules?: ValidationRule[];
  validateOnBlur?: boolean;
  validateOnChange?: boolean;
  asyncValidator?: (value: any) => Promise<ValidationResult>;
  
  // Special input types
  inputType?: InputType;
  
  // Token input props
  token?: TokenData;
  showMaxButton?: boolean;
  onMaxClick?: () => void;
  
  // Address input props
  resolveEns?: boolean;
  chainId?: number;
  
  // Search input props
  autocompleteOptions?: AutocompleteOption[];
  onSearch?: (value: string) => void;
  
  // Password props
  showPasswordStrength?: boolean;
  
  // Numeric input props
  allowNegative?: boolean;
  precision?: number;
  currencySymbol?: string;
  
  // Animation props
  animate?: boolean;
  animateLabel?: boolean;
  
  // Form integration
  formControl?: UseFormReturn<any, any>;
  
  // Accessibility
  ariaLabel?: string;
  ariaDescribedBy?: string;
  
  // Callbacks
  onValueChange?: (value: any) => void;
  onValidationChange?: (result: ValidationResult) => void;
  onCopy?: () => void;
  onPaste?: () => void;
}

// ========== Animation Variants ==========

const floatingLabelVariants = {
  idle: {
    y: 0,
    scale: 1,
    color: 'inherit',
  },
  focus: {
    y: -22,
    scale: 0.85,
    color: 'var(--chakra-colors-blue-500)',
  },
};

const validationIconVariants = {
  initial: { opacity: 0, scale: 0 },
  animate: { opacity: 1, scale: 1, transition: { type: 'spring', stiffness: 500, damping: 15 } },
  exit: { opacity: 0, scale: 0, transition: { duration: 0.2 } },
};

const autocompleteVariants = {
  hidden: { opacity: 0, y: -10 },
  visible: { opacity: 1, y: 0, transition: { type: 'spring', stiffness: 500, damping: 15 } },
  exit: { opacity: 0, y: -10, transition: { duration: 0.2 } },
};

// ========== Helper Components ==========

const MotionBox = motion(Box);
const MotionFlex = motion(Flex);
const MotionText = motion(Text);
const MotionInput = motion(Input);

// ========== Helper Functions ==========

const validateAddress = (address: string): boolean => {
  try {
    return ethers.utils.isAddress(address);
  } catch (error) {
    return false;
  }
};

const formatCurrency = (value: string, precision: number = 2): string => {
  if (!value) return '';
  
  const number = parseFloat(value);
  if (isNaN(number)) return value;
  
  return number.toLocaleString('en-US', {
    minimumFractionDigits: precision,
    maximumFractionDigits: precision,
  });
};

const formatPercentage = (value: string): string => {
  if (!value) return '';
  
  const number = parseFloat(value);
  if (isNaN(number)) return value;
  
  return `${number.toFixed(2)}%`;
};

const formatTokenAmount = (value: string, decimals: number = 18): string => {
  if (!value) return '0';
  
  try {
    const number = parseFloat(value);
    if (isNaN(number)) return '0';
    
    // Format with appropriate decimal places based on token decimals
    const displayDecimals = Math.min(decimals, 8); // Cap at 8 decimal places for display
    return number.toLocaleString('en-US', {
      minimumFractionDigits: 0,
      maximumFractionDigits: displayDecimals,
    });
  } catch (error) {
    return '0';
  }
};

const calculatePasswordStrength = (password: string): number => {
  if (!password) return 0;
  
  let strength = 0;
  
  // Length check
  if (password.length >= 8) strength += 20;
  if (password.length >= 12) strength += 10;
  
  // Complexity checks
  if (/[a-z]/.test(password)) strength += 10; // lowercase
  if (/[A-Z]/.test(password)) strength += 10; // uppercase
  if (/[0-9]/.test(password)) strength += 10; // numbers
  if (/[^a-zA-Z0-9]/.test(password)) strength += 20; // special chars
  
  // Variety check
  const uniqueChars = new Set(password).size;
  strength += Math.min(20, uniqueChars * 2);
  
  return Math.min(100, strength);
};

// ========== Specialized Input Components ==========

// Token Amount Input Component
const TokenAmountInput = forwardRef<HTMLInputElement, EnhancedInputProps>((props, ref) => {
  const {
    token,
    showMaxButton,
    onMaxClick,
    size = 'md',
    onChange,
    value,
    precision = 6,
    isDisabled,
    isReadOnly,
    ...rest
  } = props;
  
  const handleMaxClick = () => {
    if (onMaxClick && token?.balance) {
      onMaxClick();
    }
  };
  
  const formattedBalance = token?.balance 
    ? formatTokenAmount(token.balance, token.decimals) 
    : '0';
  
  const balanceColor = useColorModeValue('gray.600', 'gray.400');
  const tokenBgColor = useColorModeValue('gray.100', 'gray.700');
  
  return (
    <Box>
      <InputGroup size={size}>
        <Input
          ref={ref}
          type="number"
          step={`0.${'0'.repeat(precision - 1)}1`}
          onChange={onChange}
          value={value}
          isDisabled={isDisabled}
          isReadOnly={isReadOnly}
          {...rest}
        />
        <InputRightElement width="auto" pr={2}>
          <Flex align="center">
            {showMaxButton && token?.balance && (
              <Button
                size="xs"
                onClick={handleMaxClick}
                mr={2}
                isDisabled={isDisabled || isReadOnly}
              >
                MAX
              </Button>
            )}
            {token && (
              <Flex
                align="center"
                bg={tokenBgColor}
                px={2}
                py={1}
                borderRadius="md"
              >
                {token.icon && (
                  <Box mr={1} boxSize={size === 'sm' ? '14px' : size === 'lg' ? '24px' : '18px'}>
                    <img src={token.icon} alt={token.symbol} style={{ width: '100%', height: '100%' }} />
                  </Box>
                )}
                <Text fontWeight="medium">{token.symbol}</Text>
              </Flex>
            )}
          </Flex>
        </InputRightElement>
      </InputGroup>
      
      {token?.balance && (
        <Flex justify="flex-end" mt={1}>
          <Text fontSize="xs" color={balanceColor}>
            Balance: {formattedBalance} {token.symbol}
          </Text>
        </Flex>
      )}
    </Box>
  );
});

// Address Input Component
const AddressInput = forwardRef<HTMLInputElement, EnhancedInputProps>((props, ref) => {
  const {
    value = '',
    onChange,
    resolveEns = true,
    chainId = 1,
    isDisabled,
    isReadOnly,
    size = 'md',
    ...rest
  } = props;
  
  const [ensName, setEnsName] = useState<string | null>(null);
  const [isResolving, setIsResolving] = useState(false);
  const [isValidAddress, setIsValidAddress] = useState(false);
  
  useEffect(() => {
    const checkAddress = async () => {
      if (!value) {
        setIsValidAddress(false);
        setEnsName(null);
        return;
      }
      
      // Check if it's a valid Ethereum address
      const isEthAddress = validateAddress(value as string);
      setIsValidAddress(isEthAddress);
      
      // If it might be an ENS name and resolution is enabled
      if (resolveEns && !isEthAddress && (value as string).includes('.eth')) {
        setIsResolving(true);
        try {
          // In a real implementation, you would use a provider to resolve ENS
          // This is a placeholder for demonstration
          setTimeout(() => {
            // Simulate ENS resolution
            const mockAddress = '0x' + '1'.repeat(40);
            setIsValidAddress(true);
            setIsResolving(false);
          }, 1000);
        } catch (error) {
          setIsValidAddress(false);
          setIsResolving(false);
        }
      } else if (resolveEns && isEthAddress) {
        // Reverse lookup - get ENS for address
        setIsResolving(true);
        try {
          // In a real implementation, you would use a provider to lookup ENS
          // This is a placeholder for demonstration
          setTimeout(() => {
            // Simulate ENS lookup (only sometimes finds a name)
            if (Math.random() > 0.5) {
              setEnsName('example.eth');
            } else {
              setEnsName(null);
            }
            setIsResolving(false);
          }, 800);
        } catch (error) {
          setEnsName(null);
          setIsResolving(false);
        }
      }
    };
    
    checkAddress();
  }, [value, resolveEns, chainId]);
  
  const addressBgColor = useColorModeValue('gray.100', 'gray.700');
  
  return (
    <InputGroup size={size}>
      <InputLeftElement>
        <Icon as={FaWallet} color={isValidAddress ? 'green.500' : 'gray.400'} />
      </InputLeftElement>
      <Input
        ref={ref}
        value={value}
        onChange={onChange}
        isDisabled={isDisabled}
        isReadOnly={isReadOnly}
        {...rest}
      />
      <InputRightElement width="auto" pr={2}>
        {isResolving ? (
          <Spinner size="sm" />
        ) : ensName ? (
          <Flex
            align="center"
            bg={addressBgColor}
            px={2}
            py={1}
            borderRadius="md"
            fontSize="sm"
          >
            <Icon as={FaEthereum} mr={1} />
            <Text>{ensName}</Text>
          </Flex>
        ) : isValidAddress ? (
          <Icon as={FaCheck} color="green.500" />
        ) : value ? (
          <Icon as={FaTimes} color="red.500" />
        ) : null}
      </InputRightElement>
    </InputGroup>
  );
});

// Search Input Component
const SearchInput = forwardRef<HTMLInputElement, EnhancedInputProps>((props, ref) => {
  const {
    value = '',
    onChange,
    onSearch,
    autocompleteOptions = [],
    isDisabled,
    isReadOnly,
    size = 'md',
    ...rest
  } = props;
  
  const [showOptions, setShowOptions] = useState(false);
  const [filteredOptions, setFilteredOptions] = useState<AutocompleteOption[]>([]);
  const inputRef = useRef<HTMLInputElement>(null);
  
  // Combine refs
  const combinedRef = (node: HTMLInputElement) => {
    // Forward the ref
    if (typeof ref === 'function') {
      ref(node);
    } else if (ref) {
      (ref as React.MutableRefObject<HTMLInputElement | null>).current = node;
    }
    
    // Set the local ref
    inputRef.current = node;
  };
  
  useEffect(() => {
    if (!value) {
      setFilteredOptions([]);
      return;
    }
    
    const filtered = autocompleteOptions.filter(option =>
      option.label.toLowerCase().includes((value as string).toLowerCase()) ||
      option.value.toLowerCase().includes((value as string).toLowerCase())
    );
    
    setFilteredOptions(filtered.slice(0, 5)); // Limit to 5 suggestions
  }, [value, autocompleteOptions]);
  
  const handleOptionSelect = (option: AutocompleteOption) => {
    if (onChange) {
      const event = {
        target: { value: option.value }
      } as React.ChangeEvent<HTMLInputElement>;
      
      onChange(event);
    }
    
    if (onSearch) {
      onSearch(option.value);
    }
    
    setShowOptions(false);
  };
  
  const handleInputFocus = () => {
    setShowOptions(true);
  };
  
  const handleInputBlur = () => {
    // Delay hiding to allow for option clicks
    setTimeout(() => setShowOptions(false), 200);
  };
  
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && onSearch) {
      onSearch(value as string);
    }
  };
  
  const bgColor = useColorModeValue('white', 'gray.800');
  const hoverBgColor = useColorModeValue('gray.100', 'gray.700');
  
  return (
    <Box position="relative">
      <InputGroup size={size}>
        <InputLeftElement>
          <Icon as={FaSearch} color="gray.400" />
        </InputLeftElement>
        <Input
          ref={combinedRef}
          value={value}
          onChange={onChange}
          onFocus={handleInputFocus}
          onBlur={handleInputBlur}
          onKeyDown={handleKeyDown}
          isDisabled={isDisabled}
          isReadOnly={isReadOnly}
          {...rest}
        />
        {value && (
          <InputRightElement>
            <IconButton
              aria-label="Clear search"
              icon={<FaTimes />}
              size="sm"
              variant="ghost"
              onClick={() => {
                if (onChange) {
                  const event = {
                    target: { value: '' }
                  } as React.ChangeEvent<HTMLInputElement>;
                  onChange(event);
                }
                inputRef.current?.focus();
              }}
            />
          </InputRightElement>
        )}
      </InputGroup>
      
      <AnimatePresence>
        {showOptions && filteredOptions.length > 0 && (
          <MotionBox
            position="absolute"
            top="100%"
            left={0}
            right={0}
            zIndex={10}
            mt={1}
            bg={bgColor}
            boxShadow="md"
            borderRadius="md"
            overflow="hidden"
            variants={autocompleteVariants}
            initial="hidden"
            animate="visible"
            exit="exit"
          >
            <List spacing={0}>
              {filteredOptions.map((option, index) => (
                <ListItem
                  key={index}
                  px={4}
                  py={2}
                  cursor="pointer"
                  _hover={{ bg: hoverBgColor }}
                  onClick={() => handleOptionSelect(option)}
                >
                  <Flex align="center">
                    {option.icon && <Box mr={2}>{option.icon}</Box>}
                    <Box>
                      <Text fontWeight="medium">{option.label}</Text>
                      {option.description && (
                        <Text fontSize="xs" color="gray.500">
                          {option.description}
                        </Text>
                      )}
                    </Box>
                  </Flex>
                </ListItem>
              ))}
            </List>
          </MotionBox>
        )}
      </AnimatePresence>
    </Box>
  );
});

// Password Input Component
const PasswordInput = forwardRef<HTMLInputElement, EnhancedInputProps>((props, ref) => {
  const {
    value = '',
    onChange,
    showPasswordStrength = true,
    isDisabled,
    isReadOnly,
    size = 'md',
    ...rest
  } = props;
  
  const [showPassword, setShowPassword] = useState(false);
  const [strength, setStrength] = useState(0);
  
  useEffect(() => {
    if (showPasswordStrength && value) {
      setStrength(calculatePasswordStrength(value as string));
    }
  }, [value, showPasswordStrength]);
  
  const getStrengthColor = () => {
    if (strength < 30) return 'red.500';
    if (strength < 60) return 'orange.500';
    if (strength < 80) return 'yellow.500';
    return 'green.500';
  };
  
  const getStrengthText = () => {
    if (strength < 30) return 'Weak';
    if (strength < 60) return 'Fair';
    if (strength < 80) return 'Good';
    return 'Strong';
  };
  
  return (
    <Box>
      <InputGroup size={size}>
        <Input
          ref={ref}
          type={showPassword ? 'text' : 'password'}
          value={value}
          onChange={onChange}
          isDisabled={isDisabled}
          isReadOnly={isReadOnly}
          {...rest}
        />
        <InputRightElement>
          <IconButton
            aria-label={showPassword ? 'Hide password' : 'Show password'}
            icon={showPassword ? <FaEyeSlash /> : <FaEye />}
            size="sm"
            variant="ghost"
            onClick={() => setShowPassword(!showPassword)}
            isDisabled={isDisabled || isReadOnly}
          />
        </InputRightElement>
      </InputGroup>
      
      {showPasswordStrength && value && (
        <Box mt={2}>
          <Flex align="center" justify="space-between" mb={1}>
            <Text fontSize="xs" color={getStrengthColor()}>
              Password strength: {getStrengthText()}
            </Text>
            <Text fontSize="xs">{strength}%</Text>
          </Flex>
          <Progress
            value={strength}
            size="xs"
            colorScheme={
              strength < 30 ? 'red' :
              strength < 60 ? 'orange' :
              strength < 80 ? 'yellow' : 'green'
            }
            borderRadius="full"
          />
        </Box>
      )}
    </Box>
  );
});

// Currency Input Component
const CurrencyInput = forwardRef<HTMLInputElement, EnhancedInputProps>((props, ref) => {
  const {
    value = '',
    onChange,
    currencySymbol = '$',
    precision = 2,
    allowNegative = false,
    isDisabled,
    isReadOnly,
    size = 'md',
    ...rest
  } = props;
  
  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const inputValue = e.target.value;
    
    // Remove currency symbol, commas, and other non-numeric characters
    let numericValue = inputValue.replace(/[^0-9.-]/g, '');
    
    // Handle negative values
    if (!allowNegative && numericValue.includes('-')) {
      numericValue = numericValue.replace(/-/g, '');
    }
    
    // Ensure only one decimal point
    const parts = numericValue.split('.');
    if (parts.length > 2) {
      numericValue = `${parts[0]}.${parts.slice(1).join('')}`;
    }
    
    // Update the input with the raw numeric value
    if (onChange) {
      const event = {
        ...e,
        target: {
          ...e.target,
          value: numericValue
        }
      };
      onChange(event);
    }
  };
  
  return (
    <InputGroup size={size}>
      <InputLeftElement>
        <Text>{currencySymbol}</Text>
      </InputLeftElement>
      <Input
        ref={ref}
        value={value}
        onChange={handleChange}
        isDisabled={isDisabled}
        isReadOnly={isReadOnly}
        pl={8} // Make room for the currency symbol
        {...rest}
      />
    </InputGroup>
  );
});

// Percentage Input Component
const PercentageInput = forwardRef<HTMLInputElement, EnhancedInputProps>((props, ref) => {
  const {
    value = '',
    onChange,
    precision = 2,
    isDisabled,
    isReadOnly,
    size = 'md',
    ...rest
  } = props;
  
  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const inputValue = e.target.value;
    
    // Remove percentage sign and other non-numeric characters
    let numericValue = inputValue.replace(/[^0-9.-]/g, '');
    
    // Ensure only one decimal point
    const parts = numericValue.split('.');
    if (parts.length > 2) {
      numericValue = `${parts[0]}.${parts.slice(1).join('')}`;
    }
    
    // Limit to reasonable percentage values
    const parsedValue = parseFloat(numericValue);
    if (!isNaN(parsedValue) && parsedValue > 100) {
      numericValue = '100';
    }
    
    // Update the input with the raw numeric value
    if (onChange) {
      const event = {
        ...e,
        target: {
          ...e.target,
          value: numericValue
        }
      };
      onChange(event);
    }
  };
  
  return (
    <InputGroup size={size}>
      <Input
        ref={ref}
        value={value}
        onChange={handleChange}
        isDisabled={isDisabled}
        isReadOnly={isReadOnly}
        {...rest}
      />
      <InputRightElement>
        <Icon as={FaPercentage} color="gray.500" />
      </InputRightElement>
    </InputGroup>
  );
});

// ------------------------------------------------------------------
// Attach display names to forwardRef components for better debugging
// ------------------------------------------------------------------

TokenAmountInput.displayName   = 'TokenAmountInput';
AddressInput.displayName       = 'AddressInput';
SearchInput.displayName        = 'SearchInput';
PasswordInput.displayName      = 'PasswordInput';
CurrencyInput.displayName      = 'CurrencyInput';
PercentageInput.displayName    = 'PercentageInput';

// ========== Main Component ==========

export const EnhancedInput = forwardRef<HTMLInputElement, EnhancedInputProps>((props, ref) => {
  const {
    // Base props
    name,
    label,
    helperText,
    errorText,
    warningText,
    successText,
    placeholder,
    value = '',
    defaultValue,
    onChange,
    onFocus,
    onBlur,
    
    // Styling props
    variant = 'default',
    size = 'md',
    validationState = 'none',
    isRequired = false,
    isReadOnly = false,
    isDisabled = false,
    isFullWidth = true,
    
    // Icon props
    leftIcon,
    rightIcon,
    leftAddon,
    rightAddon,
    
    // Validation props
    validationRules = [],
    validateOnBlur = true,
    validateOnChange = false,
    asyncValidator,
    
    // Special input types
    inputType = 'text',
    
    // Token input props
    token,
    showMaxButton,
    onMaxClick,
    
    // Address input props
    resolveEns,
    chainId,
    
    // Search input props
    autocompleteOptions,
    onSearch,
    
    // Password props
    showPasswordStrength,
    
    // Numeric input props
    allowNegative,
    precision,
    currencySymbol,
    
    // Animation props
    animate = true,
    animateLabel = true,
    
    // Form integration
    formControl,
    
    // Accessibility
    ariaLabel,
    ariaDescribedBy,
    
    // Callbacks
    onValueChange,
    onValidationChange,
    onCopy,
    onPaste,
    
    // Rest of props
    ...rest
  } = props;
  
  // State
  const [localValidationState, setLocalValidationState] = useState<ValidationState>(validationState);
  const [validationMessage, setValidationMessage] = useState<string>('');
  const [isFocused, setIsFocused] = useState(false);
  const [isValidating, setIsValidating] = useState(false);
  const [localValue, setLocalValue] = useState<any>(value || defaultValue || '');
  
  // Refs
  const inputRef = useRef<HTMLInputElement>(null);
  
  // Hooks
  const { hasCopied, onCopy: copyToClipboard } = useClipboard(localValue as string);
  
  // Theme values
  const theme = useTheme();
  const floatingLabelColor = useColorModeValue('gray.600', 'gray.400');
  const focusedLabelColor = useColorModeValue('blue.600', 'blue.300');
  const errorColor = useColorModeValue('red.500', 'red.300');
  const warningColor = useColorModeValue('orange.500', 'orange.300');
  const successColor = useColorModeValue('green.500', 'green.300');
  const bgColor = useColorModeValue('white', 'gray.800');
  const filledBgColor = useColorModeValue('gray.100', 'gray.700');
  
  // Combine refs
  const combinedRef = (node: HTMLInputElement) => {
    // Forward the ref
    if (typeof ref === 'function') {
      ref(node);
    } else if (ref) {
      (ref as React.MutableRefObject<HTMLInputElement | null>).current = node;
    }
    
    // Set the local ref
    inputRef.current = node;
  };
  
  // Effects
  
  // Sync external value to local state
  useEffect(() => {
    if (value !== undefined && value !== localValue) {
      setLocalValue(value);
    }
  }, [value]);
  
  // Sync validation state
  useEffect(() => {
    if (validationState !== 'none') {
      setLocalValidationState(validationState);
    }
  }, [validationState]);
  
  // Validate on mount if there's an initial value
  useEffect(() => {
    if (localValue && validationRules.length > 0) {
      validateValue(localValue);
    }
  }, []);
  
  // Handlers
  
  const handleFocus = (e: React.FocusEvent<HTMLInputElement>) => {
    setIsFocused(true);
    if (onFocus) onFocus(e);
  };
  
  const handleBlur = async (e: React.FocusEvent<HTMLInputElement>) => {
    setIsFocused(false);
    if (onBlur) onBlur(e);
    
    if (validateOnBlur) {
      await validateValue(localValue);
    }
  };
  
  const handleChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const newValue = e.target.value;
    setLocalValue(newValue);
    
    if (onChange) onChange(e);
    if (onValueChange) onValueChange(newValue);
    
    if (validateOnChange) {
      await validateValue(newValue);
    }
  };
  
  const handleCopy = () => {
    copyToClipboard();
    if (onCopy) onCopy();
  };
  
  const handlePaste = async () => {
    try {
      const clipboardText = await navigator.clipboard.readText();
      setLocalValue(clipboardText);
      
      if (onChange) {
        const event = {
          target: { value: clipboardText, name }
        } as React.ChangeEvent<HTMLInputElement>;
        onChange(event);
      }
      
      if (onValueChange) onValueChange(clipboardText);
      if (onPaste) onPaste();
      
      if (validateOnChange) {
        await validateValue(clipboardText);
      }
    } catch (error) {
      console.error('Failed to read clipboard contents:', error);
    }
  };
  
  // Validation
  const validateValue = async (valueToValidate: any): Promise<ValidationResult> => {
    // Skip validation if no rules or empty value (unless required)
    if (validationRules.length === 0 && !asyncValidator && !isRequired) {
      setLocalValidationState('none');
      setValidationMessage('');
      return { isValid: true };
    }
    
    // Check required
    if (isRequired && (!valueToValidate || valueToValidate === '')) {
      const result = { isValid: false, message: 'This field is required', type: 'invalid' as ValidationState };
      setLocalValidationState('invalid');
      setValidationMessage('This field is required');
      if (onValidationChange) onValidationChange(result);
      return result;
    }
    
    // Skip other validations if value is empty and not required
    if (!valueToValidate || valueToValidate === '') {
      setLocalValidationState('none');
      setValidationMessage('');
      return { isValid: true };
    }
    
    // Check validation rules
    for (const rule of validationRules) {
      if (!rule.test(valueToValidate)) {
        const result = { 
          isValid: false, 
          message: rule.message, 
          type: rule.type || 'invalid' 
        };
        setLocalValidationState(rule.type || 'invalid');
        setValidationMessage(rule.message);
        if (onValidationChange) onValidationChange(result);
        return result;
      }
    }
    
    // Check async validator
    if (asyncValidator) {
      setIsValidating(true);
      try {
        const result = await asyncValidator(valueToValidate);
        setLocalValidationState(result.isValid ? 'valid' : (result.type || 'invalid'));
        setValidationMessage(result.message || '');
        setIsValidating(false);
        if (onValidationChange) onValidationChange(result);
        return result;
      } catch (error) {
        setLocalValidationState('invalid');
        setValidationMessage('Validation failed');
        setIsValidating(false);
        const result = { isValid: false, message: 'Validation failed', type: 'invalid' as ValidationState };
        if (onValidationChange) onValidationChange(result);
        return result;
      }
    }
    
    // If all validations pass
    setLocalValidationState('valid');
    setValidationMessage('');
    const result = { isValid: true };
    if (onValidationChange) onValidationChange(result);
    return result;
  };
  
  // Determine if label should float (if there's a value or the input is focused)
  const shouldFloatLabel = Boolean(localValue) || isFocused;
  
  // Get validation icon
  const getValidationIcon = () => {
    if (isValidating) {
      return <Spinner size="sm" />;
    }
    
    switch (localValidationState) {
      case 'valid':
        return <Icon as={FaCheck} color="green.500" />;
      case 'invalid':
        return <Icon as={FaTimes} color="red.500" />;
      case 'warning':
        return <Icon as={FaExclamationTriangle} color="orange.500" />;
      default:
        return null;
    }
  };
  
  // Get validation message
  const getValidationMessage = () => {
    if (localValidationState === 'invalid' && errorText) {
      return errorText;
    }
    if (localValidationState === 'warning' && warningText) {
      return warningText;
    }
    if (localValidationState === 'valid' && successText) {
      return successText;
    }
    return validationMessage;
  };
  
  // Get validation message color
  const getValidationColor = () => {
    switch (localValidationState) {
      case 'valid':
        return successColor;
      case 'invalid':
        return errorColor;
      case 'warning':
        return warningColor;
      default:
        return 'inherit';
    }
  };
  
  // Get input border color based on validation state and focus
  const getBorderColor = () => {
    if (localValidationState === 'invalid') return errorColor;
    if (localValidationState === 'warning') return warningColor;
    if (localValidationState === 'valid') return successColor;
    if (isFocused) return 'blue.500';
    return 'inherit';
  };
  
  // Get input background color based on variant
  const getInputBgColor = () => {
    if (variant === 'filled') return filledBgColor;
    return 'transparent';
  };
  
  // Render specialized input components based on inputType
  const renderSpecializedInput = () => {
    const commonProps = {
      ref: combinedRef,
      name,
      value: localValue,
      onChange: handleChange,
      onFocus: handleFocus,
      onBlur: handleBlur,
      placeholder,
      isDisabled,
      isReadOnly,
      size,
      ...rest
    };
    
    switch (inputType) {
      case 'token':
        return (
          <TokenAmountInput
            {...commonProps}
            token={token}
            showMaxButton={showMaxButton}
            onMaxClick={onMaxClick}
            precision={precision}
          />
        );
      case 'address':
        return (
          <AddressInput
            {...commonProps}
            resolveEns={resolveEns}
            chainId={chainId}
          />
        );
      case 'search':
        return (
          <SearchInput
            {...commonProps}
            autocompleteOptions={autocompleteOptions}
            onSearch={onSearch}
          />
        );
      case 'password':
        return (
          <PasswordInput
            {...commonProps}
            showPasswordStrength={showPasswordStrength}
          />
        );
      case 'currency':
        return (
          <CurrencyInput
            {...commonProps}
            currencySymbol={currencySymbol}
            precision={precision}
            allowNegative={allowNegative}
          />
        );
      case 'percentage':
        return (
          <PercentageInput
            {...commonProps}
            precision={precision}
          />
        );
      default:
        return null;
    }
  };
  
  // Render standard input with all features
  const renderStandardInput = () => {
    const inputElement = (
      <Input
        ref={combinedRef}
        name={name}
        value={localValue}
        onChange={handleChange}
        onFocus={handleFocus}
        onBlur={handleBlur}
        placeholder={variant === 'floating' ? ' ' : placeholder}
        isDisabled={isDisabled}
        isReadOnly={isReadOnly}
        size={size}
        bg={getInputBgColor()}
        borderColor={getBorderColor()}
        _hover={{ borderColor: isFocused ? getBorderColor() : 'inherit' }}
        _focus={{ borderColor: getBorderColor(), boxShadow: `0 0 0 1px ${getBorderColor()}` }}
        aria-label={ariaLabel || label}
        aria-describedby={ariaDescribedBy}
        {...rest}
      />
    );
    
    // Wrap with input group if needed
    if (leftIcon || rightIcon || leftAddon || rightAddon) {
      return (
        <InputGroup size={size}>
          {leftAddon && <InputLeftAddon>{leftAddon}</InputLeftAddon>}
          {leftIcon && <InputLeftElement>{leftIcon}</InputLeftElement>}
          {inputElement}
          {rightIcon && <InputRightElement>{rightIcon}</InputRightElement>}
          {rightAddon && <InputRightAddon>{rightAddon}</InputRightAddon>}
        </InputGroup>
      );
    }
    
    return inputElement;
  };
  
  // Render the input component
  const renderInput = () => {
    // Render specialized input types
    if (['token', 'address', 'search', 'password', 'currency', 'percentage'].includes(inputType)) {
      return renderSpecializedInput();
    }
    
    // Render standard input
    return renderStandardInput();
  };
  
  // Render floating label variant
  const renderFloatingLabel = () => {
    return (
      <Box position="relative" width={isFullWidth ? '100%' : 'auto'}>
        {/* Input */}
        {renderInput()}
        
        {/* Floating Label */}
        {label && (
          <MotionBox
            position="absolute"
            top={shouldFloatLabel ? '-12px' : '50%'}
            left="10px"
            transform={shouldFloatLabel ? 'translateY(0)' : 'translateY(-50%)'}
            px={1}
            bg={bgColor}
            zIndex={1}
            pointerEvents="none"
            initial={false}
            animate={
              animateLabel
                ? {
                    top: shouldFloatLabel ? '-12px' : '50%',
                    transform: shouldFloatLabel ? 'translateY(0) scale(0.85)' : 'translateY(-50%) scale(1)',
                    color: shouldFloatLabel ? focusedLabelColor : floatingLabelColor,
                  }
                : {}
            }
            transition={{ duration: 0.2 }}
          >
            <Text
              fontSize={shouldFloatLabel ? 'xs' : 'md'}
              fontWeight={shouldFloatLabel ? 'medium' : 'normal'}
              color={shouldFloatLabel ? focusedLabelColor : floatingLabelColor}
            >
              {label}
              {isRequired && <Box as="span" color={errorColor} ml={1}>*</Box>}
            </Text>
          </MotionBox>
        )}
      </Box>
    );
  };
  
  // Main render
  return (
    <FormControl
      isRequired={isRequired}
      isInvalid={localValidationState === 'invalid'}
      isDisabled={isDisabled}
      isReadOnly={isReadOnly}
      width={isFullWidth ? '100%' : 'auto'}
    >
      {/* Label (non-floating variants) */}
      {label && variant !== 'floating' && (
        <FormLabel htmlFor={name}>
          {label}
          {isRequired && <Box as="span" color={errorColor} ml={1}>*</Box>}
        </FormLabel>
      )}
      
      {/* Input */}
      <Box position="relative">
        {variant === 'floating' ? renderFloatingLabel() : renderInput()}
        
        {/* Copy/Paste buttons */}
        {!isDisabled && !isReadOnly && (
          <Flex
            position="absolute"
            top="-30px"
            right="0"
            zIndex={1}
            opacity={isFocused ? 1 : 0}
            transition="opacity 0.2s"
            pointerEvents={isFocused ? 'auto' : 'none'}
          >
            <Tooltip label="Copy value" placement="top">
              <IconButton
                aria-label="Copy value"
                icon={<FaCopy />}
                size="xs"
                variant="ghost"
                onClick={handleCopy}
                mr={1}
              />
            </Tooltip>
            <Tooltip label="Paste from clipboard" placement="top">
              <IconButton
                aria-label="Paste from clipboard"
                icon={<FaPaste />}
                size="xs"
                variant="ghost"
                onClick={handlePaste}
              />
            </Tooltip>
          </Flex>
        )}
        
        {/* Validation icon */}
        <AnimatePresence>
          {(localValidationState !== 'none' || isValidating) && (
            <MotionBox
              position="absolute"
              top="50%"
              right={3}
              transform="translateY(-50%)"
              zIndex={2}
              variants={validationIconVariants}
              initial="initial"
              animate="animate"
              exit="exit"
            >
              {getValidationIcon()}
            </MotionBox>
          )}
        </AnimatePresence>
      </Box>
      
      {/* Helper text or validation message */}
      <AnimatePresence>
        {(helperText || getValidationMessage()) && (
          <MotionBox
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.2 }}
            overflow="hidden"
          >
            {localValidationState !== 'none' ? (
              <Text
                fontSize="sm"
                color={getValidationColor()}
                mt={1}
              >
                {getValidationMessage()}
              </Text>
            ) : helperText ? (
              <FormHelperText>{helperText}</FormHelperText>
            ) : null}
          </MotionBox>
        )}
      </AnimatePresence>
      
      {/* Screen reader only validation message for accessibility */}
      {localValidationState !== 'none' && (
        <VisuallyHidden>
          <div aria-live="polite">
            {localValidationState}: {getValidationMessage()}
          </div>
        </VisuallyHidden>
      )}
    </FormControl>
  );
});

EnhancedInput.displayName = 'EnhancedInput';

export default EnhancedInput;

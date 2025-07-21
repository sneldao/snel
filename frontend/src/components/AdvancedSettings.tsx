import React, { useState, useCallback } from "react";
import {
  Box,
  Button,
  Collapse,
  VStack,
  HStack,
  Text,
  Select,
  NumberInput,
  NumberInputField,
  NumberInputStepper,
  NumberIncrementStepper,
  NumberDecrementStepper,
  Switch,
  FormControl,
  FormLabel,
  Divider,
  Icon,
  useColorModeValue,
  Alert,
  AlertIcon,
  AlertTitle,
  AlertDescription,
} from "@chakra-ui/react";
import {
  FaCog,
  FaChevronDown,
  FaChevronUp,
  FaRoute,
  FaGasPump,
} from "react-icons/fa";
import { useChainId, useAccount } from "wagmi";
import { ChainUtils } from "../utils/chainUtils";

interface AdvancedSettingsProps {
  isOpen?: boolean;
  onToggle?: () => void;
  onSettingsChange?: (settings: AdvancedSettingsValues) => void;
  forceOpen?: boolean; // For when Axelar is unavailable
  axelarUnavailable?: boolean;
}

export interface AdvancedSettingsValues {
  selectedChain?: number;
  protocol: "axelar" | "brian" | "0x" | "auto";
  slippageTolerance: number;
  gasPrice?: number;
  enableMEVProtection: boolean;
  preferredRoute: "fastest" | "cheapest" | "balanced";
  manualChainSelection: boolean;
}

const SUPPORTED_CHAINS = ChainUtils.getSupportedChainIds().map((id) => ({
  id,
  name: ChainUtils.getChainName(id),
}));

export const AdvancedSettings: React.FC<AdvancedSettingsProps> = ({
  isOpen = false,
  onToggle,
  onSettingsChange,
  forceOpen = false,
  axelarUnavailable = false,
}) => {
  const [isExpanded, setIsExpanded] = useState(forceOpen); // Default to closed for cleaner UI
  const [settings, setSettings] = useState<AdvancedSettingsValues>({
    protocol: "auto",
    slippageTolerance: 1.0,
    enableMEVProtection: true,
    preferredRoute: "balanced",
    manualChainSelection: false,
  });

  const bgColor = useColorModeValue("gray.50", "gray.800");
  const borderColor = useColorModeValue("gray.200", "gray.600");
  const chainId = useChainId();
  const { isConnected } = useAccount();

  const currentChainName = chainId
    ? ChainUtils.getChainName(chainId)
    : "Unknown";

  const handleToggle = () => {
    const newExpanded = !isExpanded;
    setIsExpanded(newExpanded);
    onToggle?.();
  };

  const updateSettings = useCallback(
    (newSettings: Partial<AdvancedSettingsValues>) => {
      setSettings((prevSettings) => {
        const updated = { ...prevSettings, ...newSettings };
        onSettingsChange?.(updated);
        return updated;
      });
    },
    [onSettingsChange]
  );

  // Auto-expand when Axelar is unavailable
  React.useEffect(() => {
    if (axelarUnavailable) {
      setIsExpanded(true);
      // Use setTimeout to avoid updating during render
      setTimeout(() => {
        updateSettings({ manualChainSelection: true });
      }, 0);
    }
  }, [axelarUnavailable, updateSettings]);

  return (
    <Box>
      {/* Advanced Settings Toggle */}
      <Button
        variant="ghost"
        size="sm"
        leftIcon={<Icon as={FaCog} />}
        rightIcon={<Icon as={isExpanded ? FaChevronUp : FaChevronDown} />}
        onClick={handleToggle}
        isDisabled={forceOpen}
        opacity={forceOpen ? 0.6 : 1}
      >
        Advanced Settings
      </Button>

      {/* Settings Panel */}
      <Collapse in={isExpanded || forceOpen} animateOpacity>
        <Box
          mt={3}
          p={4}
          bg={bgColor}
          borderRadius="lg"
          border="1px solid"
          borderColor={borderColor}
          shadow="sm"
          _hover={{ shadow: "md" }}
          transition="all 0.2s"
        >
          {/* Alert when Axelar is unavailable */}
          {axelarUnavailable && (
            <Alert status="warning" size="sm" mb={4} borderRadius="md">
              <AlertIcon />
              <Box>
                <AlertTitle fontSize="sm">
                  Cross-chain routing unavailable
                </AlertTitle>
                <AlertDescription fontSize="xs">
                  Using manual mode. Select your preferred chain and protocol.
                </AlertDescription>
              </Box>
            </Alert>
          )}

          <VStack spacing={4} align="stretch">
            {/* Chain Selection */}
            <FormControl>
              <FormLabel fontSize="sm" display="flex" alignItems="center">
                <Icon as={FaRoute} mr={2} />
                Target Chain
                {!axelarUnavailable && (
                  <Text fontSize="xs" color="gray.500" ml={2}>
                    (Auto-detected for cross-chain)
                  </Text>
                )}
              </FormLabel>
              <Select
                size="sm"
                value={settings.selectedChain || chainId || ""}
                onChange={(e) =>
                  updateSettings({ selectedChain: parseInt(e.target.value) })
                }
                isDisabled={
                  !axelarUnavailable && !settings.manualChainSelection
                }
              >
                <option value="">Current Chain ({currentChainName})</option>
                {SUPPORTED_CHAINS.map((supportedChain) => (
                  <option key={supportedChain.id} value={supportedChain.id}>
                    {supportedChain.name}
                  </option>
                ))}
              </Select>
            </FormControl>

            {/* Manual Chain Selection Toggle */}
            {!axelarUnavailable && (
              <FormControl>
                <HStack justify="space-between">
                  <FormLabel fontSize="sm" mb={0}>
                    Manual Chain Selection
                  </FormLabel>
                  <Switch
                    size="sm"
                    isChecked={settings.manualChainSelection}
                    onChange={(e) =>
                      updateSettings({ manualChainSelection: e.target.checked })
                    }
                  />
                </HStack>
                <Text fontSize="xs" color="gray.500" mt={1}>
                  Override automatic cross-chain detection
                </Text>
              </FormControl>
            )}

            <Divider />

            {/* Protocol Selection */}
            <FormControl>
              <FormLabel fontSize="sm">Protocol Preference</FormLabel>
              <Select
                size="sm"
                value={settings.protocol}
                onChange={(e) =>
                  updateSettings({ protocol: e.target.value as any })
                }
              >
                <option value="auto">Auto (Recommended)</option>
                <option value="axelar">Axelar Network (Cross-chain)</option>
                <option value="brian">Brian AI (DeFi Intelligence)</option>
                <option value="0x">0x Protocol (DEX Aggregation)</option>
              </Select>
              <Text fontSize="xs" color="gray.500" mt={1}>
                Powered by industry-leading protocols for secure, efficient
                transactions
              </Text>
            </FormControl>

            {/* Route Preference */}
            <FormControl>
              <FormLabel fontSize="sm">Route Optimization</FormLabel>
              <Select
                size="sm"
                value={settings.preferredRoute}
                onChange={(e) =>
                  updateSettings({ preferredRoute: e.target.value as any })
                }
              >
                <option value="balanced">Balanced (Best overall)</option>
                <option value="fastest">Fastest</option>
                <option value="cheapest">Cheapest</option>
              </Select>
            </FormControl>

            <Divider />

            {/* Trading Settings */}
            <FormControl>
              <FormLabel fontSize="sm" display="flex" alignItems="center">
                Slippage Tolerance (%)
              </FormLabel>
              <NumberInput
                size="sm"
                min={0.1}
                max={5}
                step={0.1}
                value={settings.slippageTolerance}
                onChange={(_, value) =>
                  updateSettings({ slippageTolerance: value || 1.0 })
                }
              >
                <NumberInputField />
                <NumberInputStepper>
                  <NumberIncrementStepper />
                  <NumberDecrementStepper />
                </NumberInputStepper>
              </NumberInput>
            </FormControl>

            {/* Gas Settings */}
            <FormControl>
              <FormLabel fontSize="sm" display="flex" alignItems="center">
                <Icon as={FaGasPump} mr={2} />
                Custom Gas Price (Gwei)
              </FormLabel>
              <NumberInput
                size="sm"
                min={1}
                max={200}
                value={settings.gasPrice || ""}
                onChange={(_, value) => updateSettings({ gasPrice: value })}
              >
                <NumberInputField placeholder="Auto" />
                <NumberInputStepper>
                  <NumberIncrementStepper />
                  <NumberDecrementStepper />
                </NumberInputStepper>
              </NumberInput>
              <Text fontSize="xs" color="gray.500" mt={1}>
                Leave empty for automatic gas estimation
              </Text>
            </FormControl>

            {/* MEV Protection */}
            <FormControl>
              <HStack justify="space-between">
                <FormLabel fontSize="sm" mb={0}>
                  MEV Protection
                </FormLabel>
                <Switch
                  size="sm"
                  isChecked={settings.enableMEVProtection}
                  onChange={(e) =>
                    updateSettings({ enableMEVProtection: e.target.checked })
                  }
                />
              </HStack>
              <Text fontSize="xs" color="gray.500" mt={1}>
                Protect against front-running (may increase gas costs)
              </Text>
            </FormControl>
          </VStack>
        </Box>
      </Collapse>
    </Box>
  );
};

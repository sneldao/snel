/**
 * X402 Automation Card - Premium Dynamic Configuration Interface
 * Advanced editable interface with real-time calculations and premium aesthetics.
 */

import React, { useState, useEffect } from 'react';
import {
    Box,
    VStack,
    HStack,
    Text,
    Button,
    Icon,
    Badge,
    Divider,
    useColorModeValue,
    Alert,
    AlertIcon,
    Progress,
    Input,
    NumberInput,
    NumberInputField,
    Select,
    FormControl,
    FormLabel,
    InputGroup,
    InputRightAddon,
    Tooltip,
    Collapse,
    IconButton,
    Switch,
    Slider,
    SliderTrack,
    SliderFilledTrack,
    SliderThumb,
    useDisclosure
} from '@chakra-ui/react';
import { keyframes } from '@emotion/react';
import { FaBolt, FaRobot, FaCheckCircle, FaClock, FaEdit, FaChevronDown, FaChevronUp, FaCog, FaShieldAlt, FaCalculator } from 'react-icons/fa';

interface X402AutomationCardProps {
    content: any;
    onExecute?: (overrides?: any) => void;
    onCancel?: () => void;
    isExecuting?: boolean;
}

export const X402AutomationCard: React.FC<X402AutomationCardProps> = ({
    content,
    onExecute,
    onCancel,
    isExecuting = false,
}) => {
    // Theme & Styling
    const bgColor = useColorModeValue('rgba(255, 255, 255, 0.95)', 'rgba(26, 32, 44, 0.95)');
    const glassBg = useColorModeValue('rgba(255, 255, 255, 0.8)', 'rgba(45, 55, 72, 0.8)');
    const accentColor = 'purple.500';
    const borderColor = useColorModeValue('rgba(160, 174, 192, 0.3)', 'rgba(74, 85, 104, 0.3)');
    const inputBg = useColorModeValue('rgba(247, 250, 252, 0.8)', 'rgba(255, 255, 255, 0.05)');

    // Animations
    const pulseAnimation = keyframes`
        0% { transform: scale(1); }
        50% { transform: scale(1.05); }
        100% { transform: scale(1); }
    `;

    const shimmerAnimation = keyframes`
        0% { background-position: -200px 0; }
        100% { background-position: calc(200px + 100%) 0; }
    `;

    // Initial Data
    const metadata = content?.metadata || {};

    // State for editable fields
    const [amount, setAmount] = useState<string>(metadata.amount || metadata.budget || '0');
    const [recipient, setRecipient] = useState<string>(metadata.recipient || '');
    const [frequency, setFrequency] = useState<string>(metadata.interval || 'monthly');
    const [asset] = useState<string>(metadata.asset || 'USDC');
    const [customBudgetCap, setCustomBudgetCap] = useState<boolean>(false);
    const [budgetCapMonths, setBudgetCapMonths] = useState<number>(12);

    // Advanced controls
    const { isOpen: showAdvanced, onToggle: toggleAdvanced } = useDisclosure();

    // Derived State
    const network = metadata.network || 'cronos-testnet';
    const facilitatorHealthy = metadata.facilitator_healthy !== false;

    // Enhanced calculation with custom cap support
    const calculateAnnualCap = (amt: string, freq: string, months: number = 12): number => {
        const val = parseFloat(amt) || 0;
        const multiplier = months / 12; // Scale based on custom months

        switch (freq.toLowerCase()) {
            case 'daily': return val * 365 * multiplier;
            case 'weekly': return val * 52 * multiplier;
            case 'monthly': return val * 12 * multiplier;
            case 'hourly': return val * 8760 * multiplier;
            default: return val * 12 * multiplier;
        }
    };

    const annualCap = calculateAnnualCap(amount, frequency, customBudgetCap ? budgetCapMonths : 12);
    const monthlyEstimate = annualCap / (customBudgetCap ? budgetCapMonths : 12);

    // Handle Execute with Overrides
    const handleAuthorize = () => {
        if (onExecute) {
            onExecute({
                amount,
                recipient,
                interval: frequency,
                approval_amount: annualCap.toString(),
                budget_cap_months: customBudgetCap ? budgetCapMonths : 12
            });
        }
    };

    return (
        <Box
            bg={bgColor}
            backdropFilter="blur(20px)"
            borderWidth="1px"
            borderColor={borderColor}
            borderRadius="3xl"
            p={0}
            position="relative"
            overflow="hidden"
            boxShadow="0 25px 50px -12px rgba(0, 0, 0, 0.25)"
            _hover={{
                boxShadow: "0 25px 50px -12px rgba(139, 92, 246, 0.3)",
                borderColor: "purple.300",
                transform: "translateY(-2px)"
            }}
            transition="all 0.3s cubic-bezier(0.4, 0, 0.2, 1)"
        >
            {/* Animated Header Gradient */}
            <Box
                h="8px"
                bgGradient="linear(to-r, purple.400, blue.500, purple.600)"
                w="100%"
                position="relative"
                _before={{
                    content: '""',
                    position: 'absolute',
                    top: 0,
                    left: '-100%',
                    width: '100%',
                    height: '100%',
                    background: 'linear-gradient(90deg, transparent, rgba(255,255,255,0.4), transparent)',
                    animation: `${shimmerAnimation} 2s infinite`
                }}
            />

            <Box p={8}>
                {/* Enhanced Header Section */}
                <HStack justify="space-between" mb={8} align="start">
                    <HStack spacing={4}>
                        <Box
                            p={3}
                            bg="linear-gradient(135deg, rgba(139, 92, 246, 0.1), rgba(59, 130, 246, 0.1))"
                            borderRadius="xl"
                            color="purple.500"
                            border="1px solid"
                            borderColor="purple.200"
                            animation={parseFloat(amount) > 0 ? `${pulseAnimation} 2s infinite` : 'none'}
                        >
                            <Icon as={FaRobot} boxSize={6} />
                        </Box>
                        <VStack align="start" spacing={1}>
                            <Text fontSize="xl" fontWeight="bold" bgGradient="linear(to-r, purple.600, blue.600)" bgClip="text">
                                Payment Automation
                            </Text>
                            <Text fontSize="sm" color="gray.500" fontWeight="medium">
                                Recurring Payments via X402 Protocol
                            </Text>
                        </VStack>
                    </HStack>

                    <VStack spacing={2} align="end">
                        <Badge
                            colorScheme={network.includes('ethereum') ? 'blue' : 'purple'}
                            variant="subtle"
                            px={4}
                            py={2}
                            borderRadius="full"
                            fontSize="xs"
                            fontWeight="bold"
                        >
                            {network.includes('ethereum') ? 'Ethereum Mainnet' : 'Cronos Chain'}
                        </Badge>
                        <IconButton
                            aria-label="Advanced Settings"
                            icon={<Icon as={FaCog} />}
                            size="sm"
                            variant="ghost"
                            colorScheme="purple"
                            onClick={toggleAdvanced}
                            transform={showAdvanced ? 'rotate(180deg)' : 'rotate(0deg)'}
                            transition="transform 0.3s"
                        />
                    </VStack>
                </HStack>

                {/* Configuration Form */}
                <VStack spacing={6} align="stretch">

                    {/* Amount Input with Live Preview */}
                    <FormControl>
                        <FormLabel fontSize="xs" color="gray.500" fontWeight="bold" textTransform="uppercase" letterSpacing="wider">
                            Payment Amount
                        </FormLabel>
                        <InputGroup size="lg">
                            <NumberInput
                                w="100%"
                                value={amount}
                                onChange={(val) => setAmount(val)}
                                min={0}
                                precision={2}
                            >
                                <NumberInputField
                                    bg={inputBg}
                                    border="2px solid transparent"
                                    borderRadius="xl"
                                    fontWeight="bold"
                                    fontSize="lg"
                                    _focus={{
                                        borderColor: "purple.300",
                                        bg: "white",
                                        boxShadow: "0 0 0 3px rgba(139, 92, 246, 0.1)"
                                    }}
                                    _hover={{ borderColor: "purple.200" }}
                                    transition="all 0.2s"
                                />
                            </NumberInput>
                            <InputRightAddon
                                bg="purple.50"
                                border="2px solid transparent"
                                borderRadius="xl"
                                fontWeight="bold"
                                color="purple.600"
                                borderLeft="none"
                            >
                                {asset}
                            </InputRightAddon>
                        </InputGroup>
                        {parseFloat(amount) > 0 && (
                            <Text fontSize="xs" color="gray.500" mt={2} fontStyle="italic">
                                ≈ ${(parseFloat(amount) * 1).toLocaleString()} USD per payment
                            </Text>
                        )}
                    </FormControl>

                    <HStack spacing={6}>
                        {/* Enhanced Frequency Select */}
                        <FormControl>
                            <FormLabel fontSize="xs" color="gray.500" fontWeight="bold" textTransform="uppercase" letterSpacing="wider">
                                Frequency
                            </FormLabel>
                            <Select
                                value={frequency}
                                onChange={(e) => setFrequency(e.target.value)}
                                bg={inputBg}
                                border="2px solid transparent"
                                borderRadius="xl"
                                size="lg"
                                fontWeight="medium"
                                _focus={{
                                    borderColor: "purple.300",
                                    bg: "white",
                                    boxShadow: "0 0 0 3px rgba(139, 92, 246, 0.1)"
                                }}
                                _hover={{ borderColor: "purple.200" }}
                                transition="all 0.2s"
                            >
                                <option value="daily">Daily</option>
                                <option value="weekly">Weekly</option>
                                <option value="monthly">Monthly</option>
                            </Select>
                        </FormControl>

                        {/* Enhanced Recipient Input */}
                        <FormControl flex={2}>
                            <FormLabel fontSize="xs" color="gray.500" fontWeight="bold" textTransform="uppercase" letterSpacing="wider">
                                Recipient
                            </FormLabel>
                            <Input
                                value={recipient}
                                onChange={(e) => setRecipient(e.target.value)}
                                placeholder="0x... or ENS name"
                                bg={inputBg}
                                border="2px solid transparent"
                                borderRadius="xl"
                                size="lg"
                                fontFamily="mono"
                                fontSize="sm"
                                _focus={{
                                    borderColor: "purple.300",
                                    bg: "white",
                                    boxShadow: "0 0 0 3px rgba(139, 92, 246, 0.1)"
                                }}
                                _hover={{ borderColor: "purple.200" }}
                                transition="all 0.2s"
                            />
                        </FormControl>
                    </HStack>

                    {/* Advanced Controls */}
                    <Collapse in={showAdvanced} animateOpacity>
                        <VStack spacing={4} p={4} bg={glassBg} borderRadius="xl" border="1px dashed" borderColor="purple.200">
                            <HStack w="100%" justify="space-between">
                                <HStack>
                                    <Icon as={FaShieldAlt} color="purple.500" />
                                    <Text fontSize="sm" fontWeight="bold">Custom Budget Cap</Text>
                                </HStack>
                                <Switch
                                    colorScheme="purple"
                                    isChecked={customBudgetCap}
                                    onChange={(e) => setCustomBudgetCap(e.target.checked)}
                                />
                            </HStack>

                            {customBudgetCap && (
                                <VStack w="100%" spacing={3}>
                                    <HStack w="100%" justify="space-between">
                                        <Text fontSize="sm" color="gray.600">Duration: {budgetCapMonths} months</Text>
                                        <Text fontSize="sm" color="purple.600" fontWeight="bold">
                                            {annualCap.toLocaleString()} {asset}
                                        </Text>
                                    </HStack>
                                    <Slider
                                        value={budgetCapMonths}
                                        onChange={setBudgetCapMonths}
                                        min={1}
                                        max={24}
                                        step={1}
                                        colorScheme="purple"
                                    >
                                        <SliderTrack bg="purple.100">
                                            <SliderFilledTrack />
                                        </SliderTrack>
                                        <SliderThumb boxSize={6}>
                                            <Box color="purple.500" as={FaClock} />
                                        </SliderThumb>
                                    </Slider>
                                </VStack>
                            )}
                        </VStack>
                    </Collapse>

                    {/* Enhanced Budget Cap Info with Live Updates */}
                    <Box
                        bg="linear-gradient(135deg, rgba(251, 146, 60, 0.1), rgba(245, 101, 101, 0.1))"
                        p={5}
                        borderRadius="xl"
                        border="2px solid"
                        borderColor="orange.200"
                        position="relative"
                        overflow="hidden"
                    >
                        <VStack spacing={3} align="stretch">
                            <HStack justify="space-between">
                                <HStack>
                                    <Icon as={FaCalculator} color="orange.500" />
                                    <Text fontSize="sm" color="orange.800" fontWeight="bold">
                                        {customBudgetCap ? `${budgetCapMonths}-Month` : '1-Year'} Approval Cap
                                    </Text>
                                </HStack>
                                <Text fontSize="lg" fontWeight="bold" color="orange.700">
                                    {annualCap.toLocaleString()} {asset}
                                </Text>
                            </HStack>

                            <HStack justify="space-between" fontSize="xs" color="orange.600">
                                <Text>Monthly Average: {monthlyEstimate.toLocaleString()} {asset}</Text>
                                <Text>Per Payment: {amount} {asset}</Text>
                            </HStack>

                            <Text fontSize="xs" color="orange.600" fontStyle="italic">
                                This creates a <strong>Payment Action</strong> that uses X402 for secure settlement of each recurring payment.
                            </Text>
                        </VStack>
                    </Box>

                </VStack>

                <Divider my={6} borderColor="purple.100" />

                {/* Network Status */}
                {!facilitatorHealthy && (
                    <Alert status="warning" borderRadius="xl" size="sm" mb={6} bg="yellow.50" border="1px solid" borderColor="yellow.200">
                        <AlertIcon />
                        <Text fontSize="sm">Service temporarily unavailable. Please try again later.</Text>
                    </Alert>
                )}

                {/* Enhanced Actions */}
                <HStack spacing={4}>
                    <Button
                        colorScheme="purple"
                        size="lg"
                        flex={1}
                        onClick={handleAuthorize}
                        isLoading={isExecuting}
                        loadingText="Authorizing..."
                        isDisabled={!facilitatorHealthy || parseFloat(amount) <= 0 || !recipient}
                        leftIcon={<Icon as={FaBolt} />}
                        bgGradient="linear(to-r, purple.500, blue.500)"
                        _hover={{
                            bgGradient: "linear(to-r, purple.600, blue.600)",
                            transform: 'translateY(-2px)',
                            boxShadow: '0 10px 25px -5px rgba(139, 92, 246, 0.4)'
                        }}
                        _active={{ transform: 'translateY(0px)' }}
                        transition="all 0.2s cubic-bezier(0.4, 0, 0.2, 1)"
                        borderRadius="xl"
                        fontWeight="bold"
                        fontSize="md"
                    >
                        Authorize Payment Action
                    </Button>
                    <Button
                        variant="ghost"
                        size="lg"
                        onClick={onCancel}
                        isDisabled={isExecuting}
                        color="gray.500"
                        _hover={{ bg: "gray.100", color: "gray.700" }}
                        borderRadius="xl"
                        fontWeight="medium"
                    >
                        Cancel
                    </Button>
                </HStack>

                {/* Enhanced Execution Progress */}
                {isExecuting && (
                    <VStack spacing={3} mt={6}>
                        <Progress
                            size="md"
                            isIndeterminate
                            colorScheme="purple"
                            borderRadius="full"
                            w="100%"
                            bg="purple.50"
                        />
                        <Text fontSize="sm" color="gray.600" textAlign="center" fontWeight="medium">
                            Interacting with {network.includes('ethereum') ? 'Ethereum' : 'Cronos'} Facilitator...
                        </Text>
                        <Text fontSize="xs" color="gray.500" textAlign="center">
                            This may take up to 30 seconds
                        </Text>
                    </VStack>
                )}
            </Box>
        </Box>
    );
};
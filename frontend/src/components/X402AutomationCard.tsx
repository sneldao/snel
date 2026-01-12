/**
 * X402 Automation Card - Showcases x402 agentic payment capabilities
 * Integrates naturally with existing response system following design ethos
 */

import React from 'react';
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
} from '@chakra-ui/react';
import { FaBolt, FaRobot, FaCheckCircle, FaClock, FaExclamationTriangle } from 'react-icons/fa';

interface X402AutomationCardProps {
    content: any;
    onExecute?: () => void;
    onCancel?: () => void;
    isExecuting?: boolean;
}

export const X402AutomationCard: React.FC<X402AutomationCardProps> = ({
    content,
    onExecute,
    onCancel,
    isExecuting = false,
}) => {
    const bgColor = useColorModeValue('purple.50', 'purple.900');
    const borderColor = useColorModeValue('purple.200', 'purple.700');
    const textColor = useColorModeValue('gray.800', 'white');

    // Extract automation details from content
    const automationType = content?.metadata?.automation_type || 'general_automation';
    const budget = content?.metadata?.budget;
    const asset = content?.metadata?.asset || 'USDC';
    const network = content?.metadata?.network || 'cronos-testnet';
    const serviceDescription = content?.metadata?.service_description || 'DeFi automation service';
    const facilitatorHealthy = content?.metadata?.facilitator_healthy !== false;

    // Get automation-specific details
    const getAutomationDetails = () => {
        switch (automationType) {
            case 'portfolio_rebalancing':
                return {
                    title: '🎯 Portfolio Rebalancing',
                    description: 'Automatically rebalance when allocation drifts >5%',
                    frequency: 'Continuous monitoring',
                    icon: FaRobot,
                    color: 'blue.500',
                };
            case 'yield_farming':
                return {
                    title: '🌾 Yield Farming',
                    description: 'Deploy funds when APY opportunities > 15%',
                    frequency: 'Market-driven',
                    icon: FaRobot,
                    color: 'green.500',
                };
            case 'conditional_trading':
                return {
                    title: '📈 Conditional Trading',
                    description: 'Execute trades based on market conditions',
                    frequency: 'Trigger-based',
                    icon: FaRobot,
                    color: 'orange.500',
                };
            case 'cross_chain_automation':
                return {
                    title: '🌉 Cross-Chain Bridge',
                    description: 'Automated bridging on schedule',
                    frequency: 'Monthly',
                    icon: FaRobot,
                    color: 'purple.500',
                };
            default:
                return {
                    title: '🤖 DeFi Automation',
                    description: 'AI-powered DeFi management',
                    frequency: 'Condition-based',
                    icon: FaRobot,
                    color: 'purple.500',
                };
        }
    };

    const automationDetails = getAutomationDetails();

    return (
        <Box
            bg={bgColor}
            borderWidth="2px"
            borderColor={borderColor}
            borderRadius="xl"
            p={6}
            position="relative"
            overflow="hidden"
        >
            {/* X402 Badge */}
            <HStack justify="space-between" mb={4}>
                <Badge
                    colorScheme="purple"
                    variant="solid"
                    px={3}
                    py={1}
                    borderRadius="full"
                    fontSize="xs"
                >
                    <HStack spacing={1}>
                        <Icon as={FaBolt} boxSize={3} />
                        <Text>X402 AUTOMATION</Text>
                    </HStack>
                </Badge>
                <Badge
                    colorScheme={facilitatorHealthy ? 'green' : 'red'}
                    variant="outline"
                    fontSize="2xs"
                >
                    {facilitatorHealthy ? 'Service Healthy' : 'Service Unavailable'}
                </Badge>
            </HStack>

            {/* Automation Details */}
            <VStack align="stretch" spacing={4}>
                <HStack spacing={3}>
                    <Icon as={automationDetails.icon} color={automationDetails.color} boxSize={6} />
                    <VStack align="start" spacing={0}>
                        <Text fontSize="lg" fontWeight="bold" color={textColor}>
                            {automationDetails.title}
                        </Text>
                        <Text fontSize="sm" color="gray.600">
                            {automationDetails.description}
                        </Text>
                    </VStack>
                </HStack>

                <Divider />

                {/* Service Configuration */}
                <VStack align="stretch" spacing={3}>
                    <HStack justify="space-between">
                        <Text fontSize="sm" fontWeight="medium">Budget:</Text>
                        <Text fontSize="sm" fontWeight="bold" color="purple.600">
                            {budget} {asset}
                        </Text>
                    </HStack>
                    <HStack justify="space-between">
                        <Text fontSize="sm" fontWeight="medium">Network:</Text>
                        <Text fontSize="sm">
                            Cronos {network.includes('testnet') ? 'Testnet' : 'Mainnet'}
                        </Text>
                    </HStack>
                    <HStack justify="space-between">
                        <Text fontSize="sm" fontWeight="medium">Frequency:</Text>
                        <Text fontSize="sm">{automationDetails.frequency}</Text>
                    </HStack>
                </VStack>

                <Divider />

                {/* How it Works */}
                <VStack align="stretch" spacing={2}>
                    <Text fontSize="sm" fontWeight="medium" color={textColor}>
                        How it works:
                    </Text>
                    <VStack align="stretch" spacing={1} pl={4}>
                        <HStack spacing={2}>
                            <Icon as={FaRobot} color="purple.500" boxSize={3} />
                            <Text fontSize="xs" color="gray.600">
                                AI monitors conditions 24/7
                            </Text>
                        </HStack>
                        <HStack spacing={2}>
                            <Icon as={FaBolt} color="purple.500" boxSize={3} />
                            <Text fontSize="xs" color="gray.600">
                                X402 authorizes payments when triggered
                            </Text>
                        </HStack>
                        <HStack spacing={2}>
                            <Icon as={FaCheckCircle} color="green.500" boxSize={3} />
                            <Text fontSize="xs" color="gray.600">
                                Actions execute automatically on Cronos
                            </Text>
                        </HStack>
                    </VStack>
                </VStack>

                {/* Network Status Alert */}
                {!facilitatorHealthy && (
                    <Alert status="warning" borderRadius="md" size="sm">
                        <AlertIcon />
                        <Text fontSize="xs">
                            X402 facilitator service is currently unavailable. Please try again later.
                        </Text>
                    </Alert>
                )}

                {/* Action Buttons */}
                <HStack spacing={3} pt={2}>
                    <Button
                        colorScheme="purple"
                        size="md"
                        flex={1}
                        onClick={onExecute}
                        isLoading={isExecuting}
                        loadingText="Authorizing..."
                        isDisabled={!facilitatorHealthy}
                        leftIcon={<Icon as={FaBolt} />}
                    >
                        Authorize Automation
                    </Button>
                    <Button
                        variant="outline"
                        size="md"
                        onClick={onCancel}
                        isDisabled={isExecuting}
                    >
                        Cancel
                    </Button>
                </HStack>

                {/* Execution Progress */}
                {isExecuting && (
                    <VStack spacing={2}>
                        <Progress
                            size="sm"
                            isIndeterminate
                            colorScheme="purple"
                            borderRadius="full"
                        />
                        <Text fontSize="xs" color="gray.600" textAlign="center">
                            Setting up automation with Cronos x402 facilitator...
                        </Text>
                    </VStack>
                )}
            </VStack>

            {/* Decorative Elements */}
            <Box
                position="absolute"
                top="-20px"
                right="-20px"
                width="60px"
                height="60px"
                bg="purple.100"
                borderRadius="full"
                opacity={0.3}
                zIndex={0}
            />
            <Box
                position="absolute"
                bottom="-10px"
                left="-10px"
                width="40px"
                height="40px"
                bg="purple.200"
                borderRadius="full"
                opacity={0.2}
                zIndex={0}
            />
        </Box>
    );
};
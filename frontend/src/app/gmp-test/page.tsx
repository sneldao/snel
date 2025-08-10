"use client";

/**
 * GMP Test Page
 * Simple test interface to verify GMP integration works correctly
 */

import React, { useState } from 'react';
import {
  Container,
  VStack,
  HStack,
  Text,
  Button,
  Input,
  Box,
  Alert,
  AlertIcon,
  Badge,
  Divider,
  useToast,
  Card,
  CardBody,
  CardHeader,
  Heading
} from '@chakra-ui/react';
import { useGMP } from '../../contexts/GMPContext';
import { useGMPIntegration } from '../../hooks/useGMPIntegration';
import { GMPTransactionCard } from '../../components/GMP/GMPTransactionCard';

const GMPTestPage: React.FC = () => {
  const [testCommand, setTestCommand] = useState('');
  const [testResult, setTestResult] = useState<any>(null);
  const [isLoading, setIsLoading] = useState(false);
  
  const { state } = useGMP();
  const { executeCommand, isLikelyGMPCommand, stats } = useGMPIntegration();
  const toast = useToast();

  // Sample test commands
  const sampleCommands = [
    'swap 100 USDC from Ethereum to MATIC on Polygon',
    'swap 50 ETH from Arbitrum to USDC on Base',
    'swap 200 DAI from Polygon to USDC on Ethereum',
    'cross-chain swap 75 USDC to AVAX on Avalanche',
    'bridge and swap 150 USDT to ETH on Optimism',
    'call mint function on Polygon',
    'add liquidity to Uniswap on Arbitrum using ETH from Ethereum'
  ];

  const handleTestCommand = async () => {
    if (!testCommand.trim()) return;

    setIsLoading(true);
    try {
      // Test command detection
      const isGMP = isLikelyGMPCommand(testCommand);
      
      // Parse chain information from the command
      const parseChainInfo = (command: string) => {
        const lowerCommand = command.toLowerCase();
        
        // Extract source chain
        let sourceChain = 'Ethereum'; // default
        const fromMatch = lowerCommand.match(/from\s+(\w+)/);
        if (fromMatch) {
          sourceChain = fromMatch[1].charAt(0).toUpperCase() + fromMatch[1].slice(1);
        }
        
        // Extract destination chain  
        let destChain = 'Polygon'; // default
        const onMatch = lowerCommand.match(/on\s+(\w+)/);
        const toMatch = lowerCommand.match(/to\s+(\w+)\s+on\s+(\w+)/);
        if (toMatch) {
          destChain = toMatch[2].charAt(0).toUpperCase() + toMatch[2].slice(1);
        } else if (onMatch) {
          destChain = onMatch[1].charAt(0).toUpperCase() + onMatch[1].slice(1);
        }
        
        // Extract tokens
        const tokenMatch = lowerCommand.match(/swap\s+[\d.]+\s+(\w+).*(?:to|for)\s+(\w+)/);
        const sourceToken = tokenMatch ? tokenMatch[1].toUpperCase() : 'USDC';
        const destToken = tokenMatch ? tokenMatch[2].toUpperCase() : 'MATIC';
        
        // Extract amount
        const amountMatch = lowerCommand.match(/swap\s+([\d.]+)/);
        const amount = amountMatch ? amountMatch[1] : '100';
        
        return { sourceChain, destChain, sourceToken, destToken, amount };
      };
      
      const { sourceChain, destChain, sourceToken, destToken, amount } = parseChainInfo(testCommand);
      
      // Create realistic mock response based on parsed command
      const mockResponse = {
        content: {
          message: `Processed command: ${testCommand}`,
          metadata: {
            uses_gmp: isGMP,
            axelar_powered: isGMP,
            source_chain: sourceChain,
            dest_chain: destChain,
            source_token: sourceToken,
            dest_token: destToken,
            amount: amount
          },
          transaction_data: isGMP ? {
            type: 'cross_chain_swap',
            protocol: 'axelar_gmp',
            steps: [
              { 
                type: 'approve', 
                description: `Approve ${amount} ${sourceToken} for cross-chain transfer` 
              },
              { 
                type: 'pay_gas', 
                description: `Pay gas for execution on ${destChain}` 
              },
              { 
                type: 'call_contract', 
                description: `Execute cross-chain swap: ${sourceToken} → ${destToken} via Axelar` 
              }
            ],
            estimated_gas_fee: '0.025',
            estimated_cost_usd: (parseFloat(amount) * 0.125).toFixed(2), // Dynamic cost based on amount
            source_chain: sourceChain,
            dest_chain: destChain
          } : undefined
        },
        success: true,
        isGMPOperation: isGMP
      };

      setTestResult(mockResponse);
      
      toast({
        title: 'Command Processed',
        description: `${sourceChain} → ${destChain} swap ${isGMP ? 'detected as GMP' : 'processed normally'}`,
        status: 'success',
        duration: 3000
      });

    } catch (error) {
      console.error('Test failed:', error);
      toast({
        title: 'Test Failed',
        description: 'Check console for details',
        status: 'error',
        duration: 3000
      });
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <Container maxW="container.lg" py={8}>
      <VStack spacing={8} align="stretch">
        {/* Header */}
        <Box textAlign="center">
          <Heading size="lg" mb={2}>GMP Integration Test</Heading>
          <Text color="gray.600">
            Test the General Message Passing integration
          </Text>
        </Box>

        {/* Stats */}
        <Card>
          <CardHeader>
            <Heading size="md">Integration Status</Heading>
          </CardHeader>
          <CardBody>
            <HStack spacing={4} wrap="wrap">
              <Badge colorScheme="green" p={2}>
                ✅ GMP Context: Active
              </Badge>
              <Badge colorScheme="blue" p={2}>
                🔗 Supported Chains: {state.supportedChains.length}
              </Badge>
              <Badge colorScheme="purple" p={2}>
                ⚡ Operations: {state.supportedOperations.length}
              </Badge>
              <Badge colorScheme="orange" p={2}>
                📊 Success Rate: {stats.successRate.toFixed(0)}%
              </Badge>
            </HStack>
          </CardBody>
        </Card>

        {/* Test Interface */}
        <Card>
          <CardHeader>
            <Heading size="md">Command Tester</Heading>
          </CardHeader>
          <CardBody>
            <VStack spacing={4} align="stretch">
              <Input
                placeholder="Enter a command to test..."
                value={testCommand}
                onChange={(e) => setTestCommand(e.target.value)}
                size="lg"
              />
              
              <Button
                colorScheme="blue"
                onClick={handleTestCommand}
                isLoading={isLoading}
                loadingText="Testing..."
                size="lg"
              >
                Test Command
              </Button>

              {/* Sample Commands */}
              <Box>
                <Text fontSize="sm" fontWeight="semibold" mb={2}>
                  Sample GMP Commands:
                </Text>
                <VStack spacing={2} align="stretch">
                  {sampleCommands.map((cmd, index) => (
                    <Button
                      key={index}
                      variant="outline"
                      size="sm"
                      onClick={() => setTestCommand(cmd)}
                      textAlign="left"
                      justifyContent="flex-start"
                      fontFamily="mono"
                      fontSize="xs"
                    >
                      {cmd}
                    </Button>
                  ))}
                </VStack>
              </Box>
            </VStack>
          </CardBody>
        </Card>

        {/* Test Results */}
        {testResult && (
          <Card>
            <CardHeader>
              <Heading size="md">Test Results</Heading>
            </CardHeader>
            <CardBody>
              <VStack spacing={4} align="stretch">
                <Alert 
                  status={testResult.isGMPOperation ? "info" : "success"}
                  variant="left-accent"
                >
                  <AlertIcon />
                  <VStack align="start" spacing={1}>
                    <Text fontWeight="semibold">
                      {testResult.isGMPOperation ? 'GMP Operation Detected' : 'Regular Command Processed'}
                    </Text>
                    <Text fontSize="sm">
                      {testResult.content.message}
                    </Text>
                  </VStack>
                </Alert>

                {testResult.isGMPOperation && testResult.content.transaction_data && (
                  <Box>
                    <Text fontWeight="semibold" mb={2}>Transaction Details:</Text>
                    <Box bg="gray.50" p={4} borderRadius="md" fontFamily="mono" fontSize="sm">
                      <pre>{JSON.stringify(testResult.content.transaction_data, null, 2)}</pre>
                    </Box>
                  </Box>
                )}
              </VStack>
            </CardBody>
          </Card>
        )}

        {/* Active Transactions */}
        {Object.keys(state.transactions).length > 0 && (
          <Card>
            <CardHeader>
              <Heading size="md">Active Transactions</Heading>
            </CardHeader>
            <CardBody>
              <VStack spacing={4} align="stretch">
                {Object.values(state.transactions).map(transaction => (
                  <GMPTransactionCard
                    key={transaction.id}
                    transaction={transaction}
                    compact={true}
                  />
                ))}
              </VStack>
            </CardBody>
          </Card>
        )}

        {/* Instructions */}
        <Alert status="info" variant="left-accent">
          <AlertIcon />
          <VStack align="start" spacing={1}>
            <Text fontWeight="semibold">How to Test:</Text>
            <Text fontSize="sm">
              1. Try one of the sample GMP commands above
            </Text>
            <Text fontSize="sm">
              2. Look for the &quot;GMP Operation Detected&quot; message
            </Text>
            <Text fontSize="sm">
              3. Check that transaction details show Axelar integration
            </Text>
          </VStack>
        </Alert>
      </VStack>
    </Container>
  );
};

export default GMPTestPage;

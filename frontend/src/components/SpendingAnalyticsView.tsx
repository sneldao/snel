import * as React from "react";
import {
  Box,
  Text,
  VStack,
  HStack,
  Progress,
  Stat,
  StatLabel,
  StatNumber,
  StatHelpText,
  StatArrow,
  Badge,
  Icon,
  Button,
} from "@chakra-ui/react";
import { FaChartBar, FaArrowUp, FaArrowDown } from "react-icons/fa";
import { SpendingAnalytics } from "../services/paymentHistoryService";

interface SpendingAnalyticsProps {
  analytics: SpendingAnalytics;
  isLoading: boolean;
}

export const SpendingAnalyticsView: React.FC<SpendingAnalyticsProps> = ({ 
  analytics, 
  isLoading 
}) => {
  const [showDemo, setShowDemo] = React.useState(false);

  if (isLoading) {
    return (
      <Box textAlign="center" py={8}>
        <Text>Loading analytics...</Text>
      </Box>
    );
  }

  // Handle empty state with Toggle for Demo
  if (!showDemo && (parseFloat(analytics.totalSpent) === 0 && analytics.categories.length === 0)) {
    return (
      <Box textAlign="center" py={8} borderWidth="1px" borderRadius="lg" bg="gray.50">
        <Icon as={FaChartBar} boxSize={8} color="gray.400" mb={3} />
        <Text fontWeight="bold" color="gray.600">No Spending Data</Text>
        <Text fontSize="sm" color="gray.500" mb={4}>
          Make payments to see your spending analytics here.
        </Text>
        <Button size="xs" variant="link" colorScheme="blue" onClick={() => setShowDemo(true)}>
          See Example
        </Button>
      </Box>
    );
  }

  // Use real data or mock data based on toggle
  const displayData = showDemo ? {
      totalSpent: '27.8',
      period: 'month',
      categories: [
        { name: 'Payments', amount: '12.5', percentage: 45 },
        { name: 'Transfers', amount: '8.2', percentage: 30 },
        { name: 'Gifts', amount: '4.3', percentage: 15 },
        { name: 'Bills', amount: '2.8', percentage: 10 }
      ],
      trend: 'decreasing',
      comparisonPeriod: {
        amount: '32.5',
        change: -14.5
      }
  } : analytics;

  const getTrendIcon = () => {
    switch (displayData.trend) {
      case 'increasing': return <Icon as={FaArrowUp} color="red.500" />;
      case 'decreasing': return <Icon as={FaArrowDown} color="green.500" />;
      default: return null;
    }
  };

  const getTrendColor = () => {
    switch (displayData.trend) {
      case 'increasing': return 'red.500';
      case 'decreasing': return 'green.500';
      default: return 'gray.500';
    }
  };

  return (
    <VStack spacing={6} align="stretch">
      {/* Demo Banner */}
      {showDemo && (
        <HStack bg="blue.50" p={2} borderRadius="md" justify="space-between">
          <HStack>
            <Badge colorScheme="blue">EXAMPLE</Badge>
            <Text fontSize="xs" color="blue.700">This is sample data.</Text>
          </HStack>
          <Button size="xs" variant="ghost" colorScheme="blue" onClick={() => setShowDemo(false)}>
            Hide
          </Button>
        </HStack>
      )}

      {/* Total Spent */}
      <Box borderWidth="1px" borderRadius="lg" p={4}>
        <Stat>
          <StatLabel>Total Spent</StatLabel>
          <StatNumber>{displayData.totalSpent} ETH</StatNumber>
          {displayData.comparisonPeriod && (
            <StatHelpText>
              <HStack spacing={2}>
                <StatArrow type={displayData.trend === 'decreasing' ? 'decrease' : 'increase'} />
                {getTrendIcon()}
                <Text color={getTrendColor()}>
                  {Math.abs(displayData.comparisonPeriod.change).toFixed(1)}% 
                  {displayData.trend === 'decreasing' ? ' decrease' : ' increase'}
                </Text>
              </HStack>
              <Text fontSize="xs" color="gray.500">
                vs previous period ({displayData.comparisonPeriod.amount} ETH)
              </Text>
            </StatHelpText>
          )}
        </Stat>
      </Box>

      {/* Category Breakdown */}
      <Box>
        <Text fontWeight="bold" mb={3}>Spending by Category</Text>
        <VStack spacing={4} align="stretch">
          {displayData.categories.map((category, index) => (
            <Box key={index}>
              <HStack justify="space-between" mb={1}>
                <Text fontSize="sm">{category.name}</Text>
                <Text fontSize="sm" fontWeight="bold">
                  {category.amount} ETH ({category.percentage}%)
                </Text>
              </HStack>
              <Progress 
                value={category.percentage} 
                size="sm" 
                colorScheme={
                  category.percentage > 30 ? 'red' : 
                  category.percentage > 15 ? 'orange' : 'blue'
                } 
                borderRadius="full"
              />
            </Box>
          ))}
        </VStack>
      </Box>

      {/* Period Info */}
      <HStack justify="space-between" fontSize="sm" color="gray.500">
        <Text>
          Period: This {displayData.period}
        </Text>
        <Badge colorScheme="purple">
          <Icon as={FaChartBar} mr={1} />
          Analytics
        </Badge>
      </HStack>
    </VStack>
  );
};
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
  if (isLoading) {
    return (
      <Box textAlign="center" py={8}>
        <Text>Loading analytics...</Text>
      </Box>
    );
  }

  const getTrendIcon = () => {
    switch (analytics.trend) {
      case 'increasing': return <Icon as={FaArrowUp} color="red.500" />;
      case 'decreasing': return <Icon as={FaArrowDown} color="green.500" />;
      default: return null;
    }
  };

  const getTrendColor = () => {
    switch (analytics.trend) {
      case 'increasing': return 'red.500';
      case 'decreasing': return 'green.500';
      default: return 'gray.500';
    }
  };

  return (
    <VStack spacing={6} align="stretch">
      {/* Total Spent */}
      <Box borderWidth="1px" borderRadius="lg" p={4}>
        <Stat>
          <StatLabel>Total Spent</StatLabel>
          <StatNumber>{analytics.totalSpent} ETH</StatNumber>
          {analytics.comparisonPeriod && (
            <StatHelpText>
              <HStack spacing={2}>
                <StatArrow type={analytics.trend === 'decreasing' ? 'decrease' : 'increase'} />
                {getTrendIcon()}
                <Text color={getTrendColor()}>
                  {Math.abs(analytics.comparisonPeriod.change).toFixed(1)}% 
                  {analytics.trend === 'decreasing' ? ' decrease' : ' increase'}
                </Text>
              </HStack>
              <Text fontSize="xs" color="gray.500">
                vs previous period ({analytics.comparisonPeriod.amount} ETH)
              </Text>
            </StatHelpText>
          )}
        </Stat>
      </Box>

      {/* Category Breakdown */}
      <Box>
        <Text fontWeight="bold" mb={3}>Spending by Category</Text>
        <VStack spacing={4} align="stretch">
          {analytics.categories.map((category, index) => (
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
          Period: This {analytics.period}
        </Text>
        <Badge colorScheme="purple">
          <Icon as={FaChartBar} mr={1} />
          Analytics
        </Badge>
      </HStack>
    </VStack>
  );
};
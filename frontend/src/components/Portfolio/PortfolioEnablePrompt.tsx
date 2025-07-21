import React from 'react';
import { 
  Box, 
  VStack, 
  HStack, 
  Text, 
  Button, 
  Alert, 
  AlertIcon, 
  List, 
  ListItem, 
  ListIcon,
  useColorModeValue,
  Badge,
  Divider
} from '@chakra-ui/react';
import { FaChartPie, FaCheckCircle, FaClock, FaRocket } from 'react-icons/fa';

interface PortfolioEnablePromptProps {
  suggestion: {
    title: string;
    description: string;
    features: string[];
    warning: string;
  };
  onEnable: () => void;
}

export const PortfolioEnablePrompt: React.FC<PortfolioEnablePromptProps> = ({
  suggestion,
  onEnable
}) => {
  const bgColor = useColorModeValue("blue.50", "blue.900");
  const borderColor = useColorModeValue("blue.200", "blue.600");

  return (
    <Box 
      p={6} 
      borderRadius="xl" 
      borderWidth="2px" 
      borderColor={borderColor} 
      bg={bgColor}
      shadow="lg"
    >
      <VStack spacing={5} align="stretch">
        {/* Header */}
        <HStack spacing={3}>
          <Box p={3} borderRadius="full" bg="blue.500" color="white">
            <FaChartPie size="20" />
          </Box>
          <VStack align="flex-start" spacing={1}>
            <HStack>
              <Text fontSize="xl" fontWeight="bold">
                {suggestion.title}
              </Text>
              <Badge colorScheme="blue" size="sm">
                Powerful Analytics
              </Badge>
            </HStack>
            <Text color="gray.600" fontSize="md">
              {suggestion.description}
            </Text>
          </VStack>
        </HStack>
        
        <Divider />
        
        {/* Features */}
        <VStack align="stretch" spacing={3}>
          <Text fontSize="md" fontWeight="semibold" color="gray.700">
            What you&rsquo;ll get:
          </Text>
          <List spacing={2}>
            {suggestion.features.map((feature, index) => (
              <ListItem key={index} fontSize="sm">
                <ListIcon as={FaCheckCircle} color="green.500" />
                {feature}
              </ListItem>
            ))}
          </List>
        </VStack>
        
        {/* Performance Notice */}
        <Alert status="info" borderRadius="lg" variant="left-accent">
          <AlertIcon as={FaClock} />
          <VStack align="flex-start" spacing={1}>
            <Text fontSize="sm" fontWeight="medium">
              Performance Notice
            </Text>
            <Text fontSize="xs" color="gray.600">
              {suggestion.warning}
            </Text>
          </VStack>
        </Alert>
        
        {/* Actions */}
        <HStack justify="space-between" align="center" pt={2}>
          <VStack align="flex-start" spacing={0}>
            <Text fontSize="xs" color="gray.500">
              You can disable this anytime in settings
            </Text>
            <Text fontSize="xs" color="green.600" fontWeight="medium">
              ✓ Results cached for 5 minutes to avoid re-processing
            </Text>
          </VStack>
          
          <Button 
            colorScheme="blue" 
            size="lg"
            leftIcon={<FaRocket />}
            onClick={onEnable}
            fontWeight="bold"
            px={8}
          >
            Enable Portfolio Analysis
          </Button>
        </HStack>
      </VStack>
    </Box>
  );
};
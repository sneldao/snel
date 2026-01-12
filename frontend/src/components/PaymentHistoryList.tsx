import * as React from "react";
import {
  Box,
  Text,
  VStack,
  HStack,
  Badge,
  Divider,
  Icon,
  Link,
  Spinner,
  Alert,
  AlertIcon,
  AlertTitle,
  AlertDescription,
} from "@chakra-ui/react";
import { 
  FaExternalLinkAlt, 
  FaCheckCircle, 
  FaClock, 
  FaExclamationTriangle,
  FaEthereum
} from "react-icons/fa";
import { PaymentHistoryItem } from "../services/paymentHistoryService";
import { SUPPORTED_CHAINS } from "../constants/chains";

interface PaymentHistoryItemProps {
  item: PaymentHistoryItem;
}

const PaymentHistoryItemComponent: React.FC<PaymentHistoryItemProps> = ({ item }) => {
  const getStatusColor = () => {
    switch (item.status) {
      case 'confirmed': return 'green';
      case 'pending': return 'yellow';
      case 'failed': return 'red';
      default: return 'gray';
    }
  };

  const getStatusIcon = () => {
    switch (item.status) {
      case 'confirmed': return FaCheckCircle;
      case 'pending': return FaClock;
      case 'failed': return FaExclamationTriangle;
      default: return FaClock;
    }
  };

  const getChainName = () => {
    return SUPPORTED_CHAINS[item.chainId as keyof typeof SUPPORTED_CHAINS] || `Chain ${item.chainId}`;
  };

  return (
    <Box 
      p={4} 
      borderWidth="1px" 
      borderRadius="lg" 
      _hover={{ bg: "gray.50" }}
    >
      <HStack justify="space-between" align="flex-start">
        <VStack align="flex-start" spacing={1} flex={1}>
          <HStack spacing={2}>
            <Icon as={getStatusIcon()} color={`${getStatusColor()}.500`} />
            <Text fontWeight="bold" fontSize="lg">
              {item.amount} {item.token}
            </Text>
          </HStack>
          
          <Text fontSize="sm" color="gray.600" isTruncated maxW="200px">
            To: {item.recipient}
          </Text>
          
          {item.category && (
            <Badge colorScheme="blue" fontSize="xs">
              {item.category}
            </Badge>
          )}
        </VStack>
        
        <VStack align="flex-end" spacing={1}>
          <Badge colorScheme={getStatusColor()} fontSize="xs">
            {item.status.charAt(0).toUpperCase() + item.status.slice(1)}
          </Badge>
          
          <Text fontSize="xs" color="gray.500">
            {new Date(item.timestamp).toLocaleDateString()}
          </Text>
          
          <HStack spacing={1}>
            <Text fontSize="xs" color="gray.500">
              {getChainName()}
            </Text>
          </HStack>
        </VStack>
      </HStack>
      
      {item.transactionHash && (
        <HStack mt={2} justify="flex-end">
          <Link 
            href={item.explorerUrl} 
            isExternal 
            fontSize="xs" 
            color="blue.500"
          >
            View on Explorer <Icon as={FaExternalLinkAlt} ml={1} boxSize="2.5" />
          </Link>
        </HStack>
      )}
    </Box>
  );
};

interface PaymentHistoryListProps {
  items: PaymentHistoryItem[];
  isLoading: boolean;
  error?: string;
}

export const PaymentHistoryList: React.FC<PaymentHistoryListProps> = ({ 
  items, 
  isLoading, 
  error 
}) => {
  const [showDemo, setShowDemo] = React.useState(false);

  if (isLoading) {
    return (
      <VStack spacing={4} py={8}>
        <Spinner size="lg" />
        <Text>Loading payment history...</Text>
      </VStack>
    );
  }

  if (error) {
    return (
      <Alert status="error" borderRadius="lg">
        <AlertIcon />
        <VStack align="flex-start" spacing={1}>
          <AlertTitle>Error loading payment history</AlertTitle>
          <AlertDescription>{error}</AlertDescription>
        </VStack>
      </Alert>
    );
  }

  // Handle empty state with Toggle for Demo
  if (!showDemo && items.length === 0) {
    return (
      <Box textAlign="center" py={8}>
        <Text color="gray.500" mb={4}>No payment history found</Text>
        <Box as="button" fontSize="sm" color="blue.500" fontWeight="medium" onClick={() => setShowDemo(true)}>
          See Example
        </Box>
      </Box>
    );
  }

  // Mock data for demo mode
  const mockItems: PaymentHistoryItem[] = [
    {
      id: 'demo_1',
      timestamp: new Date().toISOString(),
      amount: '0.5',
      token: 'ETH',
      recipient: '0x1234...5678',
      status: 'confirmed',
      chainId: 1,
      category: 'Rent',
      transactionHash: '0xabc...def'
    },
    {
      id: 'demo_2',
      timestamp: new Date(Date.now() - 86400000).toISOString(),
      amount: '100',
      token: 'USDC',
      recipient: '0x8765...4321',
      status: 'pending',
      chainId: 8453, // Base
      category: 'Services'
    },
    {
      id: 'demo_3',
      timestamp: new Date(Date.now() - 172800000).toISOString(),
      amount: '50',
      token: 'MNEE',
      recipient: '0x9999...8888',
      status: 'confirmed',
      chainId: 1,
      category: 'Groceries'
    }
  ];

  const displayItems = showDemo ? mockItems : items;

  return (
    <VStack spacing={3} align="stretch">
      {showDemo && (
        <HStack bg="blue.50" p={2} borderRadius="md" justify="space-between" mb={2}>
          <HStack>
            <Badge colorScheme="blue">EXAMPLE</Badge>
            <Text fontSize="xs" color="blue.700">This is sample history.</Text>
          </HStack>
          <Box as="button" fontSize="xs" color="blue.700" fontWeight="bold" onClick={() => setShowDemo(false)}>
            Hide
          </Box>
        </HStack>
      )}
      
      {displayItems.map((item) => (
        <React.Fragment key={item.id}>
          <PaymentHistoryItemComponent item={item} />
          <Divider />
        </React.Fragment>
      ))}
    </VStack>
  );
};
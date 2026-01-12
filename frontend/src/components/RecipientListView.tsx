import * as React from "react";
import {
  Box,
  Text,
  VStack,
  HStack,
  Button,
  Icon,
  Badge,
  Divider,
  Input,
  InputGroup,
  InputLeftElement,
  useToast,
} from "@chakra-ui/react";
import { 
  FaUser, 
  FaEthereum, 
  FaPlus, 
  FaSearch,
  FaHistory
} from "react-icons/fa";
import { Recipient } from "../services/paymentHistoryService";

interface RecipientItemProps {
  recipient: Recipient;
  onSelect: (recipient: Recipient) => void;
}

const RecipientItem: React.FC<RecipientItemProps> = ({ recipient, onSelect }) => {
  const getChainBadge = () => {
    const chainNames: Record<number, string> = {
      1: "Ethereum",
      534352: "Scroll",
      8453: "Base",
      42161: "Arbitrum",
      10: "Optimism"
    };
    
    const chainName = chainNames[recipient.chainId || 1] || "Ethereum";
    return (
      <Badge colorScheme="purple" fontSize="xs">
        {chainName}
      </Badge>
    );
  };

  return (
    <Box 
      p={3} 
      borderWidth="1px" 
      borderRadius="lg" 
      _hover={{ bg: "gray.50", cursor: "pointer" }}
      onClick={() => onSelect(recipient)}
    >
      <HStack justify="space-between">
        <HStack spacing={3}>
          <Icon as={FaUser} color="blue.500" />
          <VStack align="flex-start" spacing={0}>
            <Text fontWeight="bold">{recipient.name}</Text>
            <Text fontSize="xs" color="gray.500" isTruncated maxW="150px">
              {recipient.address}
            </Text>
          </VStack>
        </HStack>
        
        <HStack spacing={2}>
          {recipient.chainId && getChainBadge()}
          {recipient.lastUsed && (
            <Text fontSize="xs" color="gray.500">
              {new Date(recipient.lastUsed).toLocaleDateString()}
            </Text>
          )}
        </HStack>
      </HStack>
    </Box>
  );
};

interface RecipientListViewProps {
  recipients: Recipient[];
  isLoading: boolean;
  onAddRecipient: () => void;
  onSelectRecipient: (recipient: Recipient) => void;
}

export const RecipientListView: React.FC<RecipientListViewProps> = ({ 
  recipients, 
  isLoading, 
  onAddRecipient,
  onSelectRecipient
}) => {
  const [searchTerm, setSearchTerm] = React.useState("");
  const [showDemo, setShowDemo] = React.useState(false);
  const toast = useToast();

  const mockRecipients: Recipient[] = [
    { id: 'demo_1', name: 'Alice', address: '0x123...456', lastUsed: new Date().toISOString(), chainId: 1 },
    { id: 'demo_2', name: 'Bob (Work)', address: '0xabc...def', lastUsed: new Date(Date.now() - 86400000).toISOString(), chainId: 8453 },
    { id: 'demo_3', name: 'Charlie', address: '0x789...012', chainId: 10 }
  ];

  const sourceRecipients = showDemo ? mockRecipients : recipients;

  const filteredRecipients = sourceRecipients.filter(recipient => 
    recipient.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    recipient.address.toLowerCase().includes(searchTerm.toLowerCase())
  );

  if (isLoading) {
    return (
      <Box textAlign="center" py={8}>
        <Text>Loading recipients...</Text>
      </Box>
    );
  }

  return (
    <VStack spacing={4} align="stretch">
      {/* Demo Banner */}
      {showDemo && (
        <HStack bg="blue.50" p={2} borderRadius="md" justify="space-between">
          <HStack>
            <Badge colorScheme="blue">EXAMPLE</Badge>
            <Text fontSize="xs" color="blue.700">Sample contacts.</Text>
          </HStack>
          <Box as="button" fontSize="xs" color="blue.700" fontWeight="bold" onClick={() => setShowDemo(false)}>
            Hide
          </Box>
        </HStack>
      )}

      {/* Search and Add */}
      <HStack spacing={2}>
        <InputGroup flex={1}>
          <InputLeftElement pointerEvents="none">
            <Icon as={FaSearch} color="gray.300" />
          </InputLeftElement>
          <Input
            placeholder="Search recipients..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
        </InputGroup>
        <Button 
          leftIcon={<Icon as={FaPlus} />} 
          colorScheme="blue"
          onClick={onAddRecipient}
        >
          Add
        </Button>
      </HStack>

      {/* Recipients List */}
      {filteredRecipients.length === 0 ? (
        <Box textAlign="center" py={8}>
          <Icon as={FaUser} boxSize={8} color="gray.300" mb={2} />
          <Text color="gray.500" mb={2}>No recipients found</Text>
          <Text fontSize="sm" color="gray.400" mb={3}>
            {searchTerm ? "Try a different search term" : "Add your first recipient"}
          </Text>
          {!searchTerm && !showDemo && (
             <Box as="button" fontSize="sm" color="blue.500" fontWeight="medium" onClick={() => setShowDemo(true)}>
               See Example
             </Box>
          )}
        </Box>
      ) : (
        <VStack spacing={3} align="stretch">
          {filteredRecipients.map((recipient) => (
            <React.Fragment key={recipient.id}>
              <RecipientItem 
                recipient={recipient} 
                onSelect={onSelectRecipient} 
              />
              <Divider />
            </React.Fragment>
          ))}
        </VStack>
      )}

      {/* Stats */}
      <HStack justify="space-between" fontSize="sm" color="gray.500">
        <Text>
          {sourceRecipients.length} {sourceRecipients.length === 1 ? 'recipient' : 'recipients'}
        </Text>
        <Badge colorScheme="blue">
          <Icon as={FaHistory} mr={1} />
          Address Book
        </Badge>
      </HStack>
    </VStack>
  );
};
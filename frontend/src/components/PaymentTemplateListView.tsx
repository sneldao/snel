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
  useToast,
} from "@chakra-ui/react";
import { 
  FaClock, 
  FaEthereum, 
  FaPlus, 
  FaPlay,
  FaCalendarAlt
} from "react-icons/fa";
import { PaymentTemplate } from "../services/paymentHistoryService";

interface PaymentTemplateItemProps {
  template: PaymentTemplate;
  onUseTemplate: (template: PaymentTemplate) => void;
}

const PaymentTemplateItem: React.FC<PaymentTemplateItemProps> = ({ template, onUseTemplate }) => {
  const getFrequencyLabel = () => {
    if (!template.schedule) return "One-time";
    
    switch (template.schedule.frequency) {
      case 'daily': return "Daily";
      case 'weekly': return `Weekly${template.schedule.dayOfWeek ? ` on ${['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'][template.schedule.dayOfWeek]}` : ''}`;
      case 'monthly': return `Monthly${template.schedule.dayOfMonth ? ` on day ${template.schedule.dayOfMonth}` : ''}`;
      default: return template.schedule.frequency;
    }
  };

  const getChainBadge = () => {
    const chainNames: Record<number, string> = {
      1: "Ethereum",
      534352: "Scroll",
      8453: "Base",
      42161: "Arbitrum",
      10: "Optimism"
    };
    
    const chainName = chainNames[template.chainId] || "Ethereum";
    return (
      <Badge colorScheme="purple" fontSize="xs">
        {chainName}
      </Badge>
    );
  };

  return (
    <Box 
      p={4} 
      borderWidth="1px" 
      borderRadius="lg" 
      _hover={{ bg: "gray.50" }}
    >
      <HStack justify="space-between" mb={2}>
        <Text fontWeight="bold" fontSize="lg">
          {template.name}
        </Text>
        <Badge colorScheme="blue">
          Template
        </Badge>
      </HStack>
      
      <HStack justify="space-between" mb={3}>
        <Text fontSize="md" fontWeight="semibold">
          {template.amount} {template.token}
        </Text>
        <Text fontSize="sm" color="gray.500">
          To: {template.recipient.substring(0, 6)}...{template.recipient.substring(template.recipient.length - 4)}
        </Text>
      </HStack>
      
      <HStack justify="space-between" mb={3}>
        {template.schedule ? (
          <HStack spacing={1}>
            <Icon as={FaClock} color="gray.500" />
            <Text fontSize="sm" color="gray.500">
              {getFrequencyLabel()}
            </Text>
          </HStack>
        ) : (
          <Text fontSize="sm" color="gray.500">
            One-time payment
          </Text>
        )}
        {getChainBadge()}
      </HStack>
      
      <HStack justify="flex-end">
        <Button 
          size="sm" 
          leftIcon={<Icon as={FaPlay} />} 
          colorScheme="green"
          onClick={() => onUseTemplate(template)}
        >
          Use Template
        </Button>
      </HStack>
    </Box>
  );
};

interface PaymentTemplateListViewProps {
  templates: PaymentTemplate[];
  isLoading: boolean;
  onAddTemplate: () => void;
  onUseTemplate: (template: PaymentTemplate) => void;
}

export const PaymentTemplateListView: React.FC<PaymentTemplateListViewProps> = ({ 
  templates, 
  isLoading, 
  onAddTemplate,
  onUseTemplate
}) => {
  const [showDemo, setShowDemo] = React.useState(false);
  const toast = useToast();

  const mockTemplates: PaymentTemplate[] = [
    {
        id: 'demo_1',
        name: 'Weekly Rent',
        amount: '0.5',
        token: 'ETH',
        recipient: '0x123...456',
        chainId: 1,
        createdAt: new Date().toISOString(),
        schedule: { frequency: 'weekly', dayOfWeek: 1 }
    },
    {
        id: 'demo_2',
        name: 'Monthly Subscription',
        amount: '50',
        token: 'USDC',
        recipient: '0xabc...def',
        chainId: 8453,
        createdAt: new Date().toISOString(),
        schedule: { frequency: 'monthly', dayOfMonth: 1 }
    }
  ];

  const sourceTemplates = showDemo ? mockTemplates : templates;

  if (isLoading) {
    return (
      <Box textAlign="center" py={8}>
        <Text>Loading templates...</Text>
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
            <Text fontSize="xs" color="blue.700">Sample templates.</Text>
          </HStack>
          <Box as="button" fontSize="xs" color="blue.700" fontWeight="bold" onClick={() => setShowDemo(false)}>
            Hide
          </Box>
        </HStack>
      )}

      {/* Header with Add Button */}
      <HStack justify="space-between">
        <Text fontWeight="bold" fontSize="lg">
          Payment Templates
        </Text>
        <Button 
          leftIcon={<Icon as={FaPlus} />} 
          colorScheme="blue"
          onClick={onAddTemplate}
        >
          New Template
        </Button>
      </HStack>

      {/* Templates List */}
      {sourceTemplates.length === 0 ? (
        <Box textAlign="center" py={8}>
          <Icon as={FaCalendarAlt} boxSize={8} color="gray.300" mb={2} />
          <Text color="gray.500" mb={2}>No payment templates</Text>
          <Text fontSize="sm" color="gray.400" mb={4}>
            Create templates for recurring payments
          </Text>
          <HStack justify="center" spacing={4}>
             {!showDemo && (
                <Box as="button" fontSize="sm" color="blue.500" fontWeight="medium" onClick={() => setShowDemo(true)}>
                  See Example
                </Box>
             )}
             <Button 
                size="sm"
                leftIcon={<Icon as={FaPlus} />} 
                colorScheme="blue"
                onClick={onAddTemplate}
             >
                Create First Template
             </Button>
          </HStack>
        </Box>
      ) : (
        <VStack spacing={3} align="stretch">
          {sourceTemplates.map((template) => (
            <React.Fragment key={template.id}>
              <PaymentTemplateItem 
                template={template} 
                onUseTemplate={onUseTemplate} 
              />
              <Divider />
            </React.Fragment>
          ))}
        </VStack>
      )}

      {/* Stats */}
      <HStack justify="space-between" fontSize="sm" color="gray.500">
        <Text>
          {sourceTemplates.length} {sourceTemplates.length === 1 ? 'template' : 'templates'}
        </Text>
        <Badge colorScheme="green">
          <Icon as={FaCalendarAlt} mr={1} />
          Recurring Payments
        </Badge>
      </HStack>
    </VStack>
  );
};
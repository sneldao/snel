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
  const toast = useToast();

  if (isLoading) {
    return (
      <Box textAlign="center" py={8}>
        <Text>Loading templates...</Text>
      </Box>
    );
  }

  return (
    <VStack spacing={4} align="stretch">
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
      {templates.length === 0 ? (
        <Box textAlign="center" py={8}>
          <Icon as={FaCalendarAlt} boxSize={8} color="gray.300" mb={2} />
          <Text color="gray.500" mb={2}>No payment templates</Text>
          <Text fontSize="sm" color="gray.400" mb={4}>
            Create templates for recurring payments
          </Text>
          <Button 
            leftIcon={<Icon as={FaPlus} />} 
            colorScheme="blue"
            onClick={onAddTemplate}
          >
            Create First Template
          </Button>
        </Box>
      ) : (
        <VStack spacing={3} align="stretch">
          {templates.map((template) => (
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
          {templates.length} {templates.length === 1 ? 'template' : 'templates'}
        </Text>
        <Badge colorScheme="green">
          <Icon as={FaCalendarAlt} mr={1} />
          Recurring Payments
        </Badge>
      </HStack>
    </VStack>
  );
};
import * as React from "react";
import {
  Box,
  HStack,
  Button,
  Icon,
  Text,
  useDisclosure,
  Modal,
  ModalOverlay,
  ModalContent,
  ModalHeader,
  ModalBody,
  ModalCloseButton,
  VStack,
  Divider,
} from "@chakra-ui/react";
import { 
  FaPaperPlane, 
  FaHistory, 
  FaClock, 
  FaAddressBook,
  FaChartBar,
  FaChevronRight
} from "react-icons/fa";

interface PaymentQuickActionsProps {
  onCommandSubmit: (command: string) => void;
  isVisible: boolean;
}

export const PaymentQuickActions: React.FC<PaymentQuickActionsProps> = ({
  onCommandSubmit,
  isVisible,
}) => {
  const { isOpen, onOpen, onClose } = useDisclosure();

  const handleQuickAction = (command: string) => {
    onCommandSubmit(command);
  };

  const quickActions = [
    {
      icon: FaPaperPlane,
      label: "Send Payment",
      command: "send ",
      color: "blue",
    },
    {
      icon: FaHistory,
      label: "Payment History",
      command: "show my payment history",
      color: "green",
    },
    {
      icon: FaChartBar,
      label: "Spending Analytics",
      command: "show my spending analytics",
      color: "purple",
    },
    {
      icon: FaClock,
      label: "Scheduled Payments",
      command: "show my scheduled payments",
      color: "orange",
    },
    {
      icon: FaAddressBook,
      label: "Saved Recipients",
      command: "show my saved recipients",
      color: "teal",
    },
  ];

  if (!isVisible) return null;

  return (
    <>
      <Box 
        bg="gray.50" 
        borderRadius="lg" 
        p={3}
        mb={4}
      >
        <Text fontSize="sm" fontWeight="bold" mb={2} color="gray.700">
          Payment Actions
        </Text>
        <HStack spacing={2} wrap="wrap">
          {quickActions.map((action, index) => (
            <Button
              key={index}
              size="sm"
              leftIcon={<Icon as={action.icon} />}
              colorScheme={action.color}
              variant="outline"
              onClick={() => handleQuickAction(action.command)}
              flex="1"
              minW="120px"
              justifyContent="flex-start"
            >
              <Text fontSize="xs">{action.label}</Text>
            </Button>
          ))}
        </HStack>
      </Box>

      {/* Full Payment Dashboard Modal */}
      <Modal isOpen={isOpen} onClose={onClose} size="md">
        <ModalOverlay />
        <ModalContent>
          <ModalHeader>Payment Dashboard</ModalHeader>
          <ModalCloseButton />
          <ModalBody pb={6}>
            <VStack align="stretch" spacing={4}>
              {quickActions.map((action, index) => (
                <React.Fragment key={index}>
                  <Button
                    variant="ghost"
                    justifyContent="space-between"
                    rightIcon={<FaChevronRight />}
                    onClick={() => {
                      handleQuickAction(action.command);
                      onClose();
                    }}
                    py={6}
                  >
                    <HStack spacing={3}>
                      <Icon as={action.icon} boxSize={5} color={`${action.color}.500`} />
                      <Text fontWeight="medium">{action.label}</Text>
                    </HStack>
                  </Button>
                  {index < quickActions.length - 1 && <Divider />}
                </React.Fragment>
              ))}
            </VStack>
          </ModalBody>
        </ModalContent>
      </Modal>
    </>
  );
};
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
  Spinner,
} from "@chakra-ui/react";
import { 
  FaPaperPlane, 
  FaHistory, 
  FaClock, 
  FaAddressBook,
  FaChartBar,
  FaChevronRight,
  FaPlus,
} from "react-icons/fa";
import { PaymentAction, PaymentHistoryService } from "../services/paymentHistoryService";

interface PaymentQuickActionsProps {
  onCommandSubmit: (command: string) => void;
  isVisible: boolean;
  walletAddress?: string;
  paymentService?: PaymentHistoryService;
}

export const PaymentQuickActions: React.FC<PaymentQuickActionsProps> = ({
  onCommandSubmit,
  isVisible,
  walletAddress,
  paymentService,
}) => {
  const { isOpen, onOpen, onClose } = useDisclosure();
  const [userActions, setUserActions] = React.useState<PaymentAction[]>([]);
  const [isLoading, setIsLoading] = React.useState(false);

  // Load user's payment actions on mount and when wallet changes
  React.useEffect(() => {
    if (walletAddress && paymentService) {
      loadUserActions();
    }
  }, [walletAddress, paymentService]);

  const loadUserActions = async () => {
    if (!walletAddress || !paymentService) return;
    
    setIsLoading(true);
    try {
      const actions = await paymentService.getQuickActions(walletAddress);
      setUserActions(actions);
    } catch (error) {
      console.error("Error loading user actions:", error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleQuickAction = (command: string) => {
    onCommandSubmit(command);
  };

  // System actions (always available)
  const systemActions = [
    {
      icon: FaHistory,
      label: "History",
      command: "show my payment history",
      color: "green",
      description: "View transactions",
    },
    {
      icon: FaChartBar,
      label: "Analytics",
      command: "show my spending analytics",
      color: "purple",
      description: "Spending insights",
    },
    {
      icon: FaClock,
      label: "Scheduled",
      command: "show my scheduled payments",
      color: "orange",
      description: "Recurring payments",
    },
    {
      icon: FaAddressBook,
      label: "Recipients",
      command: "show my saved recipients",
      color: "teal",
      description: "Saved addresses",
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
        <HStack justify="space-between" mb={2}>
          <Text fontSize="sm" fontWeight="bold" color="gray.700">
            Payment Actions
          </Text>
          <Button
            size="xs"
            leftIcon={<Icon as={FaPlus} />}
            variant="ghost"
            onClick={() => handleQuickAction("create payment action")}
          >
            New
          </Button>
        </HStack>

        {isLoading ? (
          <Spinner size="sm" />
        ) : (
          <Box
            display="flex"
            flexDirection={{ base: "column", md: "row" }}
            flexWrap={{ base: "nowrap", md: "wrap" }}
            gap={2}
          >
            {/* User's pinned quick actions */}
            {userActions.map((action) => (
              <Button
                key={action.id}
                size="sm"
                leftIcon={<Icon as={FaPaperPlane} />}
                colorScheme="blue"
                variant="outline"
                onClick={() => handleQuickAction(`use action ${action.id}`)}
                flex={{ base: "1 1 auto", md: "1" }}
                minW={{ base: "auto", md: "120px" }}
                justifyContent="flex-start"
                title={`${action.amount} ${action.token} to ${action.recipientAddress.slice(0, 10)}...`}
              >
                <Text fontSize="xs" isTruncated>{action.name}</Text>
              </Button>
            ))}

            {/* System actions */}
            {systemActions.map((action, index) => (
              <Button
                key={`system_${index}`}
                size="sm"
                leftIcon={<Icon as={action.icon} />}
                colorScheme={action.color}
                variant="outline"
                onClick={() => handleQuickAction(action.command)}
                flex={{ base: "1 1 auto", md: "1" }}
                minW={{ base: "auto", md: "120px" }}
                justifyContent="flex-start"
              >
                <Text fontSize="xs">{action.label}</Text>
              </Button>
            ))}
          </Box>
        )}
      </Box>

      {/* Full Payment Dashboard Modal */}
      <Modal isOpen={isOpen} onClose={onClose} size="lg">
        <ModalOverlay />
        <ModalContent>
          <ModalHeader>Payment Dashboard</ModalHeader>
          <ModalCloseButton />
          <ModalBody pb={6}>
            <VStack align="stretch" spacing={4}>
              {/* User's Actions Section */}
              {userActions.length > 0 && (
                <>
                  <Text fontSize="sm" fontWeight="bold">Your Actions</Text>
                  {userActions.map((action) => (
                    <Button
                      key={action.id}
                      variant="ghost"
                      justifyContent="space-between"
                      rightIcon={<FaChevronRight />}
                      onClick={() => {
                        handleQuickAction(`use action ${action.id}`);
                        onClose();
                      }}
                      py={6}
                    >
                      <HStack spacing={3} flex={1}>
                        <Icon as={FaPaperPlane} boxSize={5} color="blue.500" />
                        <VStack align="flex-start" spacing={0}>
                          <Text fontWeight="medium">{action.name}</Text>
                          <Text fontSize="xs" color="gray.500">
                            {action.amount} {action.token}
                          </Text>
                        </VStack>
                      </HStack>
                    </Button>
                  ))}
                </>
              )}

              {/* System Actions */}
              <Text fontSize="sm" fontWeight="bold">System Actions</Text>
              {systemActions.map((action, index) => (
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
                      <VStack align="flex-start" spacing={0}>
                        <Text fontWeight="medium">{action.label}</Text>
                        <Text fontSize="xs" color="gray.500">
                          {action.description}
                        </Text>
                      </VStack>
                    </HStack>
                  </Button>
                  {index < systemActions.length - 1 && <Divider />}
                </React.Fragment>
              ))}
            </VStack>
          </ModalBody>
        </ModalContent>
      </Modal>
    </>
  );
};
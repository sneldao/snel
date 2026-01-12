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
  useToast,
  AlertDialog,
  AlertDialogBody,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogContent,
  AlertDialogOverlay,
} from "@chakra-ui/react";
import { 
  FaPaperPlane, 
  FaHistory, 
  FaClock, 
  FaAddressBook,
  FaChartBar,
  FaChevronRight,
  FaPlus,
  FaRobot,
  FaLeaf,
  FaTrash,
  FaEyeSlash,
  FaEye,
} from "react-icons/fa";
import { PaymentAction, PaymentHistoryService } from "../services/paymentHistoryService";
import { ApiService } from "../services/apiService";

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
  const [deleteConfirmId, setDeleteConfirmId] = React.useState<string | null>(null);
  const [isDeleting, setIsDeleting] = React.useState(false);
  const toast = useToast();
  const cancelRef = React.useRef(null);
  const apiService = React.useMemo(() => new ApiService(), []);

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

  const handleDeleteAction = async (actionId: string) => {
    setIsDeleting(true);
    try {
      await apiService.delete(`/api/v1/payment-actions/${actionId}?wallet_address=${walletAddress}`);
      
      // Reload actions
      await loadUserActions();
      
      toast({
        title: "Action Deleted",
        description: "Payment action has been removed.",
        status: "success",
        duration: 3000,
        isClosable: true,
      });
    } catch (error) {
      console.error("Error deleting action:", error);
      toast({
        title: "Error",
        description: "Failed to delete payment action.",
        status: "error",
        duration: 3000,
        isClosable: true,
      });
    } finally {
      setIsDeleting(false);
      setDeleteConfirmId(null);
    }
  };

  const handleToggleEnabled = async (action: PaymentAction) => {
    try {
      const newEnabledState = !action.isEnabled;
      
      await apiService.put(`/api/v1/payment-actions/${action.id}?wallet_address=${walletAddress}`, {
        is_enabled: newEnabledState,
      });
      
      // Update local state
      setUserActions(prev => 
        prev.map(a => 
          a.id === action.id 
            ? { ...a, isEnabled: newEnabledState }
            : a
        )
      );
      
      toast({
        title: newEnabledState ? "Action Enabled" : "Action Disabled",
        description: newEnabledState 
          ? "Payment action is now active."
          : "Payment action has been paused.",
        status: "success",
        duration: 3000,
        isClosable: true,
      });
    } catch (error) {
      console.error("Error updating action:", error);
      toast({
        title: "Error",
        description: "Failed to update payment action.",
        status: "error",
        duration: 3000,
        isClosable: true,
      });
    }
  };

  // System actions (always available)
  // Showcase x402 agent automation features for hackathon judges
  const systemActions = [
    {
      icon: FaHistory,
      label: "History",
      command: "show my payment history",
      color: "green",
      description: "All transactions",
    },
    {
      icon: FaClock,
      label: "Recurring",
      command: "setup recurring payment",
      color: "orange",
      description: "Scheduled MNEE payments",
    },
    {
      icon: FaRobot,
      label: "Auto Rebalance",
      command: "setup automated portfolio rebalancing",
      color: "blue",
      description: "Agent-triggered rebalancing",
    },
    {
      icon: FaLeaf,
      label: "Yield Farm",
      command: "setup automated yield farming",
      color: "teal",
      description: "Agent finds best APY",
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
                    <Box
                      key={action.id}
                      borderWidth="1px"
                      borderRadius="lg"
                      p={4}
                      bg={action.isEnabled ? "white" : "gray.50"}
                      opacity={action.isEnabled ? 1 : 0.7}
                    >
                      <HStack justify="space-between" mb={3}>
                        <VStack align="flex-start" spacing={1} flex={1}>
                          <Text fontWeight="medium">{action.name}</Text>
                          <Text fontSize="xs" color="gray.500">
                            {action.amount} {action.token}
                          </Text>
                        </VStack>
                        <Text fontSize="xs" color={action.isEnabled ? "green.500" : "orange.500"}>
                          {action.isEnabled ? "Active" : "Paused"}
                        </Text>
                      </HStack>
                      
                      <HStack spacing={2} justify="flex-end">
                        <Button
                          size="sm"
                          variant="outline"
                          colorScheme="blue"
                          onClick={() => {
                            handleQuickAction(`use action ${action.id}`);
                            onClose();
                          }}
                        >
                          Execute
                        </Button>
                        <Button
                          size="sm"
                          variant="outline"
                          leftIcon={<Icon as={action.isEnabled ? FaEyeSlash : FaEye} />}
                          colorScheme={action.isEnabled ? "orange" : "green"}
                          onClick={() => handleToggleEnabled(action)}
                        >
                          {action.isEnabled ? "Pause" : "Enable"}
                        </Button>
                        <Button
                          size="sm"
                          variant="outline"
                          colorScheme="red"
                          leftIcon={<Icon as={FaTrash} />}
                          onClick={() => setDeleteConfirmId(action.id)}
                        >
                          Delete
                        </Button>
                      </HStack>
                    </Box>
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

        {/* Delete Confirmation Dialog */}
        <AlertDialog
        isOpen={deleteConfirmId !== null}
        leastDestructiveRef={cancelRef}
        onClose={() => setDeleteConfirmId(null)}
        >
        <AlertDialogOverlay>
          <AlertDialogContent>
            <AlertDialogHeader fontSize="lg" fontWeight="bold">
              Delete Payment Action
            </AlertDialogHeader>

            <AlertDialogBody>
              Are you sure you want to delete this payment action? This action cannot be undone.
            </AlertDialogBody>

            <AlertDialogFooter>
              <Button ref={cancelRef} onClick={() => setDeleteConfirmId(null)}>
                Cancel
              </Button>
              <Button
                colorScheme="red"
                onClick={() => deleteConfirmId && handleDeleteAction(deleteConfirmId)}
                ml={3}
                isLoading={isDeleting}
              >
                Delete
              </Button>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialogOverlay>
        </AlertDialog>
        </>
        );
        };
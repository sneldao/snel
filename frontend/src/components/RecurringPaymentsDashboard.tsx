import React, { useState, useEffect } from 'react';
import {
  Modal,
  ModalOverlay,
  ModalContent,
  ModalHeader,
  ModalBody,
  ModalCloseButton,
  VStack,
  HStack,
  Text,
  Badge,
  Button,
  Box,
  Spinner,
  useColorModeValue,
  IconButton,
  Tooltip,
} from '@chakra-ui/react';
import { FaPause, FaPlay, FaTrash, FaClock } from 'react-icons/fa';
import { PaymentActionService, PaymentActionResponse } from '../services/paymentActionService';
import { useAccount } from 'wagmi';

interface RecurringPaymentsDashboardProps {
  isOpen: boolean;
  onClose: () => void;
}

export const RecurringPaymentsDashboard: React.FC<RecurringPaymentsDashboardProps> = ({
  isOpen,
  onClose,
}) => {
  const { address } = useAccount();
  const [paymentActions, setPaymentActions] = useState<PaymentActionResponse[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const bg = useColorModeValue('white', 'gray.800');
  const borderColor = useColorModeValue('gray.200', 'gray.600');

  const paymentActionService = new PaymentActionService();

  useEffect(() => {
    if (isOpen && address) {
      fetchPaymentActions();
    }
  }, [isOpen, address]);

  const fetchPaymentActions = async () => {
    if (!address) return;
    
    setLoading(true);
    setError(null);
    try {
      const actions = await paymentActionService.getPaymentActions(address);
      setPaymentActions(actions);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load payment actions');
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (actionId: string) => {
    if (!address) return;
    
    try {
      await paymentActionService.deletePaymentAction(address, actionId);
      await fetchPaymentActions(); // Refresh list
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete payment action');
    }
  };

  const getStatusBadge = (status: string) => {
    const statusColors = {
      active: 'green',
      paused: 'yellow',
      cancelled: 'red',
      completed: 'gray',
    };
    return (
      <Badge colorScheme={statusColors[status as keyof typeof statusColors] || 'gray'}>
        {status.toUpperCase()}
      </Badge>
    );
  };

  const formatFrequency = (frequency: string) => {
    return frequency.charAt(0).toUpperCase() + frequency.slice(1);
  };

  const truncateAddress = (address: string) => {
    return `${address.slice(0, 6)}...${address.slice(-4)}`;
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} size="xl">
      <ModalOverlay />
      <ModalContent bg={bg}>
        <ModalHeader>
          <HStack>
            <FaClock />
            <Text>Recurring Payments</Text>
          </HStack>
        </ModalHeader>
        <ModalCloseButton />
        <ModalBody pb={6}>
          {loading ? (
            <Box textAlign="center" py={8}>
              <Spinner size="lg" />
              <Text mt={4} color="gray.500">Loading payment actions...</Text>
            </Box>
          ) : error ? (
            <Box textAlign="center" py={8}>
              <Text color="red.500">{error}</Text>
              <Button mt={4} onClick={fetchPaymentActions}>Retry</Button>
            </Box>
          ) : paymentActions.length === 0 ? (
            <Box textAlign="center" py={8}>
              <Text color="gray.500">No recurring payments found</Text>
              <Text fontSize="sm" color="gray.400" mt={2}>
                Create one by typing "pay 1 USDC to recipient.eth weekly"
              </Text>
            </Box>
          ) : (
            <VStack spacing={4} align="stretch">
              {paymentActions.map((action) => (
                <Box
                  key={action.id}
                  p={4}
                  border="1px solid"
                  borderColor={borderColor}
                  borderRadius="lg"
                  bg={bg}
                >
                  <HStack justify="space-between" mb={2}>
                    <VStack align="start" spacing={1}>
                      <Text fontWeight="bold">{action.name}</Text>
                      <HStack spacing={2}>
                        <Text fontSize="sm" color="gray.500">
                          {action.amount} {action.token}
                        </Text>
                        <Text fontSize="sm" color="gray.500">•</Text>
                        <Text fontSize="sm" color="gray.500">
                          {formatFrequency(action.schedule?.frequency || 'once')}
                        </Text>
                        <Text fontSize="sm" color="gray.500">•</Text>
                        <Text fontSize="sm" color="gray.500" fontFamily="mono">
                          {truncateAddress(action.recipient_address)}
                        </Text>
                      </HStack>
                    </VStack>
                    <HStack>
                      {getStatusBadge(action.is_enabled ? 'active' : 'paused')}
                      <Tooltip label="Delete">
                        <IconButton
                          aria-label="Delete payment action"
                          icon={<FaTrash />}
                          size="sm"
                          colorScheme="red"
                          variant="ghost"
                          onClick={() => handleDelete(action.id)}
                        />
                      </Tooltip>
                    </HStack>
                  </HStack>
                  
                  {action.metadata?.description && (
                    <Text fontSize="sm" color="gray.600" mt={2}>
                      {action.metadata.description}
                    </Text>
                  )}
                </Box>
              ))}
            </VStack>
          )}
        </ModalBody>
      </ModalContent>
    </Modal>
  );
};

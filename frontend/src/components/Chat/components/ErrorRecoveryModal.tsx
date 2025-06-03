import React from "react";
import {
  Modal,
  ModalOverlay,
  ModalContent,
  ModalHeader,
  ModalBody,
  ModalFooter,
  Button,
  VStack,
  Text,
  Icon,
  HStack,
  Divider,
} from "@chakra-ui/react";
import {
  FaExclamationTriangle,
  FaRedo,
  FaCog,
  FaExchangeAlt,
} from "react-icons/fa";

interface ErrorRecoveryModalProps {
  isOpen: boolean;
  onClose: () => void;
  error?: {
    code: string;
    message: string;
    recovery_options?: string[];
  };
  onRetry: () => void;
}

export const ErrorRecoveryModal: React.FC<ErrorRecoveryModalProps> = ({
  isOpen,
  onClose,
  error,
  onRetry,
}) => {
  const getActionIcon = (option: string) => {
    if (option.toLowerCase().includes("retry")) return FaRedo;
    if (option.toLowerCase().includes("parameters")) return FaCog;
    if (option.toLowerCase().includes("chains")) return FaExchangeAlt;
    return FaExclamationTriangle;
  };

  const handleOptionClick = (option: string) => {
    if (option.toLowerCase().includes("retry")) {
      onRetry();
    }
    onClose();
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} isCentered>
      <ModalOverlay />
      <ModalContent bg="gray.800">
        <ModalHeader>
          <HStack spacing={2} color="red.400">
            <Icon as={FaExclamationTriangle} />
            <Text>Error Recovery</Text>
          </HStack>
        </ModalHeader>
        <ModalBody>
          <VStack spacing={4} align="stretch">
            <Text color="red.400">{error?.code}</Text>
            <Text>{error?.message}</Text>
            <Divider />
            <Text fontWeight="medium">Recovery Options:</Text>
            <VStack align="stretch" spacing={2}>
              {error?.recovery_options?.map((option, idx) => (
                <Button
                  key={idx}
                  variant="ghost"
                  justifyContent="flex-start"
                  leftIcon={<Icon as={getActionIcon(option)} />}
                  onClick={() => handleOptionClick(option)}
                >
                  {option}
                </Button>
              ))}
            </VStack>
          </VStack>
        </ModalBody>
        <ModalFooter>
          <Button variant="outline" onClick={onClose}>
            Close
          </Button>
        </ModalFooter>
      </ModalContent>
    </Modal>
  );
};

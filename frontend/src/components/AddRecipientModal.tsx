import * as React from "react";
import {
  Modal,
  ModalOverlay,
  ModalContent,
  ModalHeader,
  ModalFooter,
  ModalBody,
  ModalCloseButton,
  Button,
  FormControl,
  FormLabel,
  Input,
  Select,
  useToast,
  VStack,
  Text,
} from "@chakra-ui/react";
import { Recipient } from "../services/paymentHistoryService";
import { SUPPORTED_CHAINS } from "../constants/chains";

interface AddRecipientModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSave: (recipient: Omit<Recipient, 'id'>) => Promise<void>;
  chainId?: number;
}

export const AddRecipientModal: React.FC<AddRecipientModalProps> = ({
  isOpen,
  onClose,
  onSave,
  chainId,
}) => {
  const toast = useToast();
  const [name, setName] = React.useState("");
  const [address, setAddress] = React.useState("");
  const [selectedChainId, setSelectedChainId] = React.useState<string>(chainId?.toString() || "1");
  const [isLoading, setIsLoading] = React.useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    // Basic validation
    if (!name.trim()) {
      toast({
        title: "Validation Error",
        description: "Please enter a name for the recipient",
        status: "error",
        duration: 3000,
        isClosable: true,
      });
      return;
    }
    
    if (!address.trim()) {
      toast({
        title: "Validation Error",
        description: "Please enter a wallet address",
        status: "error",
        duration: 3000,
        isClosable: true,
      });
      return;
    }
    
    // Simple address validation (basic format check)
    if (!address.startsWith("0x") || address.length !== 42) {
      toast({
        title: "Validation Error",
        description: "Please enter a valid Ethereum-style address",
        status: "error",
        duration: 3000,
        isClosable: true,
      });
      return;
    }
    
    setIsLoading(true);
    
    try {
      await onSave({
        name: name.trim(),
        address: address.trim(),
        chainId: parseInt(selectedChainId),
      });
      
      toast({
        title: "Success",
        description: "Recipient added successfully",
        status: "success",
        duration: 3000,
        isClosable: true,
      });
      
      // Reset form
      setName("");
      setAddress("");
      onClose();
    } catch (error) {
      console.error("Error saving recipient:", error);
      toast({
        title: "Error",
        description: "Failed to add recipient. Please try again.",
        status: "error",
        duration: 5000,
        isClosable: true,
      });
    } finally {
      setIsLoading(false);
    }
  };

  const chainOptions = Object.entries(SUPPORTED_CHAINS).map(([id, name]) => (
    <option key={id} value={id}>
      {name}
    </option>
  ));

  return (
    <Modal isOpen={isOpen} onClose={onClose} isCentered>
      <ModalOverlay />
      <ModalContent>
        <form onSubmit={handleSubmit}>
          <ModalHeader>Add New Recipient</ModalHeader>
          <ModalCloseButton />
          <ModalBody>
            <VStack spacing={4}>
              <FormControl isRequired>
                <FormLabel>Name</FormLabel>
                <Input
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="e.g., Alice"
                  autoFocus
                />
              </FormControl>
              
              <FormControl isRequired>
                <FormLabel>Wallet Address</FormLabel>
                <Input
                  value={address}
                  onChange={(e) => setAddress(e.target.value)}
                  placeholder="0x..."
                  fontFamily="mono"
                />
                <Text fontSize="sm" color="gray.500" mt={1}>
                  Enter a valid wallet address
                </Text>
              </FormControl>
              
              <FormControl>
                <FormLabel>Network</FormLabel>
                <Select
                  value={selectedChainId}
                  onChange={(e) => setSelectedChainId(e.target.value)}
                >
                  {chainOptions}
                </Select>
              </FormControl>
            </VStack>
          </ModalBody>
          
          <ModalFooter>
            <Button variant="ghost" mr={3} onClick={onClose}>
              Cancel
            </Button>
            <Button 
              colorScheme="blue" 
              type="submit" 
              isLoading={isLoading}
              isDisabled={!name.trim() || !address.trim()}
            >
              Add Recipient
            </Button>
          </ModalFooter>
        </form>
      </ModalContent>
    </Modal>
  );
};
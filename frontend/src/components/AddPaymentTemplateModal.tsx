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
  Checkbox,
  VStack,
  HStack,
  Text,
  NumberInput,
  NumberInputField,
  NumberInputStepper,
  NumberIncrementStepper,
  NumberDecrementStepper,
  useToast,
} from "@chakra-ui/react";
import { PaymentTemplate } from "../services/paymentHistoryService";
import { SUPPORTED_CHAINS } from "../constants/chains";

interface AddPaymentTemplateModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSave: (template: Omit<PaymentTemplate, 'id' | 'createdAt'>) => Promise<void>;
  chainId?: number;
}

export const AddPaymentTemplateModal: React.FC<AddPaymentTemplateModalProps> = ({
  isOpen,
  onClose,
  onSave,
  chainId,
}) => {
  const toast = useToast();
  const [name, setName] = React.useState("");
  const [amount, setAmount] = React.useState("");
  const [token, setToken] = React.useState("ETH");
  const [recipient, setRecipient] = React.useState("");
  const [isRecurring, setIsRecurring] = React.useState(false);
  const [frequency, setFrequency] = React.useState<"hourly" | "daily" | "weekly" | "monthly">("monthly");
  const [dayOfWeek, setDayOfWeek] = React.useState<number>(1); // Monday
  const [dayOfMonth, setDayOfMonth] = React.useState<number>(1);
  const [selectedChainId, setSelectedChainId] = React.useState<string>(chainId?.toString() || "1");
  const [isLoading, setIsLoading] = React.useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    // Basic validation
    if (!name.trim()) {
      toast({
        title: "Validation Error",
        description: "Please enter a name for the template",
        status: "error",
        duration: 3000,
        isClosable: true,
      });
      return;
    }
    
    if (!amount || parseFloat(amount) <= 0) {
      toast({
        title: "Validation Error",
        description: "Please enter a valid amount",
        status: "error",
        duration: 3000,
        isClosable: true,
      });
      return;
    }
    
    if (!recipient.trim()) {
      toast({
        title: "Validation Error",
        description: "Please enter a recipient address",
        status: "error",
        duration: 3000,
        isClosable: true,
      });
      return;
    }
    
    // Simple address validation (basic format check)
    if (!recipient.startsWith("0x") || recipient.length !== 42) {
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
      const templateData: Omit<PaymentTemplate, 'id' | 'createdAt'> = {
        name: name.trim(),
        amount,
        token,
        recipient: recipient.trim(),
        chainId: parseInt(selectedChainId),
      };
      
      // Add schedule if recurring
      if (isRecurring) {
        templateData.schedule = {
          frequency,
        };
        
        if (frequency === "weekly") {
          templateData.schedule.dayOfWeek = dayOfWeek;
        } else if (frequency === "monthly") {
          templateData.schedule.dayOfMonth = dayOfMonth;
        }
      }
      
      await onSave(templateData);
      
      toast({
        title: "Success",
        description: "Payment template created successfully",
        status: "success",
        duration: 3000,
        isClosable: true,
      });
      
      // Reset form
      setName("");
      setAmount("");
      setToken("ETH");
      setRecipient("");
      setIsRecurring(false);
      setFrequency("monthly");
      setDayOfWeek(1);
      setDayOfMonth(1);
      onClose();
    } catch (error) {
      console.error("Error saving template:", error);
      toast({
        title: "Error",
        description: "Failed to create payment template. Please try again.",
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

  const commonTokens = ["ETH", "USDC", "USDT", "DAI", "WBTC"];

  return (
    <Modal isOpen={isOpen} onClose={onClose} isCentered size="lg">
      <ModalOverlay />
      <ModalContent>
        <form onSubmit={handleSubmit}>
          <ModalHeader>Create Payment Template</ModalHeader>
          <ModalCloseButton />
          <ModalBody>
            <VStack spacing={4}>
              <FormControl isRequired>
                <FormLabel>Name</FormLabel>
                <Input
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="e.g., Monthly Rent"
                  autoFocus
                />
              </FormControl>
              
              <HStack spacing={4} width="100%">
                <FormControl isRequired>
                  <FormLabel>Amount</FormLabel>
                  <NumberInput
                    value={amount}
                    onChange={(value) => setAmount(value)}
                    precision={6}
                    step={0.1}
                  >
                    <NumberInputField placeholder="0.00" />
                    <NumberInputStepper>
                      <NumberIncrementStepper />
                      <NumberDecrementStepper />
                    </NumberInputStepper>
                  </NumberInput>
                </FormControl>
                
                <FormControl isRequired>
                  <FormLabel>Token</FormLabel>
                  <Select
                    value={token}
                    onChange={(e) => setToken(e.target.value)}
                  >
                    {commonTokens.map((t) => (
                      <option key={t} value={t}>
                        {t}
                      </option>
                    ))}
                  </Select>
                </FormControl>
              </HStack>
              
              <FormControl isRequired>
                <FormLabel>Recipient Address</FormLabel>
                <Input
                  value={recipient}
                  onChange={(e) => setRecipient(e.target.value)}
                  placeholder="0x..."
                  fontFamily="mono"
                />
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
              
              <Checkbox
                isChecked={isRecurring}
                onChange={(e) => setIsRecurring(e.target.checked)}
              >
                Make this a recurring payment
              </Checkbox>
              
              {isRecurring && (
                <VStack spacing={4} width="100%" pl={6}>
                  <FormControl>
                    <FormLabel>Frequency</FormLabel>
                    <Select
                      value={frequency}
                      onChange={(e) => setFrequency(e.target.value as any)}
                    >
                      <option value="hourly">Hourly</option>
                      <option value="daily">Daily</option>
                      <option value="weekly">Weekly</option>
                      <option value="monthly">Monthly</option>
                    </Select>
                  </FormControl>
                  
                  {frequency === "weekly" && (
                    <FormControl>
                      <FormLabel>Day of Week</FormLabel>
                      <Select
                        value={dayOfWeek}
                        onChange={(e) => setDayOfWeek(parseInt(e.target.value))}
                      >
                        <option value="0">Sunday</option>
                        <option value="1">Monday</option>
                        <option value="2">Tuesday</option>
                        <option value="3">Wednesday</option>
                        <option value="4">Thursday</option>
                        <option value="5">Friday</option>
                        <option value="6">Saturday</option>
                      </Select>
                    </FormControl>
                  )}
                  
                  {frequency === "monthly" && (
                    <FormControl>
                      <FormLabel>Day of Month</FormLabel>
                      <NumberInput
                        value={dayOfMonth}
                        onChange={(value) => setDayOfMonth(parseInt(value) || 1)}
                        min={1}
                        max={31}
                      >
                        <NumberInputField />
                        <NumberInputStepper>
                          <NumberIncrementStepper />
                          <NumberDecrementStepper />
                        </NumberInputStepper>
                      </NumberInput>
                    </FormControl>
                  )}
                </VStack>
              )}
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
              isDisabled={!name.trim() || !amount || !recipient.trim()}
            >
              Create Template
            </Button>
          </ModalFooter>
        </form>
      </ModalContent>
    </Modal>
  );
};
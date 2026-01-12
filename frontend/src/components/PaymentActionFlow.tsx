/**
 * Payment action flow component - guided creation through natural conversation.
 * 
 * DESIGN ETHOS: Keeps payment customization entirely in chat, no modals or forms.
 * Uses multi-step conversation pattern for intuitive action building.
 */
import * as React from "react";
import {
  Box,
  VStack,
  HStack,
  Button,
  Input,
  Select,
  Text,
  Checkbox,
  useToast,
  FormControl,
  FormLabel,
  NumberInput,
  NumberInputField,
  NumberInputStepper,
  NumberIncrementStepper,
  NumberDecrementStepper,
} from "@chakra-ui/react";
import { PaymentAction, PaymentHistoryService } from "../services/paymentHistoryService";
import { SUPPORTED_CHAINS } from "../constants/chains";

interface PaymentActionFlowProps {
  walletAddress: string;
  paymentService: PaymentHistoryService;
  onActionCreated: (action: PaymentAction) => void;
  onFlowComplete: () => void;
}

type FlowStep = 
  | "name"
  | "type"
  | "recipient"
  | "amount"
  | "token"
  | "chain"
  | "recurring"
  | "frequency"
  | "confirmation";

interface FlowState {
  step: FlowStep;
  data: Partial<PaymentAction>;
}

export const PaymentActionFlow: React.FC<PaymentActionFlowProps> = ({
  walletAddress,
  paymentService,
  onActionCreated,
  onFlowComplete,
}) => {
  const toast = useToast();
  const [state, setState] = React.useState<FlowState>({
    step: "name",
    data: {
      walletAddress,
      actionType: "template",
      isEnabled: true,
      isPinned: false,
      order: 0,
      usageCount: 0,
    },
  });

  const handleNext = (stepData: any) => {
    const steps: FlowStep[] = [
      "name",
      "type",
      "recipient",
      "amount",
      "token",
      "chain",
      "recurring",
      "frequency",
      "confirmation",
    ];

    const currentIndex = steps.indexOf(state.step);
    const nextIndex = currentIndex + 1;

    setState({
      step: nextIndex < steps.length ? steps[nextIndex] : "confirmation",
      data: { ...state.data, ...stepData },
    });
  };

  const handleBack = () => {
    const steps: FlowStep[] = [
      "name",
      "type",
      "recipient",
      "amount",
      "token",
      "chain",
      "recurring",
      "frequency",
      "confirmation",
    ];

    const currentIndex = steps.indexOf(state.step);
    if (currentIndex > 0) {
      setState({
        ...state,
        step: steps[currentIndex - 1],
      });
    }
  };

  const handleComplete = async () => {
    try {
      const action = await paymentService.createPaymentAction(walletAddress, {
        walletAddress,
        name: state.data.name!,
        actionType: state.data.actionType!,
        recipientAddress: state.data.recipientAddress!,
        amount: state.data.amount!,
        token: state.data.token!,
        chainId: state.data.chainId!,
        schedule: state.data.schedule,
        triggers: state.data.triggers,
        isEnabled: true,
        isPinned: false,
        order: 0,
      });

      toast({
        title: "Success",
        description: `Payment action "${action.name}" created!`,
        status: "success",
        duration: 3000,
      });

      onActionCreated(action);
      onFlowComplete();
    } catch (error) {
      toast({
        title: "Error",
        description: `Failed to create payment action: ${error}`,
        status: "error",
        duration: 5000,
      });
    }
  };

  return (
    <Box
      bg="gray.50"
      borderRadius="lg"
      p={4}
      mb={4}
      border="1px solid"
      borderColor="blue.200"
    >
      <VStack spacing={4} align="stretch">
        {/* Step: Name */}
        {state.step === "name" && (
          <>
            <Text fontSize="sm" color="gray.600">
              Step 1/7: What should we call this action?
            </Text>
            <Input
              placeholder="e.g., Weekly Rent, Coffee Fund, Bill Payment"
              onChange={(e) => {
                handleNext({ name: e.target.value });
              }}
              autoFocus
            />
            <HStack>
              <Button size="sm" onClick={onFlowComplete}>Cancel</Button>
            </HStack>
          </>
        )}

        {/* Step: Type */}
        {state.step === "type" && (
          <>
            <Text fontSize="sm" color="gray.600">
              Step 2/7: What type of action is this?
            </Text>
            <VStack spacing={2}>
              {["send", "template", "recurring", "shortcut"].map((type) => (
                <Button
                  key={type}
                  variant={
                    state.data.actionType === type ? "solid" : "outline"
                  }
                  onClick={() => handleNext({ actionType: type })}
                  width="full"
                  justifyContent="flex-start"
                >
                  {type.charAt(0).toUpperCase() + type.slice(1)}
                </Button>
              ))}
            </VStack>
            <HStack>
              <Button size="sm" onClick={handleBack}>Back</Button>
            </HStack>
          </>
        )}

        {/* Step: Recipient */}
        {state.step === "recipient" && (
          <>
            <Text fontSize="sm" color="gray.600">
              Step 3/7: Who should receive the payment?
            </Text>
            <Input
              placeholder="0x... wallet address"
              fontFamily="mono"
              onChange={(e) => {
                handleNext({ recipientAddress: e.target.value });
              }}
              autoFocus
            />
            <HStack>
              <Button size="sm" onClick={handleBack}>Back</Button>
            </HStack>
          </>
        )}

        {/* Step: Amount */}
        {state.step === "amount" && (
          <>
            <Text fontSize="sm" color="gray.600">
              Step 4/7: How much should be sent?
            </Text>
            <NumberInput
              onChange={(value) => handleNext({ amount: value })}
              precision={6}
              step={0.1}
            >
              <NumberInputField placeholder="0.00" autoFocus />
              <NumberInputStepper>
                <NumberIncrementStepper />
                <NumberDecrementStepper />
              </NumberInputStepper>
            </NumberInput>
            <HStack>
              <Button size="sm" onClick={handleBack}>Back</Button>
            </HStack>
          </>
        )}

        {/* Step: Token */}
        {state.step === "token" && (
          <>
            <Text fontSize="sm" color="gray.600">
              Step 5/7: Which token?
            </Text>
            <Select
              onChange={(e) => handleNext({ token: e.target.value })}
            >
              <option value="">Select a token...</option>
              {["ETH", "USDC", "USDT", "DAI", "MNEE"].map((token) => (
                <option key={token} value={token}>
                  {token}
                </option>
              ))}
            </Select>
            <HStack>
              <Button size="sm" onClick={handleBack}>Back</Button>
            </HStack>
          </>
        )}

        {/* Step: Chain */}
        {state.step === "chain" && (
          <>
            <Text fontSize="sm" color="gray.600">
              Step 6/7: Which blockchain?
            </Text>
            <Select
              onChange={(e) => handleNext({ chainId: parseInt(e.target.value) })}
            >
              <option value="">Select a chain...</option>
              {Object.entries(SUPPORTED_CHAINS).map(([id, name]) => (
                <option key={id} value={id}>
                  {name}
                </option>
              ))}
            </Select>
            <HStack>
              <Button size="sm" onClick={handleBack}>Back</Button>
            </HStack>
          </>
        )}

        {/* Step: Recurring */}
        {state.step === "recurring" && (
          <>
            <Text fontSize="sm" color="gray.600">
              Step 7/7: Should this repeat automatically?
            </Text>
            <Checkbox
              onChange={(e) => {
                if (e.target.checked) {
                  handleNext({ schedule: { frequency: "monthly" } });
                } else {
                  handleNext({ schedule: undefined });
                  setState({
                    ...state,
                    step: "confirmation",
                  });
                }
              }}
            >
              Make this recurring
            </Checkbox>
            {state.data.schedule && (
              <Select
                value={state.data.schedule.frequency}
                onChange={(e) =>
                  handleNext({
                    schedule: {
                      ...state.data.schedule,
                      frequency: e.target.value as any,
                    },
                  })
                }
              >
                <option value="daily">Daily</option>
                <option value="weekly">Weekly</option>
                <option value="monthly">Monthly</option>
              </Select>
            )}
            <HStack>
              <Button size="sm" onClick={handleBack}>Back</Button>
            </HStack>
          </>
        )}

        {/* Step: Confirmation */}
        {state.step === "confirmation" && (
          <>
            <Text fontSize="sm" fontWeight="bold">
              Review your payment action:
            </Text>
            <Box bg="white" p={3} borderRadius="md">
              <VStack spacing={2} align="flex-start">
                <Text>
                  <strong>Name:</strong> {state.data.name}
                </Text>
                <Text>
                  <strong>Type:</strong> {state.data.actionType}
                </Text>
                <Text>
                  <strong>Amount:</strong> {state.data.amount} {state.data.token}
                </Text>
                <Text>
                  <strong>To:</strong> {state.data.recipientAddress?.slice(0, 10)}...
                </Text>
                {state.data.schedule && (
                  <Text>
                    <strong>Repeats:</strong> {state.data.schedule.frequency}
                  </Text>
                )}
              </VStack>
            </Box>
            <HStack justify="space-between">
              <Button size="sm" onClick={handleBack}>Back</Button>
              <Button
                colorScheme="blue"
                onClick={handleComplete}
              >
                Create Action
              </Button>
            </HStack>
          </>
        )}
      </VStack>
    </Box>
  );
};

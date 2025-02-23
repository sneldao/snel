import * as React from "react";
import {
  Box,
  Textarea,
  Button,
  VStack,
  HStack,
  Avatar,
  Text,
  useToast,
  Popover,
  PopoverTrigger,
  PopoverContent,
  PopoverBody,
  PopoverArrow,
  IconButton,
  List,
  ListItem,
  ListIcon,
  Badge,
} from "@chakra-ui/react";
import { InfoIcon, ChatIcon } from "@chakra-ui/icons";
import { useAccount, useChainId } from "wagmi";

type CommandInputProps = {
  onSubmit: (command: string) => Promise<void>;
  isLoading: boolean;
  isDisabled?: boolean;
};

const SUPPORTED_CHAINS = {
  1: "Ethereum",
  8453: "Base",
  42161: "Arbitrum",
  10: "Optimism",
  137: "Polygon",
  43114: "Avalanche",
  534352: "Scroll",
} as const;

const EXAMPLE_COMMANDS = [
  "swap 1 usdc for eth",
  "send 5 ETH to @vitalik",
  "what is the price of ETH?",
  "how much UNI can I get for 1 ETH?",
];

export const CommandInput = ({
  onSubmit,
  isLoading,
  isDisabled,
}: CommandInputProps) => {
  const [command, setCommand] = React.useState("");
  const toast = useToast();
  const chainId = useChainId();
  const { isConnected } = useAccount();

  const isChainSupported = chainId && chainId in SUPPORTED_CHAINS;
  const currentChainName = chainId
    ? SUPPORTED_CHAINS[chainId as keyof typeof SUPPORTED_CHAINS]
    : undefined;

  const handleSubmit = async () => {
    if (!command.trim()) {
      toast({
        title: "Error",
        description: "Please enter a command",
        status: "error",
        duration: 3000,
        isClosable: true,
      });
      return;
    }

    // Check if it's a swap command and validate chain
    if (command.toLowerCase().includes("swap")) {
      if (!isConnected) {
        toast({
          title: "Wallet not connected",
          description: "Please connect your wallet to execute swaps",
          status: "warning",
          duration: 5000,
        });
        return;
      }

      if (!isChainSupported) {
        toast({
          title: "Unsupported Network",
          description: `Please switch to a supported network: ${Object.values(
            SUPPORTED_CHAINS
          ).join(", ")}`,
          status: "warning",
          duration: 5000,
        });
        return;
      }
    }

    try {
      await onSubmit(command);
      setCommand("");
    } catch (error) {
      console.error("Error submitting command:", error);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const handleExampleClick = (example: string) => {
    setCommand(example);
  };

  return (
    <Box
      borderWidth="1px"
      borderRadius="lg"
      p={4}
      bg="white"
      opacity={isDisabled ? 0.6 : 1}
    >
      <VStack spacing={4} align="stretch">
        <HStack>
          <Text fontSize="lg" fontWeight="bold">
            Ask Pointless
          </Text>
          {chainId && (
            <Badge
              colorScheme={isChainSupported ? "green" : "red"}
              variant="subtle"
              fontSize="sm"
            >
              {isChainSupported ? currentChainName : "Unsupported Network"}
            </Badge>
          )}
          <Popover placement="top">
            <PopoverTrigger>
              <IconButton
                aria-label="Help"
                icon={<InfoIcon />}
                size="sm"
                variant="ghost"
              />
            </PopoverTrigger>
            <PopoverContent>
              <PopoverArrow />
              <PopoverBody>
                <VStack align="start" spacing={2}>
                  <Text fontWeight="bold">Example commands:</Text>
                  <List spacing={2}>
                    {EXAMPLE_COMMANDS.map((example, index) => (
                      <ListItem
                        key={index}
                        cursor={isDisabled ? "not-allowed" : "pointer"}
                        onClick={() =>
                          !isDisabled && handleExampleClick(example)
                        }
                        _hover={{ color: isDisabled ? undefined : "blue.500" }}
                      >
                        <ListIcon as={ChatIcon} color="green.500" />
                        {example}
                      </ListItem>
                    ))}
                  </List>
                </VStack>
              </PopoverBody>
            </PopoverContent>
          </Popover>
        </HStack>

        <HStack align="start" spacing={3}>
          <Avatar size="sm" name="User" bg="gray.500" />
          <VStack align="stretch" flex={1} spacing={3}>
            <Textarea
              value={command}
              onChange={(e) => setCommand(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder={
                isDisabled
                  ? "Please set your OpenAI API key to start"
                  : `Type a command or question (e.g., 'swap 1 usdc for eth')${
                      currentChainName ? ` on ${currentChainName} network` : ""
                    }`
              }
              resize="none"
              minH="60px"
              maxLength={280}
              bg="white"
              isDisabled={isLoading || isDisabled}
            />
            <HStack justify="space-between">
              <Text fontSize="sm" color="gray.500">
                {command.length}/280 • Press Enter to send
              </Text>
              <Button
                colorScheme="twitter"
                isLoading={isLoading}
                onClick={handleSubmit}
                leftIcon={<ChatIcon />}
                px={6}
                isDisabled={!command.trim() || isDisabled}
              >
                Send
              </Button>
            </HStack>
          </VStack>
        </HStack>
      </VStack>
    </Box>
  );
};

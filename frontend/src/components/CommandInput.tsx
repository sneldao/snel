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
  Link,
  Tooltip,
} from "@chakra-ui/react";
import { InfoIcon, ChatIcon } from "@chakra-ui/icons";
import { useAccount, useChainId } from "wagmi";
import NextLink from "next/link";
import { useUserProfile } from "../hooks/useUserProfile";

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
  56: "BSC",
  59144: "Linea",
  5000: "Mantle",
  81457: "Blast",
  34443: "Mode",
  324: "zkSync Era",
  100: "Gnosis",
  167004: "Taiko",
} as const;

const EXAMPLE_COMMANDS = [
  "swap 1 usdc for eth",
  "send 5 ETH to @papajams",
  "bridge 0.1 ETH from Scroll to Base",
  "analyze my portfolio",
  "tell me about Aave",
  "what's my USDC balance?",
  "show me my risk assessment",
  "research Compound protocol",
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
  const { profile, getUserDisplayName } = useUserProfile();

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

    const isPortfolioQuery = /portfolio|allocation|holdings|assets/i.test(
      command.toLowerCase()
    );

    // Check if it's a portfolio analysis command
    if (isPortfolioQuery) {
      if (!isConnected) {
        toast({
          title: "Wallet not connected",
          description: "Please connect your wallet to analyze your portfolio",
          status: "warning",
          duration: 5000,
        });
        return;
      }
    }
    // Check if it's a swap command and validate chain
    else if (command.toLowerCase().includes("swap")) {
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
            Ask something pointless on
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
          {!isConnected && (
            <Badge colorScheme="yellow" variant="subtle" fontSize="sm">
              Wallet Not Connected
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
          <Tooltip label={getUserDisplayName()} placement="top" hasArrow>
            <Avatar
              size="sm"
              name={getUserDisplayName()}
              src={profile?.avatar || undefined}
              bg="blue.500"
            />
          </Tooltip>
          <VStack align="stretch" flex={1} spacing={3}>
            <Textarea
              value={command}
              onChange={(e) => setCommand(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder={
                isDisabled
                  ? "Please set your OpenAI API key to start"
                  : !isConnected
                  ? "Please connect your wallet to start"
                  : !isChainSupported
                  ? "Please switch to a supported network"
                  : `Type a command or question (e.g., 'swap 1 usdc for eth') on ${currentChainName}`
              }
              isDisabled={isDisabled || !isConnected || !isChainSupported}
              size="sm"
              rows={1}
              resize="none"
              _focus={{
                borderColor: "blue.500",
                boxShadow: "0 0 0 1px var(--chakra-colors-blue-500)",
              }}
            />
            <Button
              onClick={handleSubmit}
              isLoading={isLoading}
              isDisabled={
                isDisabled ||
                !isConnected ||
                !isChainSupported ||
                !command.trim()
              }
              colorScheme="blue"
              size="sm"
              width="full"
            >
              Send
            </Button>
          </VStack>
        </HStack>
      </VStack>
    </Box>
  );
};

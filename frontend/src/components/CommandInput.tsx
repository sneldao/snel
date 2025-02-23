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
} from "@chakra-ui/react";
import { InfoIcon, ChatIcon } from "@chakra-ui/icons";

type CommandInputProps = {
  onSubmit: (command: string) => Promise<void>;
  isLoading: boolean;
};

const EXAMPLE_COMMANDS = [
  "swap $300 for $UNI",
  "send 5 ETH to @vitalik",
  "what is the price of ETH?",
  "how much UNI can I get for 1 ETH?",
];

export const CommandInput = ({ onSubmit, isLoading }: CommandInputProps) => {
  const [command, setCommand] = React.useState("");
  const toast = useToast();

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
    <Box borderWidth="1px" borderRadius="lg" p={4} bg="white">
      <VStack spacing={4} align="stretch">
        <HStack>
          <Text fontSize="lg" fontWeight="bold">
            Ask Pointless
          </Text>
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
                        cursor="pointer"
                        onClick={() => handleExampleClick(example)}
                        _hover={{ color: "blue.500" }}
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
              placeholder="Type a command or question (e.g., 'swap $300 for $UNI')"
              resize="none"
              minH="60px"
              maxLength={280}
              bg="white"
              isDisabled={isLoading}
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
                isDisabled={!command.trim()}
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

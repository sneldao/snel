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
  VStack,
  Text,
  useToast,
  Link as ChakraLink,
  Alert,
  AlertIcon,
  Box,
} from "@chakra-ui/react";
import NextLink from "next/link";

type ApiKeyModalProps = {
  isOpen: boolean;
  onClose: () => void;
};

export const ApiKeyModal = ({ isOpen, onClose }: ApiKeyModalProps) => {
  const [openaiKey, setOpenaiKey] = React.useState(() => {
    if (typeof window === "undefined") return "";
    return localStorage.getItem("openai_api_key") || "";
  });
  const toast = useToast();

  const handleSave = () => {
    // Save to localStorage
    localStorage.setItem("openai_api_key", openaiKey);

    toast({
      title: "API Key Saved",
      description: "Your OpenAI API key has been saved successfully.",
      status: "success",
      duration: 3000,
    });

    onClose();
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} size="xl">
      <ModalOverlay />
      <ModalContent>
        <ModalHeader>OpenAI API Key Configuration</ModalHeader>
        <ModalCloseButton />
        <ModalBody>
          <VStack spacing={4} align="stretch">
            <Alert status="info">
              <AlertIcon />
              An OpenAI API key is required to use this application. Your key is
              stored locally in your browser and is never sent to our servers.
            </Alert>

            <FormControl isRequired>
              <FormLabel>OpenAI API Key</FormLabel>
              <Input
                type="password"
                value={openaiKey}
                onChange={(e) => setOpenaiKey(e.target.value)}
                placeholder="sk-..."
              />
              <Text fontSize="sm" color="gray.500" mt={1}>
                Get your key from{" "}
                <ChakraLink
                  href="https://platform.openai.com/api-keys"
                  isExternal
                  color="blue.500"
                >
                  OpenAI Dashboard
                </ChakraLink>
              </Text>
            </FormControl>

            <Text fontSize="sm" color="gray.600" mt={4}>
              Your API key is stored securely in your browser&apos;s local
              storage. You can update or remove it at any time.
            </Text>

            <Box mt={4} pt={4} borderTop="1px" borderColor="gray.200">
              <Text fontSize="sm" color="gray.600">
                By using this service, you agree to our{" "}
                <ChakraLink
                  as={NextLink}
                  href="/terms"
                  color="blue.500"
                  onClick={onClose}
                >
                  terms & conditions
                </ChakraLink>
                .
              </Text>
            </Box>
          </VStack>
        </ModalBody>

        <ModalFooter>
          <Button variant="ghost" mr={3} onClick={onClose}>
            Cancel
          </Button>
          <Button
            colorScheme="blue"
            onClick={handleSave}
            isDisabled={!openaiKey}
          >
            Save Key
          </Button>
        </ModalFooter>
      </ModalContent>
    </Modal>
  );
};

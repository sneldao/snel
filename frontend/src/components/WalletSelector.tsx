"use client";
import React from "react";
import { useAccount as useEvmAccount } from "wagmi";
import { 
  useAccount as useStarknetAccount, 
  useConnect, 
  useDisconnect 
} from "@starknet-react/core";
import { ConnectKitButton } from "connectkit";
import {
  Box,
  Button,
  HStack,
  Text,
  Menu,
  MenuButton,
  MenuList,
  MenuItem,
  useDisclosure,
  Modal,
  ModalOverlay,
  ModalContent,
  ModalHeader,
  ModalBody,
  ModalCloseButton,
  VStack,
  Icon,
} from "@chakra-ui/react";
import { FaChevronDown, FaWallet } from "react-icons/fa";
import { SiStarknet } from "react-icons/si";

export function WalletSelector() {
  const { isConnected: isEvmConnected } = useEvmAccount();
  const { address: starknetAddress, isConnected: isStarknetConnected } = useStarknetAccount();
  const { connect, connectors } = useConnect();
  const { disconnect } = useDisconnect();
  const { isOpen, onOpen, onClose } = useDisclosure();

  return (
    <HStack spacing={2}>
      {/* EVM Wallet */}
      <ConnectKitButton />

      {/* Starknet Wallet */}
      {isStarknetConnected ? (
        <Menu>
          <MenuButton as={Button} size="sm" variant="outline" rightIcon={<FaChevronDown />}>
            <HStack spacing={2}>
              <Icon as={SiStarknet} color="orange.400" />
              <Text fontSize="xs" fontWeight="medium">
                {starknetAddress ? `${starknetAddress.slice(0, 6)}...${starknetAddress.slice(-4)}` : "Starknet"}
              </Text>
            </HStack>
          </MenuButton>
          <MenuList>
            <Box px={3} py={2}>
              <Text fontSize="xs" color="gray.500">Connected to Starknet</Text>
              <Text fontSize="xs" fontWeight="bold" noOfLines={1}>{starknetAddress}</Text>
            </Box>
            <MenuItem onClick={() => disconnect()} color="red.500">
              Disconnect Starknet
            </MenuItem>
          </MenuList>
        </Menu>
      ) : (
        <Button 
          size="sm" 
          colorScheme="orange" 
          variant="outline"
          onClick={onOpen} 
          leftIcon={<Icon as={SiStarknet} />}
        >
          Connect Starknet
        </Button>
      )}

      <Modal isOpen={isOpen} onClose={onClose} size="xs" isCentered>
        <ModalOverlay />
        <ModalContent>
          <ModalHeader fontSize="md">Connect Starknet Wallet</ModalHeader>
          <ModalCloseButton />
          <ModalBody pb={6}>
            <VStack spacing={3}>
              {connectors.map((connector) => (
                <Button
                  key={connector.id}
                  w="full"
                  variant="outline"
                  onClick={() => {
                    connect({ connector });
                    onClose();
                  }}
                  isDisabled={!connector.available()}
                  justifyContent="space-between"
                  rightIcon={!connector.available() ? <Text fontSize="2xs" color="gray.500">Not Installed</Text> : undefined}
                >
                  <HStack>
                    <Icon as={FaWallet} />
                    <Text>{connector.name}</Text>
                  </HStack>
                </Button>
              ))}
              {connectors.length === 0 && (
                <Text fontSize="xs" color="gray.500" textAlign="center">
                  No Starknet connectors found. Please install Argent X or Braavos.
                </Text>
              )}
            </VStack>
          </ModalBody>
        </ModalContent>
      </Modal>
    </HStack>
  );
}

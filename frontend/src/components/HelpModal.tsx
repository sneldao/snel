import React from "react";
import {
  Modal,
  ModalOverlay,
  ModalContent,
  ModalHeader,
  ModalFooter,
  ModalBody,
  ModalCloseButton,
  Button,
  Text,
  VStack,
  Box,
  Heading,
  Divider,
  useColorModeValue,
  Flex,
  Icon,
  List,
  ListItem,
  ListIcon,
} from "@chakra-ui/react";
import {
  FaExchangeAlt,
  FaWallet,
  FaCoins,
  FaArrowRight,
  FaBalanceScale,
} from "react-icons/fa";
import { BsArrowLeftRight } from "react-icons/bs";
import Image from "next/image";

interface HelpModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const HelpModal: React.FC<HelpModalProps> = ({ isOpen, onClose }) => {
  const bgColor = useColorModeValue("white", "gray.800");
  const borderColor = useColorModeValue("gray.200", "gray.700");
  const headingColor = useColorModeValue("gray.700", "white");
  const textColor = useColorModeValue("gray.600", "gray.300");

  const examples = [
    {
      category: "Token Transfers",
      icon: FaArrowRight,
      examples: [
        "send 10 USDC to 0x123...",
        "transfer 0.1 ETH to papajams.eth",
      ],
    },
    {
      category: "Cross-Chain Bridging",
      icon: BsArrowLeftRight,
      examples: [
        "bridge 0.1 ETH from Scroll to Base",
        "bridge 50 USDC from Ethereum to Arbitrum",
      ],
    },
    {
      category: "Balance Checking",
      icon: FaBalanceScale,
      examples: ["check my USDC balance on Scroll", "what's my ETH balance"],
    },
    {
      category: "Token Swaps",
      icon: FaExchangeAlt,
      examples: ["swap 1 ETH for USDC", "swap $100 worth of USDC for ETH"],
    },
    {
      category: "DCA Orders",
      icon: FaCoins,
      examples: [
        "dca $10 USDC into ETH over 5 days",
        "dollar cost average 100 USDC into ETH weekly for a month",
      ],
    },
  ];

  return (
    <Modal isOpen={isOpen} onClose={onClose} size="lg" isCentered>
      <ModalOverlay backdropFilter="blur(4px)" />
      <ModalContent
        borderRadius="xl"
        boxShadow="xl"
        bg={bgColor}
        border="1px solid"
        borderColor={borderColor}
        mx={4}
      >
        <ModalHeader
          display="flex"
          alignItems="center"
          justifyContent="center"
          pt={6}
        >
          <Flex align="center" justify="center" direction="column">
            <Box position="relative" width="60px" height="60px" mb={2}>
              <Image
                src="/icon.png"
                alt="SNEL Logo"
                width={60}
                height={60}
                priority
                style={{ objectFit: "contain" }}
              />
            </Box>
            <Heading size="lg" color={headingColor}>
              What can SNEL do?
            </Heading>
            <Text fontSize="sm" color={textColor} mt={1}>
              Super poiNtlEss Lazy agents at your service
            </Text>
          </Flex>
        </ModalHeader>
        <ModalCloseButton />

        <ModalBody pb={6}>
          <VStack spacing={5} align="stretch">
            {examples.map((category, idx) => (
              <Box key={idx}>
                <Flex align="center" mb={2}>
                  <Icon
                    as={category.icon}
                    mr={2}
                    color="blue.500"
                    boxSize={5}
                  />
                  <Heading size="sm" color={headingColor}>
                    {category.category}
                  </Heading>
                </Flex>
                <List spacing={2} pl={8}>
                  {category.examples.map((example, exIdx) => (
                    <ListItem key={exIdx} color={textColor} fontSize="sm">
                      <Text as="span" fontFamily="mono" fontWeight="medium">
                        "{example}"
                      </Text>
                    </ListItem>
                  ))}
                </List>
                {idx < examples.length - 1 && <Divider mt={4} />}
              </Box>
            ))}
          </VStack>
        </ModalBody>

        <ModalFooter justifyContent="center">
          <Button colorScheme="blue" onClick={onClose} size="md" width="150px">
            Got it!
          </Button>
        </ModalFooter>
      </ModalContent>
    </Modal>
  );
};

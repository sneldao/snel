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
  SimpleGrid,
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
      examples: ["** coming soon **", "** coming soon **"],
    },
  ];

  return (
    <Modal isOpen={isOpen} onClose={onClose} size="md" isCentered>
      <ModalOverlay backdropFilter="blur(4px)" />
      <ModalContent
        borderRadius="xl"
        boxShadow="xl"
        bg={bgColor}
        border="1px solid"
        borderColor={borderColor}
        mx={4}
        maxW="450px"
      >
        <ModalHeader
          display="flex"
          alignItems="center"
          justifyContent="center"
          pt={4}
          pb={2}
        >
          <Flex align="center" justify="center" direction="row" gap={3}>
            <Box position="relative" width="40px" height="40px">
              <Image
                src="/icon.png"
                alt="SNEL Logo"
                width={40}
                height={40}
                priority
                style={{ objectFit: "contain" }}
              />
            </Box>
            <Heading size="md" color={headingColor}>
              What can SNEL do?
            </Heading>
          </Flex>
        </ModalHeader>
        <ModalCloseButton />

        <ModalBody pb={4} px={4}>
          <SimpleGrid columns={1} spacing={3} alignItems="stretch">
            {examples.map((category, idx) => (
              <Box
                key={idx}
                p={2}
                borderRadius="md"
                bg={useColorModeValue("gray.50", "gray.700")}
              >
                <Flex align="center" mb={1}>
                  <Icon
                    as={category.icon}
                    mr={2}
                    color="blue.500"
                    boxSize={4}
                  />
                  <Heading size="xs" color={headingColor}>
                    {category.category}
                  </Heading>
                </Flex>
                <List spacing={1} pl={6} fontSize="xs">
                  {category.examples.map((example, exIdx) => (
                    <ListItem key={exIdx} color={textColor}>
                      <Text as="span" fontFamily="mono" fontWeight="medium">
                        "{example}"
                      </Text>
                    </ListItem>
                  ))}
                </List>
              </Box>
            ))}
          </SimpleGrid>
        </ModalBody>

        <ModalFooter justifyContent="center" pt={2} pb={3}>
          <Button colorScheme="blue" onClick={onClose} size="sm" width="120px">
            Got it!
          </Button>
        </ModalFooter>
      </ModalContent>
    </Modal>
  );
};

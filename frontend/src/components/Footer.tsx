import {
  Box,
  Link as ChakraLink,
  Text,
  HStack,
  Divider,
  Icon,
  Tooltip,
  useColorModeValue,
} from "@chakra-ui/react";
import NextLink from "next/link";
import { FaTelegram } from "react-icons/fa";

export const Footer = () => {
  const footerLinkColor = useColorModeValue("blue.500", "blue.400");
  const footerLinkHoverColor = useColorModeValue("blue.600", "blue.300");

  return (
    <Box
      as="footer"
      position="fixed"
      bottom="0"
      width="100%"
      py={2}
      px={4}
      bg="white"
      borderTop="1px"
      borderColor="gray.100"
      textAlign="center"
      fontSize={{ base: "xs", sm: "sm" }}
      color="gray.600"
      backdropFilter="blur(10px)"
      backgroundColor="rgba(255, 255, 255, 0.9)"
      zIndex="banner"
      _dark={{
        bg: "gray.900",
        borderColor: "gray.700",
        color: "gray.400",
        backgroundColor: "rgba(26, 32, 44, 0.9)"
      }}
    >
      <HStack spacing={4} justify="center" wrap="wrap">
        <ChakraLink
          href="https://hey.xyz/u/papajams"
          isExternal
          color={footerLinkColor}
          _hover={{ textDecoration: "none", color: footerLinkHoverColor }}
        >
          papa
        </ChakraLink>

        <Tooltip label="Chat with SNEL on Telegram" placement="top">
          <ChakraLink
            href="https://t.me/stablesnelbot"
            isExternal
            color={footerLinkColor}
            _hover={{ textDecoration: "none", color: footerLinkHoverColor }}
            display="flex"
            alignItems="center"
          >
            <Icon as={FaTelegram} boxSize={4} />
            <Text ml={1}>telegram</Text>
          </ChakraLink>
        </Tooltip>

        <ChakraLink
          as={NextLink}
          href="/terms"
          color={footerLinkColor}
          _hover={{ textDecoration: "none", color: footerLinkHoverColor }}
        >
          terms
        </ChakraLink>
      </HStack>
    </Box>
  );
};

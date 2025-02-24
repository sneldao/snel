import { Box, Link, Text } from "@chakra-ui/react";

export const Footer = () => {
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
    >
      <Text>
        <Link
          href="https://hey.xyz/u/papajams"
          isExternal
          color="blue.500"
          _hover={{ textDecoration: "none", color: "blue.600" }}
        >
          papa
        </Link>
        <Text as="span" mx={2} color="gray.400">
          |
        </Text>
        <Link
          href="https://hey.xyz/u/pointless"
          isExternal
          color="blue.500"
          _hover={{ textDecoration: "none", color: "blue.600" }}
        >
          pointless
        </Link>
      </Text>
    </Box>
  );
};

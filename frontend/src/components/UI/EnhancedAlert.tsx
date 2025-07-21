import React from "react";
import {
  Alert,
  AlertIcon,
  AlertTitle,
  AlertDescription,
  Box,
  CloseButton,
  useColorModeValue,
} from "@chakra-ui/react";

interface EnhancedAlertProps {
  status: "info" | "warning" | "success" | "error";
  title?: string;
  description?: string;
  isClosable?: boolean;
  onClose?: () => void;
  variant?: "subtle" | "left-accent" | "top-accent" | "solid";
  size?: "sm" | "md" | "lg";
}

export const EnhancedAlert: React.FC<EnhancedAlertProps> = ({
  status,
  title,
  description,
  isClosable = false,
  onClose,
  variant = "left-accent",
  size = "md",
}) => {
  const bgColor = useColorModeValue(
    status === "error" ? "red.50" : status === "success" ? "green.50" : "blue.50",
    status === "error" ? "red.900" : status === "success" ? "green.900" : "blue.900"
  );

  const getSize = () => {
    switch (size) {
      case "sm":
        return { fontSize: "sm", py: 2 };
      case "lg":
        return { fontSize: "md", py: 4 };
      default:
        return { fontSize: "sm", py: 3 };
    }
  };

  return (
    <Alert
      status={status}
      variant={variant}
      borderRadius="md"
      bg={bgColor}
      {...getSize()}
    >
      <AlertIcon />
      <Box flex="1">
        {title && (
          <AlertTitle fontSize={size === "lg" ? "md" : "sm"} mb={title && description ? 1 : 0}>
            {title}
          </AlertTitle>
        )}
        {description && (
          <AlertDescription fontSize={size === "lg" ? "sm" : "xs"}>
            {description}
          </AlertDescription>
        )}
      </Box>
      {isClosable && (
        <CloseButton
          alignSelf="flex-start"
          position="relative"
          right={-1}
          top={-1}
          onClick={onClose}
        />
      )}
    </Alert>
  );
};
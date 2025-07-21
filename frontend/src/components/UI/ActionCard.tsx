import React from "react";
import {
  Box,
  VStack,
  HStack,
  Text,
  Icon,
  Button,
  useColorModeValue,
  Divider,
  Badge,
} from "@chakra-ui/react";
import { IconType } from "react-icons";

interface ActionCardProps {
  title: string;
  description?: string;
  icon?: IconType;
  badge?: {
    text: string;
    colorScheme: string;
  };
  actions?: Array<{
    label: string;
    colorScheme?: string;
    variant?: string;
    onClick: () => void;
    isLoading?: boolean;
  }>;
  children?: React.ReactNode;
  isHighlighted?: boolean;
}

export const ActionCard: React.FC<ActionCardProps> = ({
  title,
  description,
  icon,
  badge,
  actions = [],
  children,
  isHighlighted = false,
}) => {
  const bgColor = useColorModeValue(
    isHighlighted ? "blue.50" : "white",
    isHighlighted ? "blue.900" : "gray.800"
  );
  const borderColor = useColorModeValue(
    isHighlighted ? "blue.200" : "gray.200",
    isHighlighted ? "blue.600" : "gray.600"
  );

  return (
    <Box
      p={5}
      bg={bgColor}
      borderWidth="1px"
      borderColor={borderColor}
      borderRadius="lg"
      shadow={isHighlighted ? "md" : "sm"}
      _hover={{ shadow: "md" }}
      transition="all 0.2s"
    >
      <VStack spacing={4} align="stretch">
        {/* Header */}
        <HStack justify="space-between" align="flex-start">
          <HStack spacing={3}>
            {icon && (
              <Icon
                as={icon}
                boxSize={5}
                color={isHighlighted ? "blue.500" : "gray.500"}
              />
            )}
            <VStack align="flex-start" spacing={1}>
              <Text fontSize="md" fontWeight="semibold">
                {title}
              </Text>
              {description && (
                <Text fontSize="sm" color="gray.600" lineHeight="short">
                  {description}
                </Text>
              )}
            </VStack>
          </HStack>
          {badge && (
            <Badge colorScheme={badge.colorScheme} size="sm">
              {badge.text}
            </Badge>
          )}
        </HStack>

        {/* Content */}
        {children && (
          <>
            <Divider />
            <Box>{children}</Box>
          </>
        )}

        {/* Actions */}
        {actions.length > 0 && (
          <>
            <Divider />
            <HStack spacing={2} justify="flex-end">
              {actions.map((action, index) => (
                <Button
                  key={index}
                  size="sm"
                  colorScheme={action.colorScheme || "blue"}
                  variant={action.variant || "solid"}
                  onClick={action.onClick}
                  isLoading={action.isLoading}
                >
                  {action.label}
                </Button>
              ))}
            </HStack>
          </>
        )}
      </VStack>
    </Box>
  );
};
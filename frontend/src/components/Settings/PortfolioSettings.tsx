import React, { useState } from "react";
import {
  VStack,
  HStack,
  Switch,
  Text,
  Box,
  Alert,
  AlertIcon,
  AlertTitle,
  AlertDescription,
  Badge,
  Button,
  useColorModeValue,
} from "@chakra-ui/react";
import { FaChartPie, FaClock } from "react-icons/fa";

interface PortfolioSettingsProps {
  isEnabled: boolean;
  onToggle: (enabled: boolean) => void;
  isAnalyzing?: boolean;
  lastAnalysisTime?: string;
  canUseCache?: boolean;
  onClearCache?: () => void;
}

export const PortfolioSettings: React.FC<PortfolioSettingsProps> = ({
  isEnabled,
  onToggle,
  isAnalyzing = false,
  lastAnalysisTime,
  canUseCache = false,
  onClearCache,
}) => {
  const bgColor = useColorModeValue("gray.50", "gray.800");
  const borderColor = useColorModeValue("gray.200", "gray.600");

  return (
    <Box
      p={4}
      bg={bgColor}
      borderRadius="lg"
      border="1px solid"
      borderColor={borderColor}
    >
      <VStack spacing={4} align="stretch">
        {/* Main Toggle */}
        <HStack justify="space-between">
          <VStack align="flex-start" spacing={1}>
            <HStack>
              <FaChartPie />
              <Text fontWeight="medium">Portfolio Analysis</Text>
              <Badge colorScheme="orange" size="sm">
                Beta
              </Badge>
            </HStack>
            <Text fontSize="xs" color="gray.500">
              Deep portfolio insights and recommendations
            </Text>
          </VStack>
          <Switch
            isChecked={isEnabled}
            onChange={(e) => onToggle(e.target.checked)}
            colorScheme="blue"
          />
        </HStack>

        {/* Performance Warning */}
        {isEnabled && (
          <Alert status="info" size="sm" borderRadius="md">
            <AlertIcon />
            <Box>
              <AlertTitle fontSize="xs">Performance Note</AlertTitle>
              <AlertDescription fontSize="xs">
                Portfolio analysis takes 10-30 seconds. You can continue using other features while it runs in the background.
              </AlertDescription>
            </Box>
          </Alert>
        )}

        {/* Cache Status */}
        {isEnabled && (canUseCache || lastAnalysisTime) && (
          <HStack justify="space-between" fontSize="xs" color="gray.500">
            <HStack>
              <FaClock />
              <Text>
                {lastAnalysisTime 
                  ? `Last analysis: ${lastAnalysisTime}` 
                  : "No previous analysis"}
              </Text>
            </HStack>
            {canUseCache && onClearCache && (
              <Button size="xs" variant="ghost" onClick={onClearCache}>
                Clear Cache
              </Button>
            )}
          </HStack>
        )}
      </VStack>
    </Box>
  );
};
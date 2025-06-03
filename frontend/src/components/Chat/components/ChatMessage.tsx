import React from "react";
import {
  Box,
  VStack,
  HStack,
  Text,
  Progress,
  Badge,
  Icon,
  Button,
  Collapse,
  useDisclosure,
} from "@chakra-ui/react";
import {
  FaUser,
  FaRobot,
  FaInfoCircle,
  FaChevronDown,
  FaChevronUp,
  FaExclamationTriangle,
  FaChevronRight,
} from "react-icons/fa";
import { ChatMessageProps } from "../../../types/chat";
import { PortfolioAction } from "../../../services/portfolioService";

export const ChatMessage: React.FC<ChatMessageProps> = ({
  type,
  content,
  timestamp,
  metadata,
  style,
}) => {
  const { isOpen, onToggle } = useDisclosure();

  const getMessageIcon = () => {
    switch (type) {
      case "user":
        return FaUser;
      case "assistant":
        return FaRobot;
      case "system":
        return FaInfoCircle;
      case "progress":
        return metadata?.messageType === "error"
          ? FaExclamationTriangle
          : FaInfoCircle;
      default:
        return FaInfoCircle;
    }
  };

  const getMessageColor = () => {
    switch (type) {
      case "user":
        return "blue";
      case "assistant":
        return "green";
      case "system":
        return "purple";
      case "progress":
        return metadata?.messageType === "error" ? "red" : "blue";
      default:
        return "gray";
    }
  };

  const renderProgressBar = () => {
    if (type === "progress" && metadata?.progress !== undefined) {
      return (
        <Progress
          value={metadata.progress}
          size="sm"
          colorScheme={getMessageColor()}
          borderRadius="full"
          bg="whiteAlpha.100"
          mt={2}
        />
      );
    }
    return null;
  };

  const renderMetadata = () => {
    if (!metadata) return null;

    return (
      <Collapse in={isOpen}>
        <VStack align="start" spacing={2} mt={4}>
          {metadata.reasoning && (
            <Box>
              <Text fontSize="sm" fontWeight="medium" mb={1}>
                Reasoning:
              </Text>
              <VStack align="start" spacing={1}>
                {metadata.reasoning.map((step: string, idx: number) => (
                  <Text key={idx} fontSize="sm" color="gray.400">
                    {step}
                  </Text>
                ))}
              </VStack>
            </Box>
          )}

          {metadata.suggestedActions && (
            <Box>
              <Text fontSize="sm" fontWeight="medium" mb={1}>
                Suggested Actions:
              </Text>
              <VStack align="start" spacing={2}>
                {metadata.suggestedActions.map(
                  (action: PortfolioAction, idx: number) => (
                    <Box
                      key={idx}
                      p={2}
                      borderRadius="md"
                      borderWidth="1px"
                      borderColor="whiteAlpha.200"
                      w="100%"
                    >
                      <HStack justify="space-between" mb={1}>
                        <Text fontSize="sm">{action.type}</Text>
                        <Badge colorScheme="blue">{action.type}</Badge>
                      </HStack>
                      <Text fontSize="xs" color="gray.400">
                        {action.description}
                      </Text>
                      {action.impact && (
                        <VStack align="start" spacing={1} mt={2}>
                          <Text fontSize="xs" color="gray.400">
                            Impact:
                          </Text>
                          {action.impact.risk && (
                            <Text fontSize="xs" color="gray.400">
                              Risk: {action.impact.risk}
                            </Text>
                          )}
                          {action.impact.yield && (
                            <Text fontSize="xs" color="gray.400">
                              Yield: {action.impact.yield}
                            </Text>
                          )}
                          {action.impact.gas && (
                            <Text fontSize="xs" color="gray.400">
                              Gas: {action.impact.gas}
                            </Text>
                          )}
                        </VStack>
                      )}
                    </Box>
                  )
                )}
              </VStack>
            </Box>
          )}
        </VStack>
      </Collapse>
    );
  };

  return (
    <Box
      p={4}
      borderRadius="lg"
      borderWidth="1px"
      borderColor="whiteAlpha.200"
      bg={type === "user" ? "whiteAlpha.50" : "transparent"}
      style={style}
    >
      <VStack align="stretch" spacing={2}>
        <HStack justify="space-between">
          <HStack>
            <Icon
              as={getMessageIcon()}
              color={`${getMessageColor()}.400`}
              boxSize={5}
            />
            <Text fontSize="sm" color="gray.400">
              {new Date(timestamp).toLocaleTimeString()}
            </Text>
          </HStack>
          {(metadata?.reasoning || metadata?.suggestedActions) && (
            <Button
              size="sm"
              variant="ghost"
              onClick={onToggle}
              rightIcon={<Icon as={isOpen ? FaChevronUp : FaChevronDown} />}
            >
              Details
            </Button>
          )}
        </HStack>

        <Text>{content}</Text>
        {renderProgressBar()}
        {renderMetadata()}
      </VStack>
    </Box>
  );
};

import React, { useState } from "react";
import {
  Box,
  VStack,
  HStack,
  Flex,
  Text,
  Button,
  Icon,
  Collapse,
  Badge,
  useColorModeValue,
  Tooltip,
} from "@chakra-ui/react";
import { ChevronDownIcon, ChevronUpIcon } from "@chakra-ui/icons";
import { FaRobot, FaUser, FaInfoCircle } from "react-icons/fa";
import { AgentProgress } from "../../services/agentService";
import { TerminalProgress } from "../shared/TerminalProgress";

interface ChatMessageProps {
  id: string;
  type: "user" | "assistant" | "system" | "progress";
  content: string;
  timestamp: Date;
  metadata?: {
    stage?: string;
    progress?: number;
    agent?: string;
    reasoning?: string[];
    confidence?: number;
    chainContext?: string[];
    suggestedActions?: Array<{
      type: string;
      confidence: number;
      impact: string;
      requirements: string[];
    }>;
  };
}

export const ChatMessage: React.FC<ChatMessageProps> = ({
  type,
  content,
  timestamp,
  metadata,
}) => {
  const [showDetails, setShowDetails] = useState(false);
  const bgColor = useColorModeValue("whiteAlpha.200", "whiteAlpha.100");
  const borderColor = useColorModeValue("whiteAlpha.300", "whiteAlpha.200");

  const renderAgentBadge = () => {
    if (!metadata?.agent) return null;
    return (
      <Tooltip
        label={`Confidence: ${metadata.confidence?.toFixed(2) || "N/A"}`}
      >
        <Badge colorScheme="blue" variant="subtle">
          {metadata.agent}
        </Badge>
      </Tooltip>
    );
  };

  const renderProgressIndicator = () => {
    if (type !== "progress" || !metadata?.progress) return null;
    return (
      <TerminalProgress
        steps={[
          {
            stage: metadata.stage || "",
            type: "progress",
            completion: metadata.progress,
            details: metadata.reasoning?.join("\n"),
          },
        ]}
        isComplete={metadata.progress === 100}
      />
    );
  };

  const renderSuggestedActions = () => {
    if (!metadata?.suggestedActions?.length) return null;
    return (
      <VStack align="stretch" mt={4} spacing={2}>
        <Text fontSize="sm" fontWeight="medium">
          Suggested Actions:
        </Text>
        {metadata.suggestedActions.map((action, idx) => (
          <HStack
            key={idx}
            p={2}
            bg="whiteAlpha.50"
            borderRadius="md"
            justify="space-between"
          >
            <Text fontSize="sm">{action.type}</Text>
            <Badge colorScheme={action.confidence > 0.7 ? "green" : "yellow"}>
              {(action.confidence * 100).toFixed(0)}% confident
            </Badge>
          </HStack>
        ))}
      </VStack>
    );
  };

  const renderChainContext = () => {
    if (!metadata?.chainContext?.length) return null;
    return (
      <HStack mt={2} spacing={2}>
        {metadata.chainContext.map((context, idx) => (
          <Badge key={idx} colorScheme="purple" variant="subtle">
            {context}
          </Badge>
        ))}
      </HStack>
    );
  };

  return (
    <Box
      w="100%"
      bg={type === "user" ? "transparent" : bgColor}
      p={{ base: 3, md: 4 }}
      borderRadius="xl"
      borderWidth={type === "user" ? 0 : "1px"}
      borderColor={borderColor}
      alignSelf={type === "user" ? "flex-end" : "flex-start"}
      maxW={{
        base: type === "user" ? "85%" : "100%",
        md: type === "user" ? "70%" : "95%",
      }}
    >
      <VStack align="stretch" spacing={3}>
        <Flex
          direction={{ base: "column", sm: "row" }}
          justify="space-between"
          align={{ base: "flex-start", sm: "center" }}
          gap={{ base: 1, sm: 0 }}
        >
          <HStack>
            <Icon
              as={type === "user" ? FaUser : FaRobot}
              color={type === "user" ? "blue.400" : "green.400"}
            />
            {renderAgentBadge()}
          </HStack>
          <Text fontSize="xs" color="whiteAlpha.600">
            {timestamp.toLocaleTimeString()}
          </Text>
        </Flex>

        <Text fontSize={{ base: "sm", md: "md" }} mt={2}>
          {content}
        </Text>
        {renderProgressIndicator()}
        <Box overflowX="auto" maxW="100%">
          {renderChainContext()}
        </Box>

        {(metadata?.reasoning?.length ||
          metadata?.suggestedActions?.length) && (
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setShowDetails(!showDetails)}
            rightIcon={showDetails ? <ChevronUpIcon /> : <ChevronDownIcon />}
            fontSize={{ base: "xs", md: "sm" }}
            px={{ base: 2, md: 3 }}
          >
            {showDetails ? "Hide Details" : "Show Details"}
          </Button>
        )}

        <Collapse in={showDetails}>
          <VStack align="stretch" spacing={3} pt={2}>
            {metadata?.reasoning?.length && (
              <Box>
                <Text fontSize="sm" fontWeight="medium" mb={2}>
                  Reasoning:
                </Text>
                <VStack align="stretch" spacing={1}>
                  {metadata.reasoning.map((reason, idx) => (
                    <Flex key={idx} align="flex-start" gap={2}>
                      <Icon
                        as={FaInfoCircle}
                        color="blue.400"
                        boxSize={3}
                        mt={1}
                        flexShrink={0}
                      />
                      <Text
                        fontSize={{ base: "xs", md: "sm" }}
                        wordBreak="break-word"
                      >
                        {reason}
                      </Text>
                    </Flex>
                  ))}
                </VStack>
              </Box>
            )}
            <Box overflowX="auto" maxW="100%">
              {renderSuggestedActions()}
            </Box>
          </VStack>
        </Collapse>
      </VStack>
    </Box>
  );
};

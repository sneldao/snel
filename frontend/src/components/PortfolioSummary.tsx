import React, { useState } from "react";
import {
  Box,
  VStack,
  Text,
  Button,
  Modal,
  ModalOverlay,
  ModalContent,
  ModalHeader,
  ModalBody,
  ModalCloseButton,
  useDisclosure,
  Card,
  CardBody,
} from "@chakra-ui/react";
import ReactMarkdown from "react-markdown";
import { AgnoResponse } from "../services/agnoService";

interface PortfolioSummaryProps {
  response: AgnoResponse;
}

export const PortfolioSummary: React.FC<PortfolioSummaryProps> = ({
  response,
}) => {
  const { isOpen, onOpen, onClose } = useDisclosure();

  // Ensure we have content to display
  if (!response.summary && !response.fullAnalysis && !response.content) {
    return null;
  }

  const summaryContent =
    response.summary || response.content || "Portfolio analysis completed.";
  const fullContent =
    response.fullAnalysis ||
    response.content ||
    "Full analysis data not available.";

  return (
    <VStack spacing={4} align="stretch" w="full">
      {/* Summary Card */}
      <Card>
        <CardBody>
          <VStack spacing={4} align="stretch">
            <div className="prose max-w-none">
              <ReactMarkdown>{summaryContent}</ReactMarkdown>
            </div>

            {/* Show "View Full Analysis" button if we have detailed analysis */}
            {response.fullAnalysis &&
              response.fullAnalysis !== summaryContent && (
                <Box textAlign="center">
                  <Button
                    colorScheme="blue"
                    variant="outline"
                    size="sm"
                    onClick={onOpen}
                  >
                    View Full Analysis
                  </Button>
                </Box>
              )}
          </VStack>
        </CardBody>
      </Card>

      {/* Full Analysis Modal */}
      <Modal
        isOpen={isOpen}
        onClose={onClose}
        size="6xl"
        scrollBehavior="inside"
      >
        <ModalOverlay />
        <ModalContent maxH="90vh">
          <ModalHeader>Complete Portfolio Analysis</ModalHeader>
          <ModalCloseButton />
          <ModalBody pb={6}>
            <div className="prose max-w-none">
              <ReactMarkdown>{fullContent}</ReactMarkdown>
            </div>
          </ModalBody>
        </ModalContent>
      </Modal>
    </VStack>
  );
};

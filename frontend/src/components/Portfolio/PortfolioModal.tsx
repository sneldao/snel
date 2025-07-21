import React from "react";
import {
  Modal,
  ModalOverlay,
  ModalContent,
  ModalHeader,
  ModalCloseButton,
  ModalBody,
  HStack,
  Icon,
  Text,
} from "@chakra-ui/react";
import { FaChartPie } from "react-icons/fa";
import { PortfolioSummary } from "../PortfolioSummary";

interface PortfolioModalProps {
  isOpen: boolean;
  onClose: () => void;
  portfolioAnalysis: any;
  metadata: any;
  onActionClick: (action: any) => void;
}

export const PortfolioModal: React.FC<PortfolioModalProps> = ({
  isOpen,
  onClose,
  portfolioAnalysis,
  metadata,
  onActionClick,
}) => {
  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      size="6xl"
      motionPreset="slideInBottom"
    >
      <ModalOverlay backdropFilter="blur(4px)" />
      <ModalContent borderRadius="xl" overflow="hidden" maxH="90vh">
        <ModalHeader bg="blue.600" color="white">
          <HStack>
            <Icon as={FaChartPie} />
            <Text>Portfolio Deep Dive Analysis</Text>
          </HStack>
        </ModalHeader>
        <ModalCloseButton color="white" />
        <ModalBody p={6} overflowY="auto">
          <PortfolioSummary
            response={{
              analysis: portfolioAnalysis,
              summary: portfolioAnalysis?.summary,
              fullAnalysis: portfolioAnalysis?.fullAnalysis,
              content: portfolioAnalysis?.summary,
              status: "success",
              metadata: metadata,
            }}
            onActionClick={onActionClick}
            isLoading={false}
          />
        </ModalBody>
      </ModalContent>
    </Modal>
  );
};
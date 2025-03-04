import { HStack, Text, Spinner, Icon } from "@chakra-ui/react";
import { CheckCircleIcon, WarningIcon } from "@chakra-ui/icons";

interface TransactionStatusProps {
  status: "pending" | "processing" | "success" | "error";
  pendingCommand?: string;
}

const TransactionStatus = ({
  status,
  pendingCommand,
}: TransactionStatusProps) => {
  const getStatusColor = () => {
    switch (status) {
      case "success":
        return "green.500";
      case "error":
        return "red.500";
      case "processing":
      case "pending":
        return "blue.500";
      default:
        return "gray.500";
    }
  };

  const getStatusIcon = () => {
    switch (status) {
      case "success":
        return <Icon as={CheckCircleIcon} color="green.500" />;
      case "error":
        return <Icon as={WarningIcon} color="red.500" />;
      case "processing":
      case "pending":
        return <Spinner size="sm" color="blue.500" />;
      default:
        return null;
    }
  };

  const getStatusText = () => {
    switch (status) {
      case "success":
        return "Transaction completed";
      case "error":
        return "Transaction failed";
      case "processing":
        return "Processing transaction...";
      case "pending":
        return pendingCommand ? "Awaiting confirmation..." : "Pending...";
      default:
        return "";
    }
  };

  return (
    <HStack spacing={2} opacity={0.8}>
      {getStatusIcon()}
      <Text fontSize="sm" color={getStatusColor()}>
        {getStatusText()}
      </Text>
    </HStack>
  );
};

export default TransactionStatus;

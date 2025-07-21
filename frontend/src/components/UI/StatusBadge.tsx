import React from "react";
import { Badge, Spinner, Icon } from "@chakra-ui/react";
import { FaCheckCircle, FaExclamationTriangle, FaClock } from "react-icons/fa";

interface StatusBadgeProps {
  status: "pending" | "processing" | "success" | "error";
  size?: "sm" | "md" | "lg";
  animated?: boolean;
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({ 
  status, 
  size = "md",
  animated = true 
}) => {
  const getStatusProps = () => {
    switch (status) {
      case "processing":
        return {
          colorScheme: "blue",
          children: (
            <>
              {animated && <Spinner size="xs" mr={2} />}
              Processing
            </>
          ),
        };
      case "success":
        return {
          colorScheme: "green",
          children: (
            <>
              <Icon as={FaCheckCircle} mr={1} />
              Success
            </>
          ),
        };
      case "error":
        return {
          colorScheme: "red",
          children: (
            <>
              <Icon as={FaExclamationTriangle} mr={1} />
              Error
            </>
          ),
        };
      case "pending":
      default:
        return {
          colorScheme: "yellow",
          children: (
            <>
              <Icon as={FaClock} mr={1} />
              Pending
            </>
          ),
        };
    }
  };

  return (
    <Badge 
      size={size} 
      variant="subtle" 
      alignSelf="flex-start" 
      {...getStatusProps()} 
    />
  );
};
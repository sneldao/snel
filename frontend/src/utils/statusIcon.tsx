import * as React from "react";
import { InfoIcon, CheckCircleIcon, WarningIcon } from "@chakra-ui/icons";
import { Spinner } from "@chakra-ui/react";

export const renderStatusIcon = (status: string) => {
  if (status === "pending") {
    return <InfoIcon color="blue.500" />;
  } else if (status === "processing") {
    return <Spinner size="sm" color="blue.500" />;
  } else if (status === "success") {
    return <CheckCircleIcon color="green.500" />;
  } else if (status === "error") {
    return <WarningIcon color="red.500" />;
  }
  return null;
};

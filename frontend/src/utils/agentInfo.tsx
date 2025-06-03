import * as React from "react";
import { Icon } from "@chakra-ui/react";
import {
  FaExchangeAlt,
  FaCalendarAlt,
  FaRobot,
  FaChartPie,
} from "react-icons/fa";

export type AgentType =
  | "default"
  | "swap"
  | "dca"
  | "brian"
  | "bridge"
  | "transfer"
  | "agno"
  | "portfolio";

export const getAgentInfo = (agentType?: AgentType) => {
  switch (agentType) {
    case "swap":
      return {
        name: "Swap Agent",
        handle: "@swap",
        avatarSrc: "/icon.png",
      };
    case "dca":
      return {
        name: "DCA Agent",
        handle: "@dca",
        avatarSrc: "/icon.png",
      };
    case "brian":
      return {
        name: "Brian",
        handle: "@brian",
        avatarSrc: "/icon.png",
      };
    case "bridge":
      return {
        name: "Bridge Agent",
        handle: "@bridge",
        avatarSrc: "/icon.png",
      };
    case "transfer":
      return {
        name: "Transfer Agent",
        handle: "@transfer",
        avatarSrc: "/icon.png",
      };
    case "agno":
      return {
        name: "Agno",
        handle: "@agno",
        avatarSrc: "/icon.png",
      };
    case "portfolio":
      return {
        name: "Portfolio Agent",
        handle: "@portfolio",
        avatarSrc: "/icon.png",
      };
    default:
      return {
        name: "SNEL",
        handle: "@snel",
        avatarSrc: "/icon.png",
      };
  }
};

export const getAgentIcon = (agentType?: AgentType) => {
  switch (agentType) {
    case "swap":
      return <Icon as={FaExchangeAlt} color="blue.500" />;
    case "dca":
      return <Icon as={FaCalendarAlt} color="green.500" />;
    case "brian":
      return <Icon as={FaRobot} color="purple.500" />;
    case "bridge":
      return <Icon as={FaExchangeAlt} color="orange.500" />;
    case "transfer":
      return <Icon as={FaExchangeAlt} color="green.500" />;
    case "agno":
    case "portfolio":
      return <Icon as={FaChartPie} color="teal.500" />;
    default:
      return <Icon as={FaRobot} color="gray.500" />;
  }
};

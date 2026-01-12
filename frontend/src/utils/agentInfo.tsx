import * as React from "react";
import { Icon } from "@chakra-ui/react";
import {
  FaExchangeAlt,
  FaCalendarAlt,
  FaRobot,
  FaChartPie,
  FaWallet,
  FaSearch,
  FaCreditCard,
  FaBolt,
} from "react-icons/fa";

export type AgentType =
  | "default"
  | "swap"
  | "dca"
  | "brian"
  | "bridge"
  | "transfer"
  | "agno"
  | "portfolio"
  | "balance"
  | "protocol_research"
  | "settings"
  | "payment";

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
        name: "Portfolio Analyst",
        handle: "@portfolio",
        avatarSrc: "/icon.png",
      };
    case "portfolio":
      return {
        name: "Portfolio Agent",
        handle: "@portfolio",
        avatarSrc: "/icon.png",
      };
    case "balance":
      return {
        name: "Balance Agent",
        handle: "@balance",
        avatarSrc: "/icon.png",
      };
    case "protocol_research":
      return {
        name: "Research Agent",
        handle: "@research",
        avatarSrc: "/icon.png",
      };
    case "settings":
      return {
        name: "Settings",
        handle: "@settings",
        avatarSrc: "/icon.png",
      };
    case "payment":
      return {
        name: "Payment Agent",
        handle: "@payment",
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
    case "balance":
      return <Icon as={FaWallet} color="blue.500" />;
    case "protocol_research":
      return <Icon as={FaSearch} color="purple.500" />;
    case "settings":
      return <Icon as={FaRobot} color="blue.500" />;
    case "payment":
      return <Icon as={FaCreditCard} color="green.500" />;
    default:
      return <Icon as={FaRobot} color="gray.500" />;
  }
};

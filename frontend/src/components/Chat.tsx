import * as React from "react";
import { AgnoService, AgnoResponse } from "../services/agnoService";
import { useAccount, useChainId } from "wagmi";
import ReactMarkdown from "react-markdown";
import { Spinner } from "@chakra-ui/react";
import { PortfolioAnalysis } from "./PortfolioAnalysis";
import { PortfolioSummary } from "./PortfolioSummary";

interface Message {
  content: string;
  timestamp: string;
  isCommand: boolean;
  status: "pending" | "processing" | "success" | "error";
  agentType?: string;
  intermediateSteps?: string[];
}

interface AnalysisProgressProps {
  steps: string[];
}

const AnalysisProgress: React.FC<AnalysisProgressProps> = ({ steps }) => {
  return (
    <div className="flex flex-col space-y-2 p-4 bg-gray-50 rounded-lg">
      <div className="flex items-center space-x-2">
        <Spinner />
        <span className="text-sm text-gray-600">
          {steps.length === 0
            ? "Starting portfolio analysis..."
            : "Analyzing portfolio..."}
        </span>
      </div>
      {steps.length > 0 && (
        <div className="text-xs text-gray-500 space-y-1">
          {steps.map((step, index) => (
            <div key={index} className="flex items-start space-x-2">
              <div className="w-2 h-2 mt-1.5 rounded-full bg-blue-500" />
              <div>{step}</div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export const Chat = () => {
  const [messages, setMessages] = React.useState<Message[]>([]);
  const [isLoading, setIsLoading] = React.useState(false);
  const [analysisSteps, setAnalysisSteps] = React.useState<string[]>([]);
  const agnoService = React.useMemo(() => new AgnoService(), []);
  const { address } = useAccount();
  const chainId = useChainId();
  const baseUrl =
    process.env.NODE_ENV === "production" ? "" : "http://localhost:8000";

  const handleDefaultCommand = async (command: string) => {
    const response = await fetch(`${baseUrl}/api/v1/chat/process-command`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        command,
        wallet_address: address,
        chain_id: chainId,
      }),
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    return await response.json();
  };

  const handleCommand = async (command: string) => {
    try {
      setIsLoading(true);
      setAnalysisSteps([]); // Reset analysis steps

      // Add command to messages
      const commandMessage: Message = {
        content: command,
        timestamp: new Date().toISOString(),
        isCommand: true,
        status: "success",
      };
      setMessages((prev: Message[]) => [...prev, commandMessage]);

      let response: AgnoResponse | any;

      // Check if it's a portfolio analysis command
      if (/portfolio|allocation|holdings|assets/i.test(command.toLowerCase())) {
        if (!address) {
          response = {
            content: "Please connect your wallet to analyze your portfolio.",
            agentType: "agno",
            status: "error",
          };
        } else {
          // Add initial analysis message
          setMessages((prev: Message[]) => [
            ...prev,
            {
              content: "Starting portfolio analysis...",
              timestamp: new Date().toISOString(),
              isCommand: false,
              status: "processing",
              agentType: "agno",
              intermediateSteps: [],
            },
          ]);

          response = await agnoService.analyzePortfolio(
            command,
            address,
            chainId,
            (step: string) => {
              setAnalysisSteps((prev) => [...prev, step]);
            }
          );
        }
      } else {
        // Handle other commands with existing logic
        response = await handleDefaultCommand(command);
      }

      // Update or add response message
      setMessages((prev: Message[]) => {
        const lastMessage = prev[prev.length - 1];
        if (
          lastMessage?.status === "processing" &&
          lastMessage?.agentType === "agno"
        ) {
          // Update the processing message with the final response
          return [
            ...prev.slice(0, -1),
            {
              ...response,
              timestamp: new Date().toISOString(),
              isCommand: false,
              intermediateSteps: analysisSteps,
            },
          ];
        } else {
          // Add new response message
          return [
            ...prev,
            {
              ...response,
              timestamp: new Date().toISOString(),
              isCommand: false,
            },
          ];
        }
      });
    } catch (error) {
      console.error("Error handling command:", error);
      // Add error message
      setMessages((prev: Message[]) => [
        ...prev,
        {
          content: error instanceof Error ? error.message : "An error occurred",
          timestamp: new Date().toISOString(),
          isCommand: false,
          status: "error",
        },
      ]);
    } finally {
      setIsLoading(false);
      setAnalysisSteps([]); // Clear analysis steps
    }
  };

  const renderMessage = (message: Message) => {
    if (message.status === "processing" && message.agentType === "agno") {
      return <AnalysisProgress steps={analysisSteps} />;
    }

    // If it's an Agno response, use the appropriate component
    if (message.agentType === "agno" && !message.isCommand) {
      const agnoResponse = message as unknown as AgnoResponse;

      // Debug logging
      console.log("Chat renderMessage Debug:", {
        hasAnalysis: !!agnoResponse.analysis,
        hasSummary: !!agnoResponse.summary,
        hasFullAnalysis: !!agnoResponse.fullAnalysis,
        messageContent: message.content?.substring(0, 100),
        fullAgnoResponse: agnoResponse, // Add full response for debugging
      });

      // ALWAYS use PortfolioSummary for Agno responses to ensure button appears
      console.log("FORCING PortfolioSummary component for Agno response");
      return <PortfolioSummary response={agnoResponse} />;
    }

    // For all other messages, render as markdown
    return (
      <div
        className={`message ${message.isCommand ? "command" : "response"} ${
          message.status === "error" ? "error" : ""
        }`}
      >
        <div className="prose max-w-none">
          <ReactMarkdown>{message.content}</ReactMarkdown>
        </div>
      </div>
    );
  };

  return (
    <div className="chat-container">
      <div className="messages">
        {messages.map((message, index) => (
          <div key={index} className="message-wrapper">
            {renderMessage(message)}
          </div>
        ))}
      </div>
      {/* Your existing command input component */}
    </div>
  );
};

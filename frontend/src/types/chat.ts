import { PortfolioAction } from "../services/portfolioService";

export interface ChatMessageMetadata {
  stage?: string;
  progress?: number;
  agent?: string;
  reasoning?: string[];
  confidence?: number;
  chainContext?: string[];
  suggestedActions?: PortfolioAction[];
  messageType?: "progress" | "thought" | "action" | "error";
}

export interface ChatMessageProps {
  id: string;
  type: "user" | "assistant" | "system" | "progress";
  content: string;
  timestamp: Date;
  metadata?: ChatMessageMetadata;
  style?: React.CSSProperties;
}

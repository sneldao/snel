import * as React from "react";
import { Box, Text, VStack } from "@chakra-ui/react";
import { PaymentHistoryList } from "./PaymentHistoryList";
import { SpendingAnalyticsView } from "./SpendingAnalyticsView";
import { RecipientListView } from "./RecipientListView";
import { PaymentTemplateListView } from "./PaymentTemplateListView";
import { PaymentHistoryItem, SpendingAnalytics, Recipient, PaymentTemplate } from "../services/paymentHistoryService";

interface PaymentHistoryResponseProps {
  content: {
    message: string;
    type: string;
    history?: PaymentHistoryItem[];
    analytics?: SpendingAnalytics;
    recipients?: Recipient[];
    templates?: PaymentTemplate[];
  };
  onAddRecipient?: () => void;
  onSelectRecipient?: (recipient: Recipient) => void;
}

export const PaymentHistoryResponse: React.FC<PaymentHistoryResponseProps> = ({ 
  content,
  onAddRecipient,
  onSelectRecipient
}) => {
  const [isLoading, setIsLoading] = React.useState(false);

  if (content.type === "payment_history" && content.history) {
    return (
      <Box borderWidth="1px" borderRadius="lg" p={4} bg="white">
        <Text fontWeight="bold" mb={3}>{content.message}</Text>
        <PaymentHistoryList 
          items={content.history} 
          isLoading={isLoading} 
        />
      </Box>
    );
  }

  if (content.type === "spending_analytics" && content.analytics) {
    return (
      <Box borderWidth="1px" borderRadius="lg" p={4} bg="white">
        <Text fontWeight="bold" mb={3}>{content.message}</Text>
        <SpendingAnalyticsView 
          analytics={content.analytics} 
          isLoading={isLoading} 
        />
      </Box>
    );
  }

  if (content.type === "recipients" && content.recipients) {
    return (
      <Box borderWidth="1px" borderRadius="lg" p={4} bg="white">
        <Text fontWeight="bold" mb={3}>{content.message}</Text>
        <RecipientListView 
          recipients={content.recipients} 
          isLoading={isLoading}
          onAddRecipient={onAddRecipient || (() => {})}
          onSelectRecipient={onSelectRecipient || (() => {})}
        />
      </Box>
    );
  }

  if (content.type === "payment_templates" && content.templates) {
    return (
      <Box borderWidth="1px" borderRadius="lg" p={4} bg="white">
        <Text fontWeight="bold" mb={3}>{content.message}</Text>
        <PaymentTemplateListView 
          templates={content.templates} 
          isLoading={isLoading}
          onAddTemplate={() => {
            // Trigger the add payment template modal
            if (onAddRecipient) {
              onAddRecipient();
            }
          }}
          onUseTemplate={(template) => {
            // Handle template usage by pre-filling a send command
            if (onSelectRecipient) {
              onSelectRecipient({
                id: '',
                name: template.name,
                address: template.recipient,
                chainId: template.chainId
              });
            }
          }}
        />
      </Box>
    );
  }

  return (
    <Box borderWidth="1px" borderRadius="lg" p={4} bg="white">
      <Text>{content.message}</Text>
    </Box>
  );
};
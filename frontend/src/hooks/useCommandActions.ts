import { useToast } from "@chakra-ui/react";

export const useCommandActions = () => {
  const toast = useToast();

  const handleConfirm = () => {
    // Find the closest command input (improved approach that doesn't simulate key events)
    const messageForm = document.querySelector("form");
    const inputElement = messageForm?.querySelector(
      'input[placeholder="Type a command..."]'
    ) as HTMLInputElement | null;

    if (inputElement && messageForm) {
      inputElement.value = "yes";

      // Instead of dispatching keyboard events which may have side effects,
      // trigger the form's submit handler programmatically
      const formSubmitEvent = new Event("submit", {
        bubbles: true,
        cancelable: true,
      });
      messageForm.dispatchEvent(formSubmitEvent);
    } else {
      // Fallback to simpler approach if form can't be found
      const event = new CustomEvent("swap-confirmation", {
        detail: { confirmed: true, command: "yes" },
        bubbles: true,
      });
      document.dispatchEvent(event);

      // Also set a value in session storage as another fallback
      sessionStorage.setItem(
        "swap_confirmation",
        JSON.stringify({ confirmed: true, timestamp: Date.now() })
      );
    }
  };

  const handleCancel = () => {
    // Find the closest command input (improved approach that doesn't simulate key events)
    const messageForm = document.querySelector("form");
    const inputElement = messageForm?.querySelector(
      'input[placeholder="Type a command..."]'
    ) as HTMLInputElement | null;

    if (inputElement && messageForm) {
      inputElement.value = "no";

      // Instead of dispatching keyboard events which may have side effects,
      // trigger the form's submit handler programmatically
      const formSubmitEvent = new Event("submit", {
        bubbles: true,
        cancelable: true,
      });
      messageForm.dispatchEvent(formSubmitEvent);
    } else {
      // Fallback to simpler approach if form can't be found
      const event = new CustomEvent("swap-confirmation", {
        detail: { confirmed: false, command: "no" },
        bubbles: true,
      });
      document.dispatchEvent(event);

      // Also set a value in session storage as another fallback
      sessionStorage.setItem(
        "swap_confirmation",
        JSON.stringify({ confirmed: false, timestamp: Date.now() })
      );
    }
  };

  const handleQuoteSelect = (
    content: any,
    timestamp: string,
    isCommand: boolean,
    status: string,
    awaitingConfirmation: boolean,
    agentType: string,
    metadata: any,
    requires_selection: boolean,
    all_quotes: any[],
    onQuoteSelect?: (response: any, quote: any) => void,
    quote?: any
  ) => {
    if (onQuoteSelect) {
      onQuoteSelect(
        {
          content,
          timestamp,
          isCommand,
          status,
          awaitingConfirmation,
          agentType,
          metadata,
          requires_selection,
          all_quotes,
        },
        quote
      );
    }
  };

  const handlePredefinedQuery = (query: string) => {
    // Find the command input and populate it with the query
    const inputElement = document.querySelector(
      'input[placeholder*="command"]'
    ) as HTMLInputElement;

    if (inputElement) {
      // Set the value
      inputElement.value = query;
      inputElement.focus();

      // Trigger input event to update React state
      const inputEvent = new Event("input", { bubbles: true });
      inputElement.dispatchEvent(inputEvent);

      // Automatically submit the form to execute the query
      const form = inputElement.closest("form");
      if (form) {
        const submitEvent = new Event("submit", {
          bubbles: true,
          cancelable: true,
        });
        form.dispatchEvent(submitEvent);
      } else {
        // Fallback - try to find the send button and click it
        const sendButton =
          document.querySelector('button[type="submit"]') ||
          document.querySelector('button:contains("Send")');
        if (sendButton) {
          (sendButton as HTMLButtonElement).click();
        } else {
          // If all else fails, show a toast with instructions
          toast({
            title: "Query Ready",
            description: `"${query}" added to input. Press Enter to send.`,
            status: "info",
            duration: 3000,
            isClosable: true,
          });
        }
      }
    }
  };

  return {
    handleConfirm,
    handleCancel,
    handleQuoteSelect,
    handlePredefinedQuery,
  };
};

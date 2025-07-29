import React from "react";
import { ChakraProvider } from "@chakra-ui/react";
import EnhancedMainApp from "./components/EnhancedMainApp";

function App() {
  return (
    <ChakraProvider>
      <EnhancedMainApp />
    </ChakraProvider>
  );
}

export default App;

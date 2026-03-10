"use client";

import { useState, useEffect } from "react";
import { ChakraProvider, CSSReset } from "@chakra-ui/react";
import { Web3Provider } from "./Web3Provider";
import { StarknetProvider } from "./StarknetProvider";
import { GMPProvider } from "../contexts/GMPContext";
import { Footer } from "../components/Footer";

export function Providers({ children }: { children: React.ReactNode }) {
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  return (
    <Web3Provider>
      <StarknetProvider>
        <ChakraProvider>
          <CSSReset />
          <GMPProvider>
            {mounted && children}
          </GMPProvider>
          <Footer />
        </ChakraProvider>
      </StarknetProvider>
    </Web3Provider>
  );
}

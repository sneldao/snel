"use client";

import { useState, useEffect } from "react";
import { ChakraProvider, CSSReset, ColorModeScript } from "@chakra-ui/react";
import { Web3Provider } from "./Web3Provider";
import { StarknetProvider } from "./StarknetProvider";
import { GMPProvider } from "../contexts/GMPContext";
import { Footer } from "../components/Footer";
import theme from "../theme";

export function Providers({ children }: { children: React.ReactNode }) {
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  return (
    <>
      <ColorModeScript initialColorMode={theme.config.initialColorMode} />
      <Web3Provider>
        <StarknetProvider>
          <ChakraProvider theme={theme}>
            <CSSReset />
            <GMPProvider>
              {mounted && children}
            </GMPProvider>
            <Footer />
          </ChakraProvider>
        </StarknetProvider>
      </Web3Provider>
    </>
  );
}

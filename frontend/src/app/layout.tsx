"use client";

import { useState, useEffect } from "react";
import { ChakraProvider, CSSReset } from "@chakra-ui/react";
import { Web3Provider } from "../providers/Web3Provider";
import { Footer } from "../components/Footer";

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  return (
    <html lang="en">
      <head>
        <title>Pointless - Crypto Command Interpreter</title>
        <meta
          name="description"
          content="A friendly crypto command interpreter"
        />
      </head>
      <body>
        <Web3Provider>
          <ChakraProvider>
            <CSSReset />
            {mounted && children}
            <Footer />
          </ChakraProvider>
        </Web3Provider>
      </body>
    </html>
  );
}

"use client";

import * as React from "react";
import { ChakraProvider, CSSReset } from "@chakra-ui/react";
import { Web3Provider } from "../providers/Web3Provider";

type RootLayoutProps = {
  children: React.ReactNode;
};

export default function RootLayout({ children }: RootLayoutProps) {
  const [mounted, setMounted] = React.useState(false);

  React.useEffect(() => {
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
          </ChakraProvider>
        </Web3Provider>
      </body>
    </html>
  );
}

"use client";

import * as React from "react";
import { ChakraProvider, CSSReset } from "@chakra-ui/react";

type RootLayoutProps = {
  children: React.ReactNode;
};

export default function RootLayout({ children }: RootLayoutProps) {
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
        <ChakraProvider>
          <CSSReset />
          {children}
        </ChakraProvider>
      </body>
    </html>
  );
}

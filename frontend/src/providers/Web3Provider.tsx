"use client";

import { WagmiProvider, createConfig, http } from "wagmi";
import { base, mainnet, optimism, arbitrum } from "wagmi/chains";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ConnectKitProvider, getDefaultConfig } from "connectkit";

const config = createConfig(
  getDefaultConfig({
    // Your dApp's chains
    chains: [base, mainnet, optimism, arbitrum],
    transports: {
      // RPC URL for each chain
      [base.id]: http(
        `https://base-mainnet.g.alchemy.com/v2/${process.env.NEXT_PUBLIC_ALCHEMY_KEY}`
      ),
      [mainnet.id]: http(
        `https://eth-mainnet.g.alchemy.com/v2/${process.env.NEXT_PUBLIC_ALCHEMY_KEY}`
      ),
      [optimism.id]: http(
        `https://opt-mainnet.g.alchemy.com/v2/${process.env.NEXT_PUBLIC_ALCHEMY_KEY}`
      ),
      [arbitrum.id]: http(
        `https://arb-mainnet.g.alchemy.com/v2/${process.env.NEXT_PUBLIC_ALCHEMY_KEY}`
      ),
    },

    // Required API Keys
    walletConnectProjectId:
      process.env.NEXT_PUBLIC_WALLETCONNECT_PROJECT_ID || "",

    // Required App Info
    appName: "Pointless",

    // Optional App Info
    appDescription: "Your friendly crypto command interpreter",
    appUrl: "https://pointless.xyz", // your app's url
    appIcon: "https://pointless.xyz/logo.png", // your app's icon
  })
);

const queryClient = new QueryClient();

interface Web3ProviderProps {
  children: React.ReactNode;
}

export const Web3Provider = ({ children }: Web3ProviderProps) => {
  return (
    <WagmiProvider config={config}>
      <QueryClientProvider client={queryClient}>
        <ConnectKitProvider theme="soft">{children}</ConnectKitProvider>
      </QueryClientProvider>
    </WagmiProvider>
  );
};

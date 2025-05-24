"use client";

import * as React from "react";
import { WagmiProvider, createConfig, http } from "wagmi";
import {
  base,
  mainnet,
  optimism,
  arbitrum,
  polygon,
  avalanche,
  scroll,
  bsc,
  linea,
  mantle,
  blast,
  mode,
  gnosis,
  zkSync,
  taiko,
  type Chain,
} from "wagmi/chains";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ConnectKitProvider, getDefaultConfig } from "connectkit";

// Define RPC URLs
const ALCHEMY_SUPPORTED_CHAINS = {
  [mainnet.id]: `https://eth-mainnet.g.alchemy.com/v2/${process.env.NEXT_PUBLIC_ALCHEMY_KEY}`,
  [base.id]: `https://base-mainnet.g.alchemy.com/v2/${process.env.NEXT_PUBLIC_ALCHEMY_KEY}`,
  [optimism.id]: `https://opt-mainnet.g.alchemy.com/v2/${process.env.NEXT_PUBLIC_ALCHEMY_KEY}`,
  [arbitrum.id]: `https://arb-mainnet.g.alchemy.com/v2/${process.env.NEXT_PUBLIC_ALCHEMY_KEY}`,
  [polygon.id]: `https://polygon-mainnet.g.alchemy.com/v2/${process.env.NEXT_PUBLIC_ALCHEMY_KEY}`,
} as const;

const PUBLIC_RPC_URLS = {
  [avalanche.id]: `https://avalanche-mainnet.infura.io/v3/${process.env.NEXT_PUBLIC_INFURA_KEY}`,
  [scroll.id]: "https://rpc.scroll.io",
  [bsc.id]: "https://bsc-dataseed.binance.org",
  [linea.id]: "https://rpc.linea.build",
  [mantle.id]: "https://rpc.mantle.xyz",
  [blast.id]: "https://rpc.blast.io",
  [mode.id]: "https://mainnet.mode.network",
  [gnosis.id]: "https://rpc.gnosischain.com",
  [zkSync.id]: "https://mainnet.era.zksync.io",
  [taiko.id]: "https://rpc.test.taiko.xyz",
} as const;

// Combine all supported chains
const ALL_SUPPORTED_CHAINS = [
  // Layer 1
  mainnet,
  bsc,
  gnosis,
  // Layer 2 & Rollups
  base,
  optimism,
  arbitrum,
  polygon,
  linea,
  scroll,
  zkSync,
  mode,
  taiko,
  // Other Networks
  avalanche,
  mantle,
  blast,
] as const satisfies readonly [Chain, ...Chain[]];

const config = createConfig(
  getDefaultConfig({
    // Your dApp's chains
    chains: ALL_SUPPORTED_CHAINS,
    transports: {
      ...Object.entries(ALCHEMY_SUPPORTED_CHAINS).reduce(
        (acc, [chainId, url]) => ({
          ...acc,
          [chainId]: http(url, {
            // Disable retries to prevent retrying cancelled transactions
            retryCount: 0,
            retryDelay: 0,
          }),
        }),
        {}
      ),
      ...Object.entries(PUBLIC_RPC_URLS).reduce(
        (acc, [chainId, url]) => ({
          ...acc,
          [chainId]: http(url, {
            // Disable retries to prevent retrying cancelled transactions
            retryCount: 0,
            retryDelay: 0,
          }),
        }),
        {}
      ),
    },

    // Required API Keys
    walletConnectProjectId:
      process.env.NEXT_PUBLIC_WALLETCONNECT_PROJECT_ID || "",

    // Required App Info
    appName: "Snel",

    // Optional App Info
    appDescription: "SNEL",
    appUrl: "https://stable-snel.netlify.app",
    appIcon: "https://stable-snel.netlify.app/icon.png",
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
        <ConnectKitProvider
          theme="soft"
          options={{
            hideNoWalletCTA: true,
            hideBalance: false,
            embedGoogleFonts: true,
            initialChainId: base.id,
          }}
        >
          {children}
        </ConnectKitProvider>
      </QueryClientProvider>
    </WagmiProvider>
  );
};

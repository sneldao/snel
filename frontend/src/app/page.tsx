"use client";

import * as React from "react";
import dynamicImport from "next/dynamic";

// Force dynamic rendering to avoid SSR issues with wallet components
export const dynamic = "force-dynamic";

// Dynamically import MainApp to prevent SSR issues
const MainApp = dynamicImport(() => import("../components/MainApp"), {
  ssr: false,
  loading: () => (
    <div
      style={{
        minHeight: "100vh",
        backgroundColor: "#f7fafc",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        fontSize: "18px",
        color: "#4a5568",
      }}
    >
      Loading Snel...
    </div>
  ),
});

export default function Home() {
  return <MainApp />;
}

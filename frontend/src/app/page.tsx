"use client";

import * as React from "react";
import dynamicImport from "next/dynamic";

// Force dynamic rendering to avoid SSR issues with wallet components
export const dynamic = "force-dynamic";

// Create a loading component with CSS animation
const LoadingComponent = () => {
  React.useEffect(() => {
    // Inject CSS animation into the document head
    const style = document.createElement("style");
    style.textContent = `
      @keyframes flash {
        0%, 50% {
          opacity: 0.3;
          transform: scale(1);
        }
        25% {
          opacity: 1;
          transform: scale(1.2);
        }
      }
      .loading-char {
        animation: flash 1.5s infinite;
        display: inline-block;
      }
      .loading-char:nth-child(1) { animation-delay: 0s; }
      .loading-char:nth-child(2) { animation-delay: 0.5s; }
      .loading-char:nth-child(3) { animation-delay: 1s; }
    `;
    document.head.appendChild(style);

    return () => {
      document.head.removeChild(style);
    };
  }, []);

  return (
    <div
      style={{
        minHeight: "100vh",
        backgroundColor: "#f7fafc",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        fontSize: "24px",
        color: "#4a5568",
        fontFamily: "monospace",
      }}
    >
      <div
        style={{
          display: "flex",
          gap: "8px",
          alignItems: "center",
        }}
      >
        <span className="loading-char">๑ï</span>
        <span className="loading-char">๑ï</span>
        <span className="loading-char">๑ï</span>
      </div>
    </div>
  );
};

// Dynamically import MainApp to prevent SSR issues
const MainApp = dynamicImport(() => import("../components/MainApp"), {
  ssr: false,
  loading: LoadingComponent,
});

export default function Home() {
  return <MainApp />;
}

import { Metadata } from "next";
import { Providers } from "../providers/Providers";

// Metadata must be exported from a Server Component
export const metadata: Metadata = {
  title: "SNEL",
  description: "Super pointless agent",
  icons: {
    icon: [
      { url: "/favicon.ico", sizes: "any" },
      { url: "/icon.png", type: "image/png" },
    ],
    apple: { url: "/apple-touch-icon.png", sizes: "180x180" },
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <head>
        {/* Remove the manual link tags since they're handled by metadata */}
      </head>
      <body>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}

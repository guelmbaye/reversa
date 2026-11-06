import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "REVERSA — Recovery Console",
  description: "Self-healing commerce for AI agents. Verified against real PayPal Sandbox evidence.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}

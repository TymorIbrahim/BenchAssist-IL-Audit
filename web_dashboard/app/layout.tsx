import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "BenchAssist-IL Audit Dashboard",
  description:
    "Research audit interface for a toy Israeli housing bench-memo assistant. Not legal advice.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}

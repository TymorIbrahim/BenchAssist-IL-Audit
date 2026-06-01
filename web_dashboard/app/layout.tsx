import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import "./v2-design-system.css";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "BenchAssist-IL Detention Audit Dashboard",
  description:
    "AI fairness audit dashboard for Israeli criminal detention/remand scenarios. Screens dangerousness-level shifts under counterfactual demographic and proxy changes. Research tool — not legal advice.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={inter.className}>
      <body>{children}</body>
    </html>
  );
}

import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "MIB — Mooring Intelligence Backend",
  description:
    "Real-time BHP vessel mooring-hook tension monitoring with predictive alerts, four-tier escalation, and 3D movement tracking.",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" className="antialiased">
      <body>{children}</body>
    </html>
  );
}

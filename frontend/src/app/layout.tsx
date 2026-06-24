import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Retail AI Analyst Dashboard",
  description: "Enterprise BI Engine to query 2.5 million atomic POS transactions instantly. Backed by verified Kimball dimensional constraints and generative AI reasoning.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>
        {children}
      </body>
    </html>
  );
}

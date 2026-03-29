import type { Metadata } from "next";
import { Roboto } from "next/font/google";
import "./globals.css";

const robotoCaptions = Roboto({
  weight: ["400", "500", "700"],
  subsets: ["latin"],
  variable: "--font-caption-roboto",
  display: "swap",
});

export const metadata: Metadata = {
  title: "ET Nexus | AI-Native Financial News",
  description: "Hyper-personalized, context-aware financial intelligence powered by multi-agent AI.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="light">
      <body className={`antialiased min-h-screen ${robotoCaptions.variable}`}>
        {children}
      </body>
    </html>
  );
}

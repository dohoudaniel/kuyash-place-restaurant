import type { Metadata } from "next";
import { connection } from "next/server";
import { Inter, Playfair_Display, Geist } from "next/font/google";
import "./globals.css";
import { cn } from "@/lib/utils";
import SiteChrome from "@/components/layouts/SiteChrome";
import AuthProvider from "@/components/providers/AuthProvider";

const geist = Geist({subsets:['latin'],variable:'--font-sans'});

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
  display: "swap",
  preload: false,
});

const playfair = Playfair_Display({
  subsets: ["latin"],
  variable: "--font-playfair",
  style: ["normal", "italic"],
  display: "swap",
  preload: false,
});

export const metadata: Metadata = {
  title: "Kuyash Place Restaurant",
  description: "Feel confident in every bite — crafted meals you can trust. Delicious comfort for daily living.",
};

export default async function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  // Render per request: the Content Security Policy in proxy.ts uses a fresh
  // nonce each time, and a page built ahead of time could not carry it.
  await connection();

  return (
    <html lang="en" className={cn("h-full", "antialiased", inter.variable, playfair.variable, "font-sans", geist.variable)}>
      <body className="min-h-full flex flex-col font-[var(--font-inter)]">
        <AuthProvider>
          <SiteChrome>{children}</SiteChrome>
        </AuthProvider>
      </body>
    </html>
  );
}

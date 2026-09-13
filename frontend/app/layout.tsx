import type { Metadata } from "next";
import { Inter, Playfair_Display, Geist } from "next/font/google";
import "./globals.css";
import { cn } from "@/lib/utils";
import Navbar from "@/components/layouts/navbar/Navbar";
import Footer from "@/components/layouts/footer";
import ChatButton from "@/components/features/chat";
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

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={cn("h-full", "antialiased", inter.variable, playfair.variable, "font-sans", geist.variable)}>
      <body className="min-h-full flex flex-col font-[var(--font-inter)]">
        <AuthProvider>
          <Navbar />
          {children}
          <Footer />
          <ChatButton />
        </AuthProvider>
      </body>
    </html>
  );
}

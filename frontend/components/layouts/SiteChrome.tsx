"use client";

import { usePathname } from "next/navigation";
import Navbar from "@/components/layouts/navbar/Navbar";
import Footer from "@/components/layouts/footer";
import ChatButton from "@/components/features/chat";

/** Staff screens that run full screen, without the customer site's navigation, footer or chat. */
const BARE_PREFIXES = ["/kitchen"];

export default function SiteChrome({ children }: { children: React.ReactNode }) {
  const pathname = usePathname() ?? "";
  const bare = BARE_PREFIXES.some((prefix) => pathname === prefix || pathname.startsWith(`${prefix}/`));
  if (bare) return <>{children}</>;
  return (
    <>
      <Navbar />
      {children}
      <Footer />
      <ChatButton />
    </>
  );
}

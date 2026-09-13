"use client";

import { useEffect } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { safeNext } from "@/lib/auth/next";
import { useAuthModalStore } from "@/lib/store/authModalStore";

/**
 * Opens the sign-in dialog from the URL: `/?auth=login&next=/account`.
 *
 * `proxy.ts` sends signed-out visitors here. The parameters are removed once
 * read, so a refresh or a shared link does not keep reopening the dialog.
 */
export default function AuthQueryOpener() {
  const searchParams = useSearchParams();
  const pathname = usePathname();
  const router = useRouter();
  const open = useAuthModalStore((state) => state.open);

  useEffect(() => {
    const view = searchParams.get("auth");
    if (view !== "login" && view !== "signup") return;

    open(view, safeNext(searchParams.get("next"), pathname));

    const remaining = new URLSearchParams(searchParams.toString());
    remaining.delete("auth");
    remaining.delete("next");
    const query = remaining.toString();
    router.replace(query ? `${pathname}?${query}` : pathname, { scroll: false });
  }, [searchParams, pathname, router, open]);

  return null;
}

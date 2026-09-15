"use client";

import { RequireAuth } from "@/components/features/auth";
import KitchenBoard from "@/components/features/kitchen";

/** The Kitchen Display System. Full screen, without the customer site's navigation. */
export default function KitchenPage() {
  return (
    <RequireAuth>
      <KitchenBoard />
    </RequireAuth>
  );
}

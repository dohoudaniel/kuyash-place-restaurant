"use client";

import { useEffect, useState } from "react";
import { loadBranch, loadOpeningHours, loadSiteSettings } from "@/lib/api/site";
import type { Branch, OpeningHoursResponse, SiteSettings } from "@/lib/api/types";

/** Branch, site settings and opening hours. Each is null until loaded, and stays null if it fails. */
export function useSiteInfo() {
  const [branch, setBranch] = useState<Branch | null>(null);
  const [settings, setSettings] = useState<SiteSettings | null>(null);
  const [hours, setHours] = useState<OpeningHoursResponse | null>(null);

  useEffect(() => {
    let cancelled = false;
    loadBranch().then((data) => !cancelled && setBranch(data)).catch(() => undefined);
    loadSiteSettings().then((data) => !cancelled && setSettings(data)).catch(() => undefined);
    loadOpeningHours().then((data) => !cancelled && setHours(data)).catch(() => undefined);
    return () => {
      cancelled = true;
    };
  }, []);

  return { branch, settings, hours };
}

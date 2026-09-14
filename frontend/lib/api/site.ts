/**
 * Restaurant facts every page shows — address, phone, hours, social links.
 *
 * Fetched once per page load and shared. These used to be typed into a dozen
 * components, several of them inventing details ("24/7 hotline +234 800 KUYASH").
 */
import { api } from "./client";
import type { Award, Branch, Faq, LegalPage, OpeningHoursResponse, SiteSettings, TeamMember } from "./types";

function cached<T>(load: () => Promise<T>): () => Promise<T> {
  let request: Promise<T> | null = null;
  return () =>
    (request ??= load().catch((error) => {
      request = null; // let the next caller retry
      throw error;
    }));
}

export const loadBranch = cached(() => api<Branch>("/core/branch/"));
export const loadSiteSettings = cached(() => api<SiteSettings>("/core/settings/"));
export const loadOpeningHours = cached(() => api<OpeningHoursResponse>("/core/opening-hours/"));
export const loadFaq = cached(() => api<Faq[]>("/support/faq/"));
export const loadTeam = cached(() => api<TeamMember[]>("/core/team/"));
export const loadAwards = cached(() => api<Award[]>("/core/awards/"));

/** The current published version of a policy page. */
export const fetchLegalPage = (slug: string) => api<LegalPage>(`/core/legal/${encodeURIComponent(slug)}/`);

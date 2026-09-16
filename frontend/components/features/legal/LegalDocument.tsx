"use client";

import { useEffect, useState } from "react";
import { Loader2 } from "lucide-react";
import { formatDate } from "@/components/features/orders/statusStyles";
import { fetchLegalPage } from "@/lib/api/site";
import type { LegalPage } from "@/lib/api/types";
import { renderMarkdown } from "@/lib/content/markdown";
import { useSiteInfo } from "@/lib/site/useSiteInfo";

interface LegalDocumentProps {
  slug: string;
  /** Shown while loading, and if the page cannot be fetched. */
  fallbackTitle: string;
}

/**
 * A policy page, as published and versioned in the admin.
 *
 * These pages used to be hardcoded route files, dated "January 2025", ending in
 * a placeholder phone number, and in places contradicting what checkout charged.
 */
export default function LegalDocument({ slug, fallbackTitle }: LegalDocumentProps) {
  const { branch } = useSiteInfo();
  const [page, setPage] = useState<LegalPage | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let cancelled = false;
    fetchLegalPage(slug)
      .then((data) => !cancelled && setPage(data))
      .catch(() => !cancelled && setFailed(true));
    return () => {
      cancelled = true;
    };
  }, [slug]);

  const email = branch?.email;

  return (
    <div className="min-h-screen pt-20 sm:pt-24 pb-12" style={{ background: "var(--gray-light)" }}>
      <div className="container-custom max-w-4xl">
        <div className="bg-white rounded-2xl p-8 sm:p-12 shadow-sm">
          <h1 className="font-black text-4xl sm:text-5xl mb-4" style={{ fontFamily: "var(--font-playfair)", color: "var(--black)" }}>
            {page?.title ?? fallbackTitle}
          </h1>
          {page && (
            <p className="text-sm mb-8" style={{ color: "var(--text-muted)" }}>
              Version {page.version} · Effective {formatDate(page.effective_from, "short")}
            </p>
          )}

          {failed ? (
            <p role="alert" className="text-base" style={{ color: "var(--text-muted)" }}>
              We couldn&apos;t load this page. Please check your connection and try again.
            </p>
          ) : !page ? (
            <div className="flex justify-center py-12" role="status" aria-label="Loading">
              <Loader2 className="w-6 h-6 animate-spin" style={{ color: "var(--red)" }} />
            </div>
          ) : (
            <div style={{ color: "var(--black)" }}>
              {renderMarkdown(
                page.body,
                {
                  h2: "font-black text-2xl mb-4 mt-8",
                  h3: "font-black text-xl mb-3 mt-8",
                  p: "text-base leading-relaxed mb-3",
                  ul: "list-disc pl-6 space-y-2 text-base leading-relaxed mb-3",
                  link: "underline font-bold",
                  style: {
                    heading: { fontFamily: "var(--font-playfair)" },
                    text: { color: "var(--text-muted)" },
                    link: { color: "var(--red)" },
                  },
                },
                { skipHeading: page.title }
              )}

              {(branch?.phone || email) && (
                <section className="mt-10 pt-6" style={{ borderTop: "1px solid var(--gray-mid)" }}>
                  <h2 className="font-black text-2xl mb-4" style={{ fontFamily: "var(--font-playfair)" }}>
                    Questions?
                  </h2>
                  <div className="space-y-1 text-base" style={{ color: "var(--text-muted)" }}>
                    {email && <p>Email: <a href={`mailto:${email}`} className="underline font-bold" style={{ color: "var(--red)" }}>{email}</a></p>}
                    {branch?.phone && <p>Phone: <a href={`tel:${branch.phone}`} className="underline font-bold" style={{ color: "var(--red)" }}>{branch.phone}</a></p>}
                    {branch?.address_line && <p>Address: {[branch.address_line, branch.city, branch.state].filter(Boolean).join(", ")}</p>}
                  </div>
                </section>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

"use client";

import { useEffect, useState } from "react";
import { ChevronDown, HelpCircle } from "lucide-react";
import { loadFaq } from "@/lib/api/site";
import type { Faq } from "@/lib/api/types";
import { useSiteInfo } from "@/lib/site/useSiteInfo";

/**
 * Answers from the FAQ the team maintains in the admin. The eight hardcoded
 * answers here promised valet parking, a 30-seat private room and 30–45 minute
 * delivery — none of which anyone had confirmed.
 */
export default function FAQSection() {
  const { branch } = useSiteInfo();
  const [faqs, setFaqs] = useState<Faq[]>([]);
  const [openIndex, setOpenIndex] = useState<number | null>(0);

  useEffect(() => {
    let cancelled = false;
    loadFaq().then((list) => !cancelled && setFaqs(list)).catch(() => undefined);
    return () => {
      cancelled = true;
    };
  }, []);

  if (faqs.length === 0) return null;

  return (
    <div className="bg-white rounded-xl border p-6 sm:p-8" style={{ borderColor: "var(--gray-mid)" }}>
      <div className="flex items-center gap-3 mb-6">
        <div className="w-12 h-12 rounded-full flex items-center justify-center" style={{ background: "rgba(217,4,41,0.08)" }}>
          <HelpCircle className="w-6 h-6" style={{ color: "var(--red)" }} />
        </div>
        <div>
          <h3 className="font-black text-xl sm:text-2xl" style={{ fontFamily: "var(--font-playfair)", color: "var(--black)" }}>
            Frequently Asked Questions
          </h3>
          <p className="text-sm" style={{ color: "var(--text-muted)" }}>
            Quick answers to common questions
          </p>
        </div>
      </div>

      <div className="grid md:grid-cols-2 gap-3">
        {faqs.map((faq, idx) => {
          const isOpen = openIndex === idx;
          const panelId = `faq-panel-${faq.id}`;
          return (
            <div
              key={faq.id}
              className="rounded-xl border transition-all"
              style={{ borderColor: isOpen ? "var(--red)" : "var(--gray-mid)", background: isOpen ? "rgba(217,4,41,0.02)" : "white" }}
            >
              <button
                onClick={() => setOpenIndex(isOpen ? null : idx)}
                aria-expanded={isOpen}
                aria-controls={panelId}
                className="w-full flex items-center justify-between gap-3 p-4 text-left"
              >
                <h4 className="font-bold text-sm" style={{ color: "var(--black)" }}>
                  {faq.question}
                </h4>
                <ChevronDown
                  className={`w-5 h-5 flex-shrink-0 transition-transform ${isOpen ? "rotate-180" : ""}`}
                  style={{ color: isOpen ? "var(--red)" : "var(--text-muted)" }}
                />
              </button>
              {isOpen && (
                <div id={panelId} className="px-4 pb-4">
                  <p className="text-sm leading-relaxed whitespace-pre-line" style={{ color: "var(--text-muted)" }}>
                    {faq.answer}
                  </p>
                </div>
              )}
            </div>
          );
        })}
      </div>

      <div className="mt-6 p-4 rounded-xl text-center" style={{ background: "var(--gray-light)" }}>
        <p className="text-sm font-bold" style={{ color: "var(--black)" }}>
          Still have questions?
        </p>
        <p className="text-xs mt-1" style={{ color: "var(--text-muted)" }}>
          Use the contact form above
          {branch?.phone && (
            <>
              {" "}or call us on{" "}
              <a href={`tel:${branch.phone}`} className="font-bold" style={{ color: "var(--red)" }}>
                {branch.phone}
              </a>
            </>
          )}
          .
        </p>
      </div>
    </div>
  );
}

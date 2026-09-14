"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Search, ChevronDown, MessageCircle, Phone, Mail, FileText, Loader2 } from "lucide-react";
import { loadFaq } from "@/lib/api/site";
import type { Faq } from "@/lib/api/types";
import { useSiteInfo } from "@/lib/site/useSiteInfo";

/**
 * Help, from the FAQ the team manages in the admin — the same answers the chat
 * assistant gives. The previous page hardcoded 25 answers, several wrong (a
 * ₦2,500 minimum, "free delivery over ₦10,000"), and a placeholder phone number.
 */
export default function HelpPage() {
  const { branch, settings } = useSiteInfo();
  const [faqs, setFaqs] = useState<Faq[] | null>(null);
  const [loadError, setLoadError] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [activeCategory, setActiveCategory] = useState("All");
  const [expandedFAQs, setExpandedFAQs] = useState<Set<string>>(new Set());

  useEffect(() => {
    let cancelled = false;
    loadFaq()
      .then((data) => !cancelled && setFaqs(data))
      .catch(() => !cancelled && setLoadError(true));
    return () => {
      cancelled = true;
    };
  }, []);

  const toggleFAQ = (id: string) => {
    const newExpanded = new Set(expandedFAQs);
    if (newExpanded.has(id)) {
      newExpanded.delete(id);
    } else {
      newExpanded.add(id);
    }
    setExpandedFAQs(newExpanded);
  };

  const all = faqs ?? [];
  const categories = ["All", ...Array.from(new Set(all.map((faq) => faq.category).filter(Boolean)))];
  const query = searchQuery.trim().toLowerCase();
  const filteredFAQs = all.filter((faq) => {
    const matchesCategory = activeCategory === "All" || faq.category === activeCategory;
    const matchesSearch = !query || faq.question.toLowerCase().includes(query) || faq.answer.toLowerCase().includes(query);
    return matchesCategory && matchesSearch;
  });

  const email = settings?.support_email || branch?.email;
  const quickLinks = [
    { icon: <FileText className="w-8 h-8" />, title: "Track Order", link: "/orders" },
    { icon: <MessageCircle className="w-8 h-8" />, title: "Contact Support", link: "/contact" },
    ...(branch?.phone ? [{ icon: <Phone className="w-8 h-8" />, title: "Call Us", link: `tel:${branch.phone}` }] : []),
    ...(email ? [{ icon: <Mail className="w-8 h-8" />, title: "Email Us", link: `mailto:${email}` }] : []),
  ];

  return (
    <div className="min-h-screen pt-20 sm:pt-24 pb-12" style={{ background: "var(--gray-light)" }}>
      {/* Hero Section */}
      <section className="py-16 bg-white">
        <div className="container-custom text-center max-w-3xl">
          <h1 className="font-black text-4xl sm:text-5xl mb-6" style={{ fontFamily: "var(--font-playfair)", color: "var(--black)" }}>
            How Can We Help?
          </h1>
          <p className="text-base sm:text-lg mb-8" style={{ color: "var(--text-muted)" }}>
            Find answers to common questions or get in touch with our support team
          </p>

          {/* Search Bar */}
          <div className="relative">
            <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5" style={{ color: "var(--text-muted)" }} />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search for answers..."
              aria-label="Search for answers"
              className="w-full pl-12 pr-4 py-4 rounded-full border-2 font-semibold text-base"
              style={{ borderColor: "var(--gray-mid)" }}
            />
          </div>
        </div>
      </section>

      <div className="container-custom">
        {/* Quick Links */}
        <section className="py-12">
          <div className={`grid sm:grid-cols-2 gap-6 ${quickLinks.length > 2 ? "lg:grid-cols-4" : ""}`}>
            {quickLinks.map((item) => (
              <a
                key={item.title}
                href={item.link}
                className="bg-white rounded-xl p-6 text-center transition-all hover:shadow-lg group"
                style={{ border: "2px solid var(--gray-mid)" }}
              >
                <div className="flex justify-center mb-3 transition-transform group-hover:scale-110" style={{ color: "var(--red)" }}>
                  {item.icon}
                </div>
                <h3 className="font-bold" style={{ color: "var(--black)" }}>
                  {item.title}
                </h3>
              </a>
            ))}
          </div>
        </section>

        {/* Category Filter */}
        {categories.length > 1 && (
          <section className="py-8">
            <div className="flex flex-wrap gap-3 justify-center">
              {categories.map((category) => (
                <button
                  key={category}
                  onClick={() => setActiveCategory(category)}
                  aria-pressed={activeCategory === category}
                  className="px-6 py-2 rounded-full font-bold text-sm transition-all hover:opacity-90"
                  style={{
                    background: activeCategory === category ? "var(--red)" : "var(--gray-light)",
                    color: activeCategory === category ? "white" : "var(--black)",
                  }}
                >
                  {category}
                </button>
              ))}
            </div>
          </section>
        )}

        {/* FAQ Accordion */}
        <section className="py-8">
          <div className="max-w-4xl mx-auto">
            <h2 className="font-black text-2xl sm:text-3xl mb-8 text-center" style={{ fontFamily: "var(--font-playfair)", color: "var(--black)" }}>
              Frequently Asked Questions
            </h2>

            {loadError ? (
              <p role="alert" className="text-center text-base" style={{ color: "var(--text-muted)" }}>
                We couldn&apos;t load the answers. Please check your connection and try again.
              </p>
            ) : faqs === null ? (
              <div className="flex justify-center" role="status" aria-label="Loading answers">
                <Loader2 className="w-6 h-6 animate-spin" style={{ color: "var(--red)" }} />
              </div>
            ) : filteredFAQs.length === 0 ? (
              <div className="bg-white rounded-xl p-12 text-center" style={{ border: "2px solid var(--gray-mid)" }}>
                <p className="text-lg" style={{ color: "var(--text-muted)" }}>
                  No results found. Try a different search term or category.
                </p>
              </div>
            ) : (
              <div className="space-y-4">
                {filteredFAQs.map((faq) => (
                  <div
                    key={faq.id}
                    className="bg-white rounded-xl overflow-hidden transition-all"
                    style={{ border: "2px solid var(--gray-mid)" }}
                  >
                    <button
                      onClick={() => toggleFAQ(faq.id)}
                      aria-expanded={expandedFAQs.has(faq.id)}
                      className="w-full px-6 py-5 flex items-center justify-between text-left hover:bg-gray-50 transition-colors"
                    >
                      <div className="flex-1">
                        {faq.category && (
                          <span className="text-xs font-bold mb-1 block" style={{ color: "var(--red)" }}>
                            {faq.category}
                          </span>
                        )}
                        <span className="font-bold text-base" style={{ color: "var(--black)" }}>
                          {faq.question}
                        </span>
                      </div>
                      <ChevronDown
                        className={`w-6 h-6 flex-shrink-0 ml-4 transition-transform ${expandedFAQs.has(faq.id) ? "rotate-180" : ""}`}
                        style={{ color: "var(--red)" }}
                      />
                    </button>

                    {expandedFAQs.has(faq.id) && (
                      <div className="px-6 pb-5">
                        <p className="text-base leading-relaxed whitespace-pre-line" style={{ color: "var(--text-muted)" }}>
                          {faq.answer}
                        </p>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        </section>

        {/* Still Need Help */}
        <section className="py-12">
          <div className="bg-white rounded-2xl p-8 sm:p-12 text-center max-w-3xl mx-auto">
            <h2 className="font-black text-2xl sm:text-3xl mb-4" style={{ fontFamily: "var(--font-playfair)", color: "var(--black)" }}>
              Still Need Help?
            </h2>
            <p className="text-base mb-8" style={{ color: "var(--text-muted)" }}>
              Send us a message and our team will reply by email, or use the chat button to reach us.
            </p>
            <div className="flex flex-wrap justify-center gap-4">
              <Link
                href="/contact"
                className="px-8 py-3 rounded-full font-bold text-white transition-all hover:opacity-90"
                style={{ background: "var(--red)" }}
              >
                Contact Support
              </Link>
              {branch?.phone && (
                <a
                  href={`tel:${branch.phone}`}
                  className="px-8 py-3 rounded-full font-bold transition-all hover:opacity-90"
                  style={{ background: "var(--black)", color: "white" }}
                >
                  Call Now
                </a>
              )}
            </div>
          </div>
        </section>

        {/* Popular Articles */}
        <section className="py-12">
          <h2 className="font-black text-2xl sm:text-3xl mb-8 text-center" style={{ fontFamily: "var(--font-playfair)", color: "var(--black)" }}>
            Popular Help Articles
          </h2>
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-6 max-w-5xl mx-auto">
            {[
              { title: "Track My Order", link: "/orders" },
              { title: "Book a Table", link: "/reservations" },
              { title: "Rewards Program Overview", link: "/rewards" },
              { title: "Catering Services Info", link: "/catering" },
              { title: "Refund & Cancellation Policy", link: "/refunds" },
              { title: "Privacy Policy", link: "/privacy" },
            ].map((article) => (
              <Link
                key={article.link}
                href={article.link}
                className="bg-white rounded-xl p-6 transition-all hover:shadow-lg group"
                style={{ border: "2px solid var(--gray-mid)" }}
              >
                <h3 className="font-bold text-base group-hover:text-red transition-colors" style={{ color: "var(--black)" }}>
                  {article.title}
                </h3>
              </Link>
            ))}
          </div>
        </section>
      </div>
    </div>
  );
}

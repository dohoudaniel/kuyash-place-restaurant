"use client";

import { useEffect, useRef, useState } from "react";
import { Check, Users, Clock, ChefHat, Phone, Mail, Loader2, CheckCircle, AlertCircle } from "lucide-react";
import { ApiError, api } from "@/lib/api/client";
import type { CateringPackage, EnquiryCreated } from "@/lib/api/types";
import { useSiteInfo } from "@/lib/site/useSiteInfo";

const inputClass = "w-full px-4 py-3 rounded-lg border font-semibold";

function localToday(): string {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-${String(now.getDate()).padStart(2, "0")}`;
}

/**
 * Catering packages and quote requests.
 *
 * The packages were hardcoded here, with prices computed by `toLocaleString()` on
 * a number, and the quote form ended in `alert()` and `console.log` — nobody
 * ever saw the request.
 */
export default function CateringPage() {
  const { branch, settings } = useSiteInfo();
  const formRef = useRef<HTMLElement>(null);
  const [packages, setPackages] = useState<CateringPackage[]>([]);
  const [packagesState, setPackagesState] = useState<"loading" | "ready" | "error">("loading");
  const [formData, setFormData] = useState({
    name: "",
    email: "",
    phone: "",
    eventType: "",
    eventDate: "",
    eventTime: "",
    guestCount: "",
    packageSlug: "",
    venue: "",
    message: "",
  });
  const [submitting, setSubmitting] = useState(false);
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [formError, setFormError] = useState<string | null>(null);
  const [enquiry, setEnquiry] = useState<EnquiryCreated | null>(null);

  useEffect(() => {
    let cancelled = false;
    api<CateringPackage[]>("/catering/packages/")
      .then((list) => {
        if (cancelled) return;
        setPackages(list);
        setPackagesState("ready");
      })
      .catch(() => !cancelled && setPackagesState("error"));
    return () => {
      cancelled = true;
    };
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setFieldErrors({});
    setFormError(null);
    try {
      const created = await api<EnquiryCreated>("/catering/enquiries/", {
        method: "POST",
        body: {
          name: formData.name.trim(),
          email: formData.email.trim(),
          phone: formData.phone.trim(),
          guest_count: Number(formData.guestCount),
          package: formData.packageSlug,
          event_type: formData.eventType,
          event_date: formData.eventDate || null,
          event_time: formData.eventTime || null,
          venue: formData.venue.trim(),
          message: formData.message.trim(),
        },
      });
      setEnquiry(created);
      formRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
    } catch (err) {
      if (err instanceof ApiError && err.code === "validation_error") setFieldErrors(err.fieldErrors);
      else setFormError(err instanceof ApiError ? err.message : "We couldn't send your request. Please try again.");
    } finally {
      setSubmitting(false);
    }
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const selectPackage = (slug: string) => {
    setFormData((current) => ({ ...current, packageSlug: slug }));
    formRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
  };

  const selected = packages.find((pkg) => pkg.slug === formData.packageSlug);
  const guestRange = packages.length
    ? `${Math.min(...packages.map((p) => p.min_guests))} - ${Math.max(...packages.map((p) => p.max_guests))} Guests`
    : null;
  const email = settings?.support_email || branch?.email || "";
  const errorFor = (name: string) =>
    fieldErrors[name] ? <p className="text-xs font-semibold mt-1" style={{ color: "var(--red)" }}>{fieldErrors[name]}</p> : null;
  const borderFor = (name: string) => ({ borderColor: fieldErrors[name] ? "var(--red)" : "var(--gray-mid)" });

  return (
    <div className="min-h-screen pt-20 sm:pt-24 pb-12" style={{ background: "var(--gray-light)" }}>
      {/* Hero Section */}
      <section className="py-16 sm:py-24" style={{ background: "var(--black)", color: "white" }}>
        <div className="container-custom text-center">
          <h1 className="font-black text-4xl sm:text-6xl mb-6" style={{ fontFamily: "var(--font-playfair)" }}>
            Catering Services
          </h1>
          <p className="text-lg sm:text-xl max-w-2xl mx-auto mb-8" style={{ color: "rgba(255,255,255,0.8)" }}>
            Bring the taste of Kuyash Place to your special event. From intimate gatherings to grand celebrations, we deliver exceptional Nigerian cuisine with impeccable service.
          </p>
          <div className="flex flex-wrap justify-center gap-8 text-sm">
            {guestRange && (
              <div className="flex items-center gap-2">
                <Users className="w-5 h-5" style={{ color: "var(--red)" }} />
                <span>{guestRange}</span>
              </div>
            )}
            <div className="flex items-center gap-2">
              <ChefHat className="w-5 h-5" style={{ color: "var(--red)" }} />
              <span>Professional Chefs</span>
            </div>
            <div className="flex items-center gap-2">
              <Clock className="w-5 h-5" style={{ color: "var(--red)" }} />
              <span>Reply Within 24 Hours</span>
            </div>
          </div>
        </div>
      </section>

      <div className="container-custom">
        {/* Packages Section */}
        <section className="py-12 sm:py-16">
          <div className="text-center mb-12">
            <h2 className="font-black text-3xl sm:text-4xl mb-4" style={{ fontFamily: "var(--font-playfair)", color: "var(--black)" }}>
              Catering Packages
            </h2>
            <p className="text-base sm:text-lg max-w-2xl mx-auto" style={{ color: "var(--text-muted)" }}>
              Choose a package that fits your event, or let us create a custom menu tailored to your needs.
            </p>
          </div>

          {packagesState === "loading" ? (
            <div className="flex items-center justify-center gap-2 py-12" role="status">
              <Loader2 className="w-5 h-5 animate-spin" style={{ color: "var(--red)" }} />
              <span className="text-sm" style={{ color: "var(--text-muted)" }}>Loading packages…</span>
            </div>
          ) : packagesState === "error" ? (
            <p role="alert" className="text-center py-12 text-sm" style={{ color: "var(--text-muted)" }}>
              We couldn&apos;t load our packages. You can still request a custom quote below.
            </p>
          ) : (
            <div className="grid md:grid-cols-3 gap-6 mb-12">
              {packages.map((pkg) => {
                const features = Array.isArray(pkg.features) ? (pkg.features as string[]) : [];
                const isChosen = formData.packageSlug === pkg.slug;
                return (
                  <div
                    key={pkg.slug}
                    className="bg-white rounded-2xl p-8 relative transition-all hover:shadow-2xl"
                    style={{
                      border: pkg.is_popular || isChosen ? "3px solid var(--red)" : "2px solid var(--gray-mid)",
                      transform: pkg.is_popular ? "scale(1.05)" : "scale(1)",
                    }}
                  >
                    {pkg.is_popular && (
                      <div className="absolute -top-4 left-1/2 -translate-x-1/2 px-6 py-1 rounded-full text-xs font-bold text-white" style={{ background: "var(--red)" }}>
                        MOST POPULAR
                      </div>
                    )}

                    <h3 className="font-black text-2xl mb-2" style={{ fontFamily: "var(--font-playfair)", color: "var(--black)" }}>
                      {pkg.name}
                    </h3>
                    <p className="text-sm mb-4" style={{ color: "var(--text-muted)" }}>
                      {pkg.description}
                    </p>

                    <div className="mb-6">
                      <div className="font-black text-4xl mb-2" style={{ fontFamily: "var(--font-playfair)", color: "var(--red)" }}>
                        {pkg.price_per_person?.display ?? "On request"}
                      </div>
                      <div className="text-xs" style={{ color: "var(--text-muted)" }}>
                        per person • {pkg.min_guests}-{pkg.max_guests} guests
                      </div>
                    </div>

                    <ul className="space-y-3 mb-8">
                      {features.map((feature) => (
                        <li key={feature} className="flex items-start gap-3 text-sm">
                          <Check className="w-5 h-5 flex-shrink-0 mt-0.5" style={{ color: "var(--red)" }} />
                          <span style={{ color: "var(--black)" }}>{feature}</span>
                        </li>
                      ))}
                    </ul>

                    <button
                      onClick={() => selectPackage(pkg.slug)}
                      aria-pressed={isChosen}
                      className="w-full py-3 rounded-full font-bold text-white transition-all hover:opacity-90"
                      style={{ background: pkg.is_popular || isChosen ? "var(--red)" : "var(--black)" }}
                    >
                      {isChosen ? "Selected" : "Select Package"}
                    </button>
                  </div>
                );
              })}
            </div>
          )}
        </section>

        {/* Event Types Section */}
        <section className="py-12 bg-white rounded-2xl px-8 mb-12">
          <h2 className="font-black text-3xl text-center mb-10" style={{ fontFamily: "var(--font-playfair)", color: "var(--black)" }}>
            Perfect For Any Occasion
          </h2>
          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-6">
            {[
              { icon: "💍", label: "Weddings" },
              { icon: "🎉", label: "Birthdays" },
              { icon: "💼", label: "Corporate Events" },
              { icon: "🎓", label: "Graduations" },
              { icon: "🏢", label: "Office Parties" },
              { icon: "🎊", label: "Anniversaries" },
              { icon: "🏠", label: "Private Dinners" },
              { icon: "🎪", label: "Festivals" },
            ].map((event) => (
              <div key={event.label} className="text-center p-6 rounded-xl transition-all hover:shadow-lg" style={{ background: "var(--cream)" }}>
                <div className="text-4xl mb-3" aria-hidden="true">{event.icon}</div>
                <div className="font-bold" style={{ color: "var(--black)" }}>{event.label}</div>
              </div>
            ))}
          </div>
        </section>

        {/* Quote Request Form */}
        <section ref={formRef} className="py-12 scroll-mt-24">
          <div className="max-w-3xl mx-auto bg-white rounded-2xl p-8 sm:p-12 shadow-sm">
            {enquiry ? (
              <div className="text-center">
                <div className="w-16 h-16 rounded-full flex items-center justify-center mx-auto mb-4" style={{ background: "#10b98115" }}>
                  <CheckCircle className="w-8 h-8" style={{ color: "#10b981" }} />
                </div>
                <h2 className="font-black text-3xl mb-2" style={{ fontFamily: "var(--font-playfair)", color: "var(--black)" }}>
                  Request received
                </h2>
                <p className="text-base mb-6" style={{ color: "var(--text-muted)" }}>
                  Reference <strong style={{ color: "var(--black)" }}>{enquiry.reference}</strong>. Our catering team will reply to{" "}
                  {enquiry.email} by{" "}
                  <strong style={{ color: "var(--black)" }}>
                    {new Date(enquiry.respond_by).toLocaleString("en-NG", { weekday: "long", hour: "numeric", minute: "2-digit" })}
                  </strong>
                  .
                </p>
                {enquiry.indicative_total && (
                  <div className="p-4 rounded-xl mb-6 text-left" style={{ background: "var(--gray-light)" }}>
                    <p className="text-sm font-bold" style={{ color: "var(--black)" }}>
                      Indicative total: {enquiry.indicative_total.display}
                      {enquiry.package_name ? ` (${enquiry.package_name}, ${enquiry.guest_count} guests)` : ""}
                    </p>
                    {enquiry.indicative_note && (
                      <p className="text-xs mt-1" style={{ color: "var(--text-muted)" }}>{enquiry.indicative_note}</p>
                    )}
                  </div>
                )}
                <button
                  onClick={() => setEnquiry(null)}
                  className="px-8 py-3 rounded-full font-bold text-sm"
                  style={{ border: "2px solid var(--gray-mid)", color: "var(--black)" }}
                >
                  Send Another Request
                </button>
              </div>
            ) : (
              <>
                <div className="text-center mb-8">
                  <h2 className="font-black text-3xl sm:text-4xl mb-4" style={{ fontFamily: "var(--font-playfair)", color: "var(--black)" }}>
                    Request a Quote
                  </h2>
                  <p className="text-base" style={{ color: "var(--text-muted)" }}>
                    Tell us about your event and we&apos;ll create a personalized proposal within 24 hours.
                  </p>
                </div>

                <form onSubmit={handleSubmit} className="space-y-6">
                  <div className="grid sm:grid-cols-2 gap-6">
                    <div>
                      <label htmlFor="catering-name" className="block text-sm font-bold mb-2" style={{ color: "var(--black)" }}>Full Name *</label>
                      <input id="catering-name" type="text" name="name" autoComplete="name" value={formData.name} onChange={handleChange} required className={inputClass} style={borderFor("name")} placeholder="John Doe" />
                      {errorFor("name")}
                    </div>
                    <div>
                      <label htmlFor="catering-email" className="block text-sm font-bold mb-2" style={{ color: "var(--black)" }}>Email Address *</label>
                      <input id="catering-email" type="email" name="email" autoComplete="email" value={formData.email} onChange={handleChange} required className={inputClass} style={borderFor("email")} placeholder="john@example.com" />
                      {errorFor("email")}
                    </div>
                  </div>

                  <div className="grid sm:grid-cols-2 gap-6">
                    <div>
                      <label htmlFor="catering-phone" className="block text-sm font-bold mb-2" style={{ color: "var(--black)" }}>Phone Number *</label>
                      <input id="catering-phone" type="tel" name="phone" autoComplete="tel" value={formData.phone} onChange={handleChange} required className={inputClass} style={borderFor("phone")} placeholder="+234 123 456 7890" />
                      {errorFor("phone")}
                    </div>
                    <div>
                      <label htmlFor="catering-event-type" className="block text-sm font-bold mb-2" style={{ color: "var(--black)" }}>Event Type *</label>
                      <select id="catering-event-type" name="eventType" value={formData.eventType} onChange={handleChange} required className={inputClass} style={borderFor("event_type")}>
                        <option value="">Select event type</option>
                        <option value="Wedding">Wedding</option>
                        <option value="Birthday">Birthday</option>
                        <option value="Corporate event">Corporate Event</option>
                        <option value="Graduation">Graduation</option>
                        <option value="Anniversary">Anniversary</option>
                        <option value="Other">Other</option>
                      </select>
                      {errorFor("event_type")}
                    </div>
                  </div>

                  <div className="grid sm:grid-cols-3 gap-6">
                    <div>
                      <label htmlFor="catering-date" className="block text-sm font-bold mb-2" style={{ color: "var(--black)" }}>Event Date *</label>
                      <input id="catering-date" type="date" name="eventDate" value={formData.eventDate} onChange={handleChange} required min={localToday()} className={inputClass} style={borderFor("event_date")} />
                      {errorFor("event_date")}
                    </div>
                    <div>
                      <label htmlFor="catering-time" className="block text-sm font-bold mb-2" style={{ color: "var(--black)" }}>Start Time</label>
                      <input id="catering-time" type="time" name="eventTime" value={formData.eventTime} onChange={handleChange} className={inputClass} style={borderFor("event_time")} />
                      {errorFor("event_time")}
                    </div>
                    <div>
                      <label htmlFor="catering-guests" className="block text-sm font-bold mb-2" style={{ color: "var(--black)" }}>Number of Guests *</label>
                      <input id="catering-guests" type="number" name="guestCount" value={formData.guestCount} onChange={handleChange} required min={1} max={5000} className={inputClass} style={borderFor("guest_count")} placeholder="50" />
                      {errorFor("guest_count")}
                    </div>
                  </div>

                  <div>
                    <label htmlFor="catering-package" className="block text-sm font-bold mb-2" style={{ color: "var(--black)" }}>Preferred Package</label>
                    <select id="catering-package" name="packageSlug" value={formData.packageSlug} onChange={handleChange} className={inputClass} style={borderFor("package")}>
                      <option value="">Not sure yet / custom menu</option>
                      {packages.map((pkg) => (
                        <option key={pkg.slug} value={pkg.slug}>{pkg.name} Package</option>
                      ))}
                    </select>
                    {selected && formData.guestCount && (Number(formData.guestCount) < selected.min_guests || Number(formData.guestCount) > selected.max_guests) && (
                      <p className="text-xs mt-1 flex items-center gap-1" style={{ color: "#b45309" }}>
                        <AlertCircle className="w-3.5 h-3.5" />
                        {selected.name} is designed for {selected.min_guests}–{selected.max_guests} guests — we&apos;ll suggest the best fit.
                      </p>
                    )}
                    {errorFor("package")}
                  </div>

                  <div>
                    <label htmlFor="catering-venue" className="block text-sm font-bold mb-2" style={{ color: "var(--black)" }}>Venue/Location *</label>
                    <input id="catering-venue" type="text" name="venue" value={formData.venue} onChange={handleChange} required className={inputClass} style={borderFor("venue")} placeholder="Event venue or address" />
                    {errorFor("venue")}
                  </div>

                  <div>
                    <label htmlFor="catering-message" className="block text-sm font-bold mb-2" style={{ color: "var(--black)" }}>Additional Details</label>
                    <textarea id="catering-message" name="message" value={formData.message} onChange={handleChange} rows={4} maxLength={2000} className={`${inputClass} resize-none`} style={borderFor("message")} placeholder="Special requests, dietary restrictions, menu preferences, etc." />
                    {errorFor("message")}
                  </div>

                  {formError && <p role="alert" className="text-sm font-semibold" style={{ color: "var(--red)" }}>{formError}</p>}

                  <button
                    type="submit"
                    disabled={submitting}
                    className="w-full py-4 rounded-full font-bold text-white text-lg flex items-center justify-center gap-2 transition-all hover:opacity-90 disabled:opacity-50"
                    style={{ background: "var(--red)" }}
                  >
                    {submitting && <Loader2 className="w-5 h-5 animate-spin" />}
                    {submitting ? "Sending..." : "Request Free Quote"}
                  </button>

                  <p className="text-xs text-center" style={{ color: "var(--text-muted)" }}>
                    We&apos;ll review your request and send a detailed quote within 24 hours. No commitment required.
                  </p>
                </form>
              </>
            )}
          </div>
        </section>

        {/* Contact CTA */}
        {(branch?.phone || email) && (
          <section className="py-12">
            <div className="bg-white rounded-2xl p-8 sm:p-12 text-center">
              <h2 className="font-black text-2xl sm:text-3xl mb-4" style={{ fontFamily: "var(--font-playfair)", color: "var(--black)" }}>
                Have Questions?
              </h2>
              <p className="text-base mb-8 max-w-2xl mx-auto" style={{ color: "var(--text-muted)" }}>
                Our catering team is here to help plan your perfect event. Contact us for personalized assistance.
              </p>
              <div className="flex flex-wrap justify-center gap-6">
                {branch?.phone && (
                  <a href={`tel:${branch.phone}`} className="flex items-center gap-3 px-8 py-4 rounded-full font-bold text-white transition-all hover:opacity-90" style={{ background: "var(--red)" }}>
                    <Phone className="w-5 h-5" />
                    Call Us
                  </a>
                )}
                {email && (
                  <a href={`mailto:${email}?subject=Catering`} className="flex items-center gap-3 px-8 py-4 rounded-full font-bold transition-all hover:opacity-90" style={{ background: "var(--black)", color: "white" }}>
                    <Mail className="w-5 h-5" />
                    Email Us
                  </a>
                )}
              </div>
            </div>
          </section>
        )}
      </div>
    </div>
  );
}

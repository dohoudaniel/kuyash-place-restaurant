"use client";

import ContactHero from "@/components/features/contact/ContactHero";
import ContactForm from "@/components/features/contact/ContactForm";
import ContactInfo from "@/components/features/contact/ContactInfo";
import MapSection from "@/components/features/contact/MapSection";
import FAQSection from "@/components/features/contact/FAQSection";

export default function ContactPage() {
  return (
    <div className="min-h-screen pt-20 sm:pt-24" style={{ background: "var(--gray-light)" }}>
      <ContactHero />

      <div className="container-custom py-6 sm:py-8">
        {/* Contact Form + Info Grid */}
        <div className="grid lg:grid-cols-3 gap-6 mb-8">
          <div className="lg:col-span-2">
            <ContactForm />
          </div>
          <div className="lg:col-span-1">
            <ContactInfo />
          </div>
        </div>

        {/* Map */}
        <MapSection />

        {/* FAQ */}
        <FAQSection />
      </div>
    </div>
  );
}

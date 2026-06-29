"use client";

import { useState } from "react";
import { Check, Users, Calendar, Clock, ChefHat, Utensils, MessageSquare, Phone, Mail } from "lucide-react";

interface CateringPackage {
  id: string;
  name: string;
  description: string;
  minGuests: number;
  maxGuests: number;
  pricePerPerson: number;
  features: string[];
  popular?: boolean;
}

const CATERING_PACKAGES: CateringPackage[] = [
  {
    id: "basic",
    name: "Essential",
    description: "Perfect for small gatherings and casual events",
    minGuests: 10,
    maxGuests: 30,
    pricePerPerson: 3500,
    features: [
      "2 Main Dishes (choice of Nigerian classics)",
      "1 Side Dish",
      "Soft Drinks & Water",
      "Basic Setup & Cleanup",
      "Disposable Plates & Cutlery",
    ],
  },
  {
    id: "premium",
    name: "Premium",
    description: "Ideal for corporate events and special occasions",
    minGuests: 30,
    maxGuests: 100,
    pricePerPerson: 6500,
    features: [
      "4 Main Dishes (premium selection)",
      "3 Side Dishes",
      "Appetizers & Small Chops",
      "Soft Drinks, Juice & Water",
      "Professional Serving Staff",
      "China Plates & Silverware",
      "Elegant Table Setup",
      "Full Cleanup Service",
    ],
    popular: true,
  },
  {
    id: "luxury",
    name: "Luxury",
    description: "Ultimate experience for weddings and galas",
    minGuests: 100,
    maxGuests: 500,
    pricePerPerson: 12000,
    features: [
      "6+ Main Dishes (gourmet selection)",
      "5 Side Dishes",
      "Premium Appetizers & Canapés",
      "Full Beverage Service (non-alcoholic)",
      "Live Cooking Stations",
      "Professional Chefs & Waitstaff",
      "Premium Tableware & Linens",
      "Event Coordination",
      "Custom Menu Design",
      "Decorative Food Presentation",
    ],
  },
];

export default function CateringPage() {
  const [formData, setFormData] = useState({
    name: "",
    email: "",
    phone: "",
    eventType: "",
    eventDate: "",
    guestCount: "",
    packageId: "",
    venue: "",
    message: "",
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    alert("Thank you! We'll contact you within 24 hours with a detailed quote.");
    console.log("Catering Quote Request:", formData);
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

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
            <div className="flex items-center gap-2">
              <Users className="w-5 h-5" style={{ color: "var(--red)" }} />
              <span>10 - 500 Guests</span>
            </div>
            <div className="flex items-center gap-2">
              <ChefHat className="w-5 h-5" style={{ color: "var(--red)" }} />
              <span>Professional Chefs</span>
            </div>
            <div className="flex items-center gap-2">
              <Clock className="w-5 h-5" style={{ color: "var(--red)" }} />
              <span>Full Service</span>
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

          <div className="grid md:grid-cols-3 gap-6 mb-12">
            {CATERING_PACKAGES.map((pkg) => (
              <div
                key={pkg.id}
                className="bg-white rounded-2xl p-8 relative transition-all hover:shadow-2xl"
                style={{
                  border: pkg.popular ? "3px solid var(--red)" : "2px solid var(--gray-mid)",
                  transform: pkg.popular ? "scale(1.05)" : "scale(1)",
                }}
              >
                {pkg.popular && (
                  <div
                    className="absolute -top-4 left-1/2 -translate-x-1/2 px-6 py-1 rounded-full text-xs font-bold text-white"
                    style={{ background: "var(--red)" }}
                  >
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
                    ₦{pkg.pricePerPerson.toLocaleString()}
                  </div>
                  <div className="text-xs" style={{ color: "var(--text-muted)" }}>
                    per person • {pkg.minGuests}-{pkg.maxGuests} guests
                  </div>
                </div>

                <ul className="space-y-3 mb-8">
                  {pkg.features.map((feature, idx) => (
                    <li key={idx} className="flex items-start gap-3 text-sm">
                      <Check className="w-5 h-5 flex-shrink-0 mt-0.5" style={{ color: "var(--red)" }} />
                      <span style={{ color: "var(--black)" }}>{feature}</span>
                    </li>
                  ))}
                </ul>

                <button
                  onClick={() => setFormData({ ...formData, packageId: pkg.id })}
                  className="w-full py-3 rounded-full font-bold text-white transition-all hover:opacity-90"
                  style={{ background: pkg.popular ? "var(--red)" : "var(--black)" }}
                >
                  Select Package
                </button>
              </div>
            ))}
          </div>
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
            ].map((event, idx) => (
              <div
                key={idx}
                className="text-center p-6 rounded-xl transition-all hover:shadow-lg"
                style={{ background: "var(--cream)" }}
              >
                <div className="text-4xl mb-3">{event.icon}</div>
                <div className="font-bold" style={{ color: "var(--black)" }}>{event.label}</div>
              </div>
            ))}
          </div>
        </section>

        {/* Quote Request Form */}
        <section className="py-12">
          <div className="max-w-3xl mx-auto bg-white rounded-2xl p-8 sm:p-12 shadow-sm">
            <div className="text-center mb-8">
              <h2 className="font-black text-3xl sm:text-4xl mb-4" style={{ fontFamily: "var(--font-playfair)", color: "var(--black)" }}>
                Request a Quote
              </h2>
              <p className="text-base" style={{ color: "var(--text-muted)" }}>
                Tell us about your event and we'll create a personalized proposal within 24 hours.
              </p>
            </div>

            <form onSubmit={handleSubmit} className="space-y-6">
              <div className="grid sm:grid-cols-2 gap-6">
                <div>
                  <label className="block text-sm font-bold mb-2" style={{ color: "var(--black)" }}>
                    Full Name *
                  </label>
                  <input
                    type="text"
                    name="name"
                    value={formData.name}
                    onChange={handleChange}
                    required
                    className="w-full px-4 py-3 rounded-lg border font-semibold"
                    style={{ borderColor: "var(--gray-mid)" }}
                    placeholder="John Doe"
                  />
                </div>

                <div>
                  <label className="block text-sm font-bold mb-2" style={{ color: "var(--black)" }}>
                    Email Address *
                  </label>
                  <input
                    type="email"
                    name="email"
                    value={formData.email}
                    onChange={handleChange}
                    required
                    className="w-full px-4 py-3 rounded-lg border font-semibold"
                    style={{ borderColor: "var(--gray-mid)" }}
                    placeholder="john@example.com"
                  />
                </div>
              </div>

              <div className="grid sm:grid-cols-2 gap-6">
                <div>
                  <label className="block text-sm font-bold mb-2" style={{ color: "var(--black)" }}>
                    Phone Number *
                  </label>
                  <input
                    type="tel"
                    name="phone"
                    value={formData.phone}
                    onChange={handleChange}
                    required
                    className="w-full px-4 py-3 rounded-lg border font-semibold"
                    style={{ borderColor: "var(--gray-mid)" }}
                    placeholder="+234 123 456 7890"
                  />
                </div>

                <div>
                  <label className="block text-sm font-bold mb-2" style={{ color: "var(--black)" }}>
                    Event Type *
                  </label>
                  <select
                    name="eventType"
                    value={formData.eventType}
                    onChange={handleChange}
                    required
                    className="w-full px-4 py-3 rounded-lg border font-semibold"
                    style={{ borderColor: "var(--gray-mid)" }}
                  >
                    <option value="">Select event type</option>
                    <option value="wedding">Wedding</option>
                    <option value="birthday">Birthday</option>
                    <option value="corporate">Corporate Event</option>
                    <option value="graduation">Graduation</option>
                    <option value="anniversary">Anniversary</option>
                    <option value="other">Other</option>
                  </select>
                </div>
              </div>

              <div className="grid sm:grid-cols-2 gap-6">
                <div>
                  <label className="block text-sm font-bold mb-2" style={{ color: "var(--black)" }}>
                    Event Date *
                  </label>
                  <input
                    type="date"
                    name="eventDate"
                    value={formData.eventDate}
                    onChange={handleChange}
                    required
                    min={new Date().toISOString().split("T")[0]}
                    className="w-full px-4 py-3 rounded-lg border font-semibold"
                    style={{ borderColor: "var(--gray-mid)" }}
                  />
                </div>

                <div>
                  <label className="block text-sm font-bold mb-2" style={{ color: "var(--black)" }}>
                    Number of Guests *
                  </label>
                  <input
                    type="number"
                    name="guestCount"
                    value={formData.guestCount}
                    onChange={handleChange}
                    required
                    min="10"
                    className="w-full px-4 py-3 rounded-lg border font-semibold"
                    style={{ borderColor: "var(--gray-mid)" }}
                    placeholder="50"
                  />
                </div>
              </div>

              <div>
                <label className="block text-sm font-bold mb-2" style={{ color: "var(--black)" }}>
                  Preferred Package
                </label>
                <select
                  name="packageId"
                  value={formData.packageId}
                  onChange={handleChange}
                  className="w-full px-4 py-3 rounded-lg border font-semibold"
                  style={{ borderColor: "var(--gray-mid)" }}
                >
                  <option value="">Not sure yet</option>
                  <option value="basic">Essential Package</option>
                  <option value="premium">Premium Package</option>
                  <option value="luxury">Luxury Package</option>
                  <option value="custom">Custom Package</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-bold mb-2" style={{ color: "var(--black)" }}>
                  Venue/Location *
                </label>
                <input
                  type="text"
                  name="venue"
                  value={formData.venue}
                  onChange={handleChange}
                  required
                  className="w-full px-4 py-3 rounded-lg border font-semibold"
                  style={{ borderColor: "var(--gray-mid)" }}
                  placeholder="Event venue or address"
                />
              </div>

              <div>
                <label className="block text-sm font-bold mb-2" style={{ color: "var(--black)" }}>
                  Additional Details
                </label>
                <textarea
                  name="message"
                  value={formData.message}
                  onChange={handleChange}
                  rows={4}
                  className="w-full px-4 py-3 rounded-lg border font-semibold resize-none"
                  style={{ borderColor: "var(--gray-mid)" }}
                  placeholder="Special requests, dietary restrictions, menu preferences, etc."
                />
              </div>

              <button
                type="submit"
                className="w-full py-4 rounded-full font-bold text-white text-lg transition-all hover:opacity-90"
                style={{ background: "var(--red)" }}
              >
                Request Free Quote
              </button>

              <p className="text-xs text-center" style={{ color: "var(--text-muted)" }}>
                We'll review your request and send a detailed quote within 24 hours. No commitment required.
              </p>
            </form>
          </div>
        </section>

        {/* Contact CTA */}
        <section className="py-12">
          <div className="bg-white rounded-2xl p-8 sm:p-12 text-center">
            <h2 className="font-black text-2xl sm:text-3xl mb-4" style={{ fontFamily: "var(--font-playfair)", color: "var(--black)" }}>
              Have Questions?
            </h2>
            <p className="text-base mb-8 max-w-2xl mx-auto" style={{ color: "var(--text-muted)" }}>
              Our catering team is here to help plan your perfect event. Contact us for personalized assistance.
            </p>
            <div className="flex flex-wrap justify-center gap-6">
              <a
                href="tel:+2341234567890"
                className="flex items-center gap-3 px-8 py-4 rounded-full font-bold text-white transition-all hover:opacity-90"
                style={{ background: "var(--red)" }}
              >
                <Phone className="w-5 h-5" />
                Call Us
              </a>
              <a
                href="mailto:catering@kuyashplace.com"
                className="flex items-center gap-3 px-8 py-4 rounded-full font-bold transition-all hover:opacity-90"
                style={{ background: "var(--black)", color: "white" }}
              >
                <Mail className="w-5 h-5" />
                Email Us
              </a>
            </div>
          </div>
        </section>
      </div>
    </div>
  );
}

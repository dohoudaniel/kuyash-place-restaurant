"use client";

import { useState } from "react";
import { Search, ChevronDown, MessageCircle, Phone, Mail, FileText } from "lucide-react";

interface FAQItem {
  category: string;
  question: string;
  answer: string;
}

const FAQ_DATA: FAQItem[] = [
  // Ordering
  {
    category: "Ordering",
    question: "How do I place an online order?",
    answer: "Browse our menu, select items, customize as needed, add to cart, and checkout. You'll receive an order confirmation via email and SMS.",
  },
  {
    category: "Ordering",
    question: "What are your minimum order requirements?",
    answer: "For delivery, the minimum order is ₦2,500. For pickup, there's no minimum. Catering orders have a 10-person minimum.",
  },
  {
    category: "Ordering",
    question: "Can I schedule an order for later?",
    answer: "Yes! During checkout, select 'Schedule for later' and choose your preferred date and time (up to 7 days in advance).",
  },
  {
    category: "Ordering",
    question: "How do I modify or cancel my order?",
    answer: "Log into your account, go to Orders, and select the order. You can cancel within 5 minutes or before preparation begins. For modifications, contact us immediately.",
  },

  // Delivery
  {
    category: "Delivery",
    question: "What are your delivery hours?",
    answer: "We deliver daily from 11:00 AM to 10:00 PM. Orders placed close to closing time may be scheduled for the next day.",
  },
  {
    category: "Delivery",
    question: "How much does delivery cost?",
    answer: "Delivery fees range from ₦500 to ₦1,500 depending on your location. Free delivery on orders over ₦10,000.",
  },
  {
    category: "Delivery",
    question: "How long does delivery take?",
    answer: "Typical delivery time is 30-45 minutes. You'll receive real-time updates on your order status.",
  },
  {
    category: "Delivery",
    question: "Do you deliver to my area?",
    answer: "Enter your address during checkout to see if we deliver to your location. We cover most areas in Lagos.",
  },

  // Payment
  {
    category: "Payment",
    question: "What payment methods do you accept?",
    answer: "We accept credit/debit cards (Visa, Mastercard), bank transfers, USSD, and cash on delivery (for select areas).",
  },
  {
    category: "Payment",
    question: "Is my payment information secure?",
    answer: "Yes! All transactions are encrypted using industry-standard SSL technology. We don't store your complete card details.",
  },
  {
    category: "Payment",
    question: "Can I pay with multiple payment methods?",
    answer: "Currently, each order must be paid with a single payment method. However, you can use rewards points along with any payment method.",
  },
  {
    category: "Payment",
    question: "Do you accept cash on delivery?",
    answer: "Cash on delivery is available for select areas. This option will show during checkout if available for your location.",
  },

  // Reservations
  {
    category: "Reservations",
    question: "How far in advance can I make a reservation?",
    answer: "You can make reservations up to 30 days in advance. For large parties (8+ people), we recommend booking at least 72 hours ahead.",
  },
  {
    category: "Reservations",
    question: "Can I request a specific table?",
    answer: "Yes! Add your seating preference in the special requests section. We'll do our best to accommodate, though we can't guarantee specific tables.",
  },
  {
    category: "Reservations",
    question: "What's your cancellation policy for reservations?",
    answer: "Free cancellation with 2+ hours notice. No-shows or late cancellations for large parties may incur a ₦5,000 fee.",
  },
  {
    category: "Reservations",
    question: "Do you accommodate large groups?",
    answer: "Absolutely! We can accommodate groups up to 50 people. For parties of 15+, please contact our events team for special arrangements.",
  },

  // Menu & Dietary
  {
    category: "Menu & Dietary",
    question: "Do you offer vegetarian/vegan options?",
    answer: "Yes! Our menu has several vegetarian options, and we can modify many dishes to be vegan. Look for the dietary icons on our menu.",
  },
  {
    category: "Menu & Dietary",
    question: "How do I know about allergens in your food?",
    answer: "Each menu item includes allergen information. Click on any dish for detailed ingredients. Always inform staff of allergies when ordering.",
  },
  {
    category: "Menu & Dietary",
    question: "Can you customize menu items?",
    answer: "Yes! Most items can be customized. Use the customization options when ordering online, or ask your server for dine-in orders.",
  },
  {
    category: "Menu & Dietary",
    question: "Do menu prices include VAT?",
    answer: "Yes, all displayed prices include applicable taxes. The price you see is the price you pay (plus delivery if applicable).",
  },

  // Rewards Program
  {
    category: "Rewards",
    question: "How do I join the rewards program?",
    answer: "Simply create an account! You're automatically enrolled and start earning points from your first order.",
  },
  {
    category: "Rewards",
    question: "Do my rewards points expire?",
    answer: "Points expire after 12 months of account inactivity. Place at least one order per year to keep your points active.",
  },
  {
    category: "Rewards",
    question: "Can I use points and promo codes together?",
    answer: "Yes! You can combine reward points with most promotional offers unless specifically stated otherwise.",
  },

  // Account
  {
    category: "Account",
    question: "I forgot my password. How do I reset it?",
    answer: "Click 'Login', then 'Forgot Password'. Enter your email and we'll send reset instructions. Check your spam folder if you don't see it.",
  },
  {
    category: "Account",
    question: "How do I update my delivery address?",
    answer: "Go to Account > Addresses. You can add, edit, or delete saved addresses. Set your default address for faster checkout.",
  },
  {
    category: "Account",
    question: "Can I have multiple accounts?",
    answer: "Each email can only have one account. However, you can save multiple delivery addresses under one account.",
  },
];

const CATEGORIES = ["All", "Ordering", "Delivery", "Payment", "Reservations", "Menu & Dietary", "Rewards", "Account"];

export default function HelpPage() {
  const [searchQuery, setSearchQuery] = useState("");
  const [activeCategory, setActiveCategory] = useState("All");
  const [expandedFAQs, setExpandedFAQs] = useState<Set<number>>(new Set());

  const toggleFAQ = (index: number) => {
    const newExpanded = new Set(expandedFAQs);
    if (newExpanded.has(index)) {
      newExpanded.delete(index);
    } else {
      newExpanded.add(index);
    }
    setExpandedFAQs(newExpanded);
  };

  const filteredFAQs = FAQ_DATA.filter((faq) => {
    const matchesCategory = activeCategory === "All" || faq.category === activeCategory;
    const matchesSearch =
      searchQuery === "" ||
      faq.question.toLowerCase().includes(searchQuery.toLowerCase()) ||
      faq.answer.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesCategory && matchesSearch;
  });

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
              className="w-full pl-12 pr-4 py-4 rounded-full border-2 font-semibold text-base"
              style={{ borderColor: "var(--gray-mid)" }}
            />
          </div>
        </div>
      </section>

      <div className="container-custom">
        {/* Quick Links */}
        <section className="py-12">
          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-6">
            {[
              { icon: <FileText className="w-8 h-8" />, title: "Track Order", link: "/orders" },
              { icon: <MessageCircle className="w-8 h-8" />, title: "Contact Support", link: "/contact" },
              { icon: <Phone className="w-8 h-8" />, title: "Call Us", link: "tel:+2341234567890" },
              { icon: <Mail className="w-8 h-8" />, title: "Email Us", link: "mailto:support@kuyashplace.com" },
            ].map((item, idx) => (
              <a
                key={idx}
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
        <section className="py-8">
          <div className="flex flex-wrap gap-3 justify-center">
            {CATEGORIES.map((category) => (
              <button
                key={category}
                onClick={() => setActiveCategory(category)}
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

        {/* FAQ Accordion */}
        <section className="py-8">
          <div className="max-w-4xl mx-auto">
            <h2 className="font-black text-2xl sm:text-3xl mb-8 text-center" style={{ fontFamily: "var(--font-playfair)", color: "var(--black)" }}>
              Frequently Asked Questions
            </h2>

            {filteredFAQs.length === 0 ? (
              <div className="bg-white rounded-xl p-12 text-center" style={{ border: "2px solid var(--gray-mid)" }}>
                <p className="text-lg" style={{ color: "var(--text-muted)" }}>
                  No results found. Try a different search term or category.
                </p>
              </div>
            ) : (
              <div className="space-y-4">
                {filteredFAQs.map((faq, index) => (
                  <div
                    key={index}
                    className="bg-white rounded-xl overflow-hidden transition-all"
                    style={{ border: "2px solid var(--gray-mid)" }}
                  >
                    <button
                      onClick={() => toggleFAQ(index)}
                      className="w-full px-6 py-5 flex items-center justify-between text-left hover:bg-gray-50 transition-colors"
                    >
                      <div className="flex-1">
                        <span className="text-xs font-bold mb-1 block" style={{ color: "var(--red)" }}>
                          {faq.category}
                        </span>
                        <span className="font-bold text-base" style={{ color: "var(--black)" }}>
                          {faq.question}
                        </span>
                      </div>
                      <ChevronDown
                        className={`w-6 h-6 flex-shrink-0 ml-4 transition-transform ${
                          expandedFAQs.has(index) ? "rotate-180" : ""
                        }`}
                        style={{ color: "var(--red)" }}
                      />
                    </button>

                    {expandedFAQs.has(index) && (
                      <div className="px-6 pb-5">
                        <p className="text-base leading-relaxed" style={{ color: "var(--text-muted)" }}>
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
              Our friendly support team is here to assist you. We typically respond within 2 hours during business hours.
            </p>
            <div className="flex flex-wrap justify-center gap-4">
              <a
                href="/contact"
                className="px-8 py-3 rounded-full font-bold text-white transition-all hover:opacity-90"
                style={{ background: "var(--red)" }}
              >
                Contact Support
              </a>
              <a
                href="tel:+2341234567890"
                className="px-8 py-3 rounded-full font-bold transition-all hover:opacity-90"
                style={{ background: "var(--black)", color: "white" }}
              >
                Call Now
              </a>
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
              { title: "How to Track My Order", link: "/help#track-order" },
              { title: "Payment Methods Guide", link: "/help#payment" },
              { title: "Delivery Areas & Fees", link: "/help#delivery" },
              { title: "Rewards Program Overview", link: "/rewards" },
              { title: "Catering Services Info", link: "/catering" },
              { title: "Refund & Cancellation Policy", link: "/refunds" },
            ].map((article, idx) => (
              <a
                key={idx}
                href={article.link}
                className="bg-white rounded-xl p-6 transition-all hover:shadow-lg group"
                style={{ border: "2px solid var(--gray-mid)" }}
              >
                <h3 className="font-bold text-base group-hover:text-red transition-colors" style={{ color: "var(--black)" }}>
                  {article.title} →
                </h3>
              </a>
            ))}
          </div>
        </section>
      </div>
    </div>
  );
}

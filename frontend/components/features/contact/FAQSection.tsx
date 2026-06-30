"use client";

import { useState } from "react";
import { ChevronDown, HelpCircle } from "lucide-react";

export default function FAQSection() {
  const [openIndex, setOpenIndex] = useState<number | null>(0);

  const faqs = [
    {
      question: "Do I need a reservation?",
      answer: "While walk-ins are welcome, we highly recommend making a reservation, especially for dinner service and weekends. You can book online or call us directly.",
    },
    {
      question: "What are your operating hours?",
      answer: "We're open 7 days a week from 11:00 AM to 10:00 PM. Last orders are taken at 9:30 PM. We're closed on major public holidays.",
    },
    {
      question: "Do you offer catering services?",
      answer: "Yes! We provide catering for events of all sizes, from intimate gatherings to large corporate events. Contact us for a customized menu and quote.",
    },
    {
      question: "Is parking available?",
      answer: "We have a secure parking facility that can accommodate up to 50 vehicles. Valet parking is available during peak hours at no extra charge.",
    },
    {
      question: "Do you accommodate dietary restrictions?",
      answer: "Absolutely! We cater to vegetarian, vegan, gluten-free, and other dietary needs. Please inform us when making your reservation or ordering.",
    },
    {
      question: "Can I host private events?",
      answer: "Yes, we have a dedicated private dining room that seats up to 30 guests. Perfect for birthdays, anniversaries, and business meetings.",
    },
    {
      question: "Do you offer delivery?",
      answer: "Yes, we offer delivery within Lagos through our online ordering platform and partner delivery services. Standard delivery takes 30-45 minutes.",
    },
    {
      question: "What payment methods do you accept?",
      answer: "We accept cash, all major credit/debit cards, bank transfers, and mobile payments (Paystack, Flutterwave). No checks, please.",
    },
  ];

  return (
    <div className="bg-white rounded-xl border p-6 sm:p-8" style={{ borderColor: "var(--gray-mid)" }}>
      <div className="flex items-center gap-3 mb-6">
        <div className="w-12 h-12 rounded-full flex items-center justify-center" style={{ background: "var(--red)15" }}>
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
          return (
            <div
              key={idx}
              className="rounded-xl border transition-all"
              style={{ borderColor: isOpen ? "var(--red)" : "var(--gray-mid)", background: isOpen ? "var(--red)05" : "white" }}
            >
              <button
                onClick={() => setOpenIndex(isOpen ? null : idx)}
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
                <div className="px-4 pb-4">
                  <p className="text-sm leading-relaxed" style={{ color: "var(--text-muted)" }}>
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
          Feel free to reach out via the contact form above or call us directly at{" "}
          <span className="font-bold" style={{ color: "var(--red)" }}>
            +234 123 456 7890
          </span>
        </p>
      </div>
    </div>
  );
}

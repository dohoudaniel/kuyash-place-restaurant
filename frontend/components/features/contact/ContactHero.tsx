"use client";

import { Phone, Mail, MapPin, Clock } from "lucide-react";

export default function ContactHero() {
  const quickInfo = [
    { icon: Phone, label: "Call Us", value: "+234 123 456 7890", color: "var(--red)" },
    { icon: Mail, label: "Email Us", value: "hello@kuyashplace.com", color: "#10b981" },
    { icon: MapPin, label: "Visit Us", value: "Lagos, Nigeria", color: "#3b82f6" },
    { icon: Clock, label: "Open Daily", value: "11AM - 10PM", color: "#f59e0b" },
  ];

  return (
    <div className="relative overflow-hidden">
      <div className="absolute inset-0 opacity-5" style={{
        backgroundImage: 'url("data:image/svg+xml,%3Csvg width=\'60\' height=\'60\' viewBox=\'0 0 60 60\' xmlns=\'http://www.w3.org/2000/svg\'%3E%3Cg fill=\'none\' fill-rule=\'evenodd\'%3E%3Cg fill=\'%23000000\' fill-opacity=\'1\'%3E%3Cpath d=\'M36 34v-4h-2v4h-4v2h4v4h2v-4h4v-2h-4zm0-30V0h-2v4h-4v2h4v4h2V6h4V4h-4zM6 34v-4H4v4H0v2h4v4h2v-4h4v-2H6zM6 4V0H4v4H0v2h4v4h2V6h4V4H6z\'/%3E%3C/g%3E%3C/g%3E%3C/svg%3E")'
      }} />

      <div className="container-custom py-6 sm:py-8 relative">
        <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4 lg:gap-8">
          <div className="lg:w-auto">
            <h1 className="font-black text-3xl sm:text-4xl mb-1" style={{ fontFamily: "var(--font-playfair)", color: "var(--black)" }}>
              Get in Touch
            </h1>
            <p className="text-sm sm:text-base" style={{ color: "var(--text-muted)" }}>
              We'd love to hear from you. Reach out anytime!
            </p>
          </div>

          <div className="flex gap-3 sm:gap-4 lg:gap-6 overflow-x-auto pb-2 lg:pb-0">
            {quickInfo.map((info, idx) => {
              const Icon = info.icon;
              return (
                <div
                  key={idx}
                  className="bg-white rounded-lg px-3 py-2 sm:px-4 sm:py-3 flex items-center gap-2 sm:gap-3 min-w-fit transition-all hover:shadow-md"
                  style={{ border: "1px solid var(--gray-mid)" }}
                >
                  <div
                    className="w-8 h-8 sm:w-10 sm:h-10 rounded-full flex items-center justify-center flex-shrink-0"
                    style={{ background: `${info.color}15` }}
                  >
                    <Icon className="w-4 h-4 sm:w-5 sm:h-5" style={{ color: info.color }} />
                  </div>
                  <div className="text-left">
                    <p className="text-[10px] sm:text-xs font-bold mb-0.5" style={{ color: "var(--text-muted)" }}>
                      {info.label}
                    </p>
                    <p className="font-black text-xs sm:text-sm leading-none whitespace-nowrap" style={{ color: "var(--black)" }}>
                      {info.value}
                    </p>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}

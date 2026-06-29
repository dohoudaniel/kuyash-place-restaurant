"use client";

import { Phone, Mail, MapPin, Clock, MessageCircle, Share2 } from "lucide-react";

export default function ContactInfo() {
  const contactDetails = [
    {
      icon: Phone,
      label: "Phone",
      value: "+234 123 456 7890",
      subvalue: "Mon-Sun, 11AM - 10PM",
      color: "var(--red)",
    },
    {
      icon: Mail,
      label: "Email",
      value: "hello@kuyashplace.com",
      subvalue: "We'll respond within 24 hours",
      color: "#10b981",
    },
    {
      icon: MapPin,
      label: "Address",
      value: "123 Gourmet Street",
      subvalue: "Victoria Island, Lagos, Nigeria",
      color: "#3b82f6",
    },
    {
      icon: Clock,
      label: "Hours",
      value: "11:00 AM - 10:00 PM",
      subvalue: "Open 7 days a week",
      color: "#f59e0b",
    },
  ];

  const socials = [
    { icon: Share2, label: "Instagram", url: "#", color: "#ec4899" },
    { icon: Share2, label: "Facebook", url: "#", color: "#3b82f6" },
    { icon: Share2, label: "Twitter", url: "#", color: "#1da1f2" },
    { icon: MessageCircle, label: "WhatsApp", url: "#", color: "#10b981" },
  ];

  return (
    <div className="space-y-4">
      {/* Contact Details */}
      <div className="bg-white rounded-xl border p-6 lg:sticky lg:top-24" style={{ borderColor: "var(--gray-mid)" }}>
        <h3 className="font-black text-xl mb-4" style={{ fontFamily: "var(--font-playfair)", color: "var(--black)" }}>
          Contact Information
        </h3>

        <div className="space-y-4">
          {contactDetails.map((detail, idx) => {
            const Icon = detail.icon;
            return (
              <div key={idx} className="flex items-start gap-3">
                <div
                  className="w-10 h-10 rounded-full flex items-center justify-center flex-shrink-0"
                  style={{ background: `${detail.color}15` }}
                >
                  <Icon className="w-5 h-5" style={{ color: detail.color }} />
                </div>
                <div>
                  <p className="text-xs font-bold mb-0.5" style={{ color: "var(--text-muted)" }}>
                    {detail.label}
                  </p>
                  <p className="font-bold text-sm mb-0.5" style={{ color: "var(--black)" }}>
                    {detail.value}
                  </p>
                  <p className="text-xs" style={{ color: "var(--text-muted)" }}>
                    {detail.subvalue}
                  </p>
                </div>
              </div>
            );
          })}
        </div>

        {/* Social Media */}
        <div className="mt-6 pt-6" style={{ borderTop: "1px solid var(--gray-mid)" }}>
          <p className="text-sm font-bold mb-3" style={{ color: "var(--black)" }}>
            Follow Us
          </p>
          <div className="grid grid-cols-4 gap-2">
            {socials.map((social) => {
              const Icon = social.icon;
              return (
                <a
                  key={social.label}
                  href={social.url}
                  className="flex flex-col items-center gap-1 p-2 rounded-lg transition-all hover:shadow-md"
                  style={{ background: `${social.color}08` }}
                >
                  <div
                    className="w-10 h-10 rounded-full flex items-center justify-center"
                    style={{ background: `${social.color}15` }}
                  >
                    <Icon className="w-5 h-5" style={{ color: social.color }} />
                  </div>
                  <p className="text-[10px] font-bold text-center" style={{ color: "var(--text-muted)" }}>
                    {social.label}
                  </p>
                </a>
              );
            })}
          </div>
        </div>

        {/* Emergency Contact */}
        <div className="mt-6 p-3 rounded-lg" style={{ background: "var(--gray-light)" }}>
          <p className="text-xs font-bold mb-1" style={{ color: "var(--black)" }}>
            Need Immediate Assistance?
          </p>
          <p className="text-xs" style={{ color: "var(--text-muted)" }}>
            Call our 24/7 hotline: <span className="font-bold" style={{ color: "var(--red)" }}>+234 800 KUYASH</span>
          </p>
        </div>
      </div>
    </div>
  );
}

"use client";

import { Phone, Mail, MapPin, Clock, MessageCircle, Share2 } from "lucide-react";
import { summariseHours } from "@/lib/site/hours";
import { useSiteInfo } from "@/lib/site/useSiteInfo";

/**
 * Contact details from the branch and site settings. Replaces hardcoded
 * details, four social links that went nowhere, and an invented
 * "24/7 hotline: +234 800 KUYASH".
 */
export default function ContactInfo() {
  const { branch, settings, hours } = useSiteInfo();
  const email = settings?.support_email || branch?.email || "";
  const schedule = hours ? summariseHours(hours.hours) : [];

  const contactDetails = [
    branch?.phone && { icon: Phone, label: "Phone", value: branch.phone, href: `tel:${branch.phone}`, subvalue: "Call during opening hours", color: "var(--red)" },
    email && { icon: Mail, label: "Email", value: email, href: `mailto:${email}`, subvalue: "We'll respond within 24 hours", color: "#10b981" },
    branch?.address_line && {
      icon: MapPin,
      label: "Address",
      value: branch.address_line,
      href: undefined,
      subvalue: [branch.city, branch.state].filter(Boolean).join(", "),
      color: "#3b82f6",
    },
  ].filter(Boolean) as { icon: typeof Phone; label: string; value: string; href?: string; subvalue: string; color: string }[];

  const whatsappDigits = branch?.whatsapp?.replace(/\D/g, "");
  const socials = [
    settings?.instagram_url && { label: "Instagram", url: settings.instagram_url, icon: Share2, color: "#ec4899" },
    settings?.facebook_url && { label: "Facebook", url: settings.facebook_url, icon: Share2, color: "#3b82f6" },
    settings?.twitter_url && { label: "X / Twitter", url: settings.twitter_url, icon: Share2, color: "#1da1f2" },
    settings?.tiktok_url && { label: "TikTok", url: settings.tiktok_url, icon: Share2, color: "#111827" },
    whatsappDigits && { label: "WhatsApp", url: `https://wa.me/${whatsappDigits}`, icon: MessageCircle, color: "#10b981" },
  ].filter(Boolean) as { label: string; url: string; icon: typeof Share2; color: string }[];

  return (
    <div className="space-y-4">
      <div className="bg-white rounded-xl border p-6 lg:sticky lg:top-24" style={{ borderColor: "var(--gray-mid)" }}>
        <h3 className="font-black text-xl mb-4" style={{ fontFamily: "var(--font-playfair)", color: "var(--black)" }}>
          Contact Information
        </h3>

        <div className="space-y-4">
          {contactDetails.map((detail) => {
            const Icon = detail.icon;
            return (
              <div key={detail.label} className="flex items-start gap-3">
                <div className="w-10 h-10 rounded-full flex items-center justify-center flex-shrink-0" style={{ background: `color-mix(in srgb, ${detail.color} 9%, white)` }}>
                  <Icon className="w-5 h-5" style={{ color: detail.color }} />
                </div>
                <div>
                  <p className="text-xs font-bold mb-0.5" style={{ color: "var(--text-muted)" }}>{detail.label}</p>
                  {detail.href ? (
                    <a href={detail.href} className="font-bold text-sm mb-0.5 block hover:underline" style={{ color: "var(--black)" }}>{detail.value}</a>
                  ) : (
                    <p className="font-bold text-sm mb-0.5" style={{ color: "var(--black)" }}>{detail.value}</p>
                  )}
                  <p className="text-xs" style={{ color: "var(--text-muted)" }}>{detail.subvalue}</p>
                </div>
              </div>
            );
          })}

          {schedule.length > 0 && (
            <div className="flex items-start gap-3">
              <div className="w-10 h-10 rounded-full flex items-center justify-center flex-shrink-0" style={{ background: "#f59e0b15" }}>
                <Clock className="w-5 h-5" style={{ color: "#f59e0b" }} />
              </div>
              <div>
                <p className="text-xs font-bold mb-0.5" style={{ color: "var(--text-muted)" }}>
                  Hours {hours?.is_open_now ? "· Open now" : "· Closed now"}
                </p>
                {schedule.map((row) => (
                  <p key={row.days} className="text-sm" style={{ color: "var(--black)" }}>
                    <span className="font-bold">{row.days}</span> {row.time}
                  </p>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Social Media */}
        {socials.length > 0 && (
          <div className="mt-6 pt-6" style={{ borderTop: "1px solid var(--gray-mid)" }}>
            <p className="text-sm font-bold mb-3" style={{ color: "var(--black)" }}>Follow Us</p>
            <div className="grid grid-cols-4 gap-2">
              {socials.map((social) => {
                const Icon = social.icon;
                return (
                  <a
                    key={social.label}
                    href={social.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex flex-col items-center gap-1 p-2 rounded-lg transition-all hover:shadow-md"
                    style={{ background: `color-mix(in srgb, ${social.color} 3%, white)` }}
                  >
                    <div className="w-10 h-10 rounded-full flex items-center justify-center" style={{ background: `color-mix(in srgb, ${social.color} 9%, white)` }}>
                      <Icon className="w-5 h-5" style={{ color: social.color }} />
                    </div>
                    <p className="text-[10px] font-bold text-center" style={{ color: "var(--text-muted)" }}>{social.label}</p>
                  </a>
                );
              })}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

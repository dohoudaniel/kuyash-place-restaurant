"use client";

import { useState } from "react";
import { Bell, Mail, MessageSquare, Globe, Save } from "lucide-react";

export default function PreferencesSection() {
  const [preferences, setPreferences] = useState({
    emailNotifications: true,
    smsNotifications: true,
    pushNotifications: false,
    marketingEmails: true,
    orderUpdates: true,
    promotions: true,
    newsletter: false,
  });

  const handleToggle = (key: keyof typeof preferences) => {
    setPreferences((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  const handleSave = () => {
    alert("Preferences saved successfully!");
  };

  return (
    <div className="grid lg:grid-cols-3 gap-6">
      <div className="lg:col-span-2 space-y-6">
        {/* Notifications */}
        <div className="bg-white rounded-xl border p-6" style={{ borderColor: "var(--gray-mid)" }}>
          <div className="flex items-center gap-3 mb-4">
            <div className="w-10 h-10 rounded-full flex items-center justify-center" style={{ background: "var(--red)15" }}>
              <Bell className="w-5 h-5" style={{ color: "var(--red)" }} />
            </div>
            <h3 className="font-black text-xl" style={{ fontFamily: "var(--font-playfair)", color: "var(--black)" }}>
              Notifications
            </h3>
          </div>

          <div className="space-y-4">
            {[
              { key: "emailNotifications" as const, label: "Email Notifications", desc: "Receive updates via email" },
              { key: "smsNotifications" as const, label: "SMS Notifications", desc: "Get text messages for orders" },
              { key: "pushNotifications" as const, label: "Push Notifications", desc: "Browser notifications" },
            ].map((item) => (
              <div key={item.key} className="flex items-center justify-between">
                <div>
                  <p className="font-bold text-sm" style={{ color: "var(--black)" }}>{item.label}</p>
                  <p className="text-xs" style={{ color: "var(--text-muted)" }}>{item.desc}</p>
                </div>
                <button
                  onClick={() => handleToggle(item.key)}
                  className="relative w-12 h-6 rounded-full transition-all"
                  style={{ background: preferences[item.key] ? "var(--red)" : "var(--gray-mid)" }}
                >
                  <div
                    className="absolute top-0.5 w-5 h-5 rounded-full bg-white transition-all"
                    style={{ left: preferences[item.key] ? "26px" : "2px" }}
                  />
                </button>
              </div>
            ))}
          </div>
        </div>

        {/* Marketing */}
        <div className="bg-white rounded-xl border p-6" style={{ borderColor: "var(--gray-mid)" }}>
          <div className="flex items-center gap-3 mb-4">
            <div className="w-10 h-10 rounded-full flex items-center justify-center" style={{ background: "#3b82f615" }}>
              <Mail className="w-5 h-5" style={{ color: "#3b82f6" }} />
            </div>
            <h3 className="font-black text-xl" style={{ fontFamily: "var(--font-playfair)", color: "var(--black)" }}>
              Marketing
            </h3>
          </div>

          <div className="space-y-4">
            {[
              { key: "marketingEmails" as const, label: "Marketing Emails", desc: "Special offers and promotions" },
              { key: "orderUpdates" as const, label: "Order Updates", desc: "Status updates for your orders" },
              { key: "promotions" as const, label: "Promotions", desc: "Exclusive deals and discounts" },
              { key: "newsletter" as const, label: "Newsletter", desc: "Weekly newsletter" },
            ].map((item) => (
              <div key={item.key} className="flex items-center justify-between">
                <div>
                  <p className="font-bold text-sm" style={{ color: "var(--black)" }}>{item.label}</p>
                  <p className="text-xs" style={{ color: "var(--text-muted)" }}>{item.desc}</p>
                </div>
                <button
                  onClick={() => handleToggle(item.key)}
                  className="relative w-12 h-6 rounded-full transition-all"
                  style={{ background: preferences[item.key] ? "var(--red)" : "var(--gray-mid)" }}
                >
                  <div
                    className="absolute top-0.5 w-5 h-5 rounded-full bg-white transition-all"
                    style={{ left: preferences[item.key] ? "26px" : "2px" }}
                  />
                </button>
              </div>
            ))}
          </div>
        </div>

        <button
          onClick={handleSave}
          className="w-full px-6 py-3 rounded-lg font-bold flex items-center justify-center gap-2 transition-all hover:opacity-90"
          style={{ background: "var(--red)", color: "white" }}
        >
          <Save className="w-4 h-4" />
          Save Preferences
        </button>
      </div>

      {/* Info Sidebar */}
      <div className="space-y-4">
        <div className="bg-white rounded-xl border p-6" style={{ borderColor: "var(--gray-mid)" }}>
          <h3 className="font-black text-lg mb-4" style={{ fontFamily: "var(--font-playfair)", color: "var(--black)" }}>
            Communication Tips
          </h3>
          <div className="space-y-3 text-sm" style={{ color: "var(--text-muted)" }}>
            <p>• Enable order updates to track your deliveries</p>
            <p>• Subscribe to newsletter for exclusive deals</p>
            <p>• SMS alerts ensure you never miss a delivery</p>
          </div>
        </div>

        <div className="bg-white rounded-xl border p-6" style={{ borderColor: "var(--gray-mid)" }}>
          <div className="flex items-center gap-2 mb-2">
            <Globe className="w-4 h-4" style={{ color: "var(--red)" }} />
            <p className="font-bold text-sm" style={{ color: "var(--black)" }}>Language</p>
          </div>
          <select className="w-full px-3 py-2 rounded-lg border font-semibold text-sm" style={{ borderColor: "var(--gray-mid)" }}>
            <option>English</option>
            <option>Yoruba</option>
            <option>Igbo</option>
            <option>Hausa</option>
          </select>
        </div>
      </div>
    </div>
  );
}

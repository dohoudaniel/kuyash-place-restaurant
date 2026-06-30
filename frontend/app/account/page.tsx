"use client";

import { useState } from "react";
import AccountHero from "@/components/features/account/AccountHero";
import ProfileSection from "@/components/features/account/ProfileSection";
import OrderHistorySection from "@/components/features/account/OrderHistorySection";
import AddressesSection from "@/components/features/account/AddressesSection";
import PaymentMethodsSection from "@/components/features/account/PaymentMethodsSection";
import PreferencesSection from "@/components/features/account/PreferencesSection";

type TabType = "profile" | "orders" | "addresses" | "payment" | "preferences";

export default function AccountPage() {
  const [activeTab, setActiveTab] = useState<TabType>("profile");

  return (
    <div className="min-h-screen pt-20 sm:pt-24" style={{ background: "var(--gray-light)" }}>
      <AccountHero />

      <div className="container-custom py-6 sm:py-8">
        {/* Tabs */}
        <div className="bg-white rounded-xl border p-2 mb-6 overflow-x-auto" style={{ borderColor: "var(--gray-mid)" }}>
          <div className="flex gap-2 min-w-fit">
            {[
              { id: "profile" as const, label: "Profile" },
              { id: "orders" as const, label: "Order History" },
              { id: "addresses" as const, label: "Addresses" },
              { id: "payment" as const, label: "Payment Methods" },
              { id: "preferences" as const, label: "Preferences" },
            ].map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className="px-4 py-2.5 rounded-lg font-bold text-sm whitespace-nowrap transition-all"
                style={{
                  background: activeTab === tab.id ? "var(--red)" : "transparent",
                  color: activeTab === tab.id ? "white" : "var(--black)",
                }}
              >
                {tab.label}
              </button>
            ))}
          </div>
        </div>

        {/* Tab Content */}
        {activeTab === "profile" && <ProfileSection />}
        {activeTab === "orders" && <OrderHistorySection />}
        {activeTab === "addresses" && <AddressesSection />}
        {activeTab === "payment" && <PaymentMethodsSection />}
        {activeTab === "preferences" && <PreferencesSection />}
      </div>
    </div>
  );
}

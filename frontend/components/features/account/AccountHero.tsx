"use client";

import { useEffect, useState } from "react";
import { User, Heart, MapPin, CreditCard } from "lucide-react";
import { api } from "@/lib/api/client";
import type { Address, Profile, SavedPaymentMethod } from "@/lib/api/types";
import { useWishlistStore } from "@/lib/store/wishlistStore";

/**
 * Account overview with real counts. The previous hero showed "12 orders,
 * 3 addresses, 2 cards, member since 2024" to everyone.
 */
export default function AccountHero() {
  const wishlistCount = useWishlistStore((state) => state.items.length);
  const [addresses, setAddresses] = useState<number | null>(null);
  const [cards, setCards] = useState<number | null>(null);
  const [memberSince, setMemberSince] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    api<Address[]>("/accounts/addresses/").then((list) => !cancelled && setAddresses(list.length)).catch(() => undefined);
    api<SavedPaymentMethod[]>("/payments/methods/").then((list) => !cancelled && setCards(list.length)).catch(() => undefined);
    api<Profile>("/accounts/me/")
      .then((profile) => !cancelled && setMemberSince(String(new Date(profile.date_joined).getFullYear())))
      .catch(() => undefined);
    return () => {
      cancelled = true;
    };
  }, []);

  const stats = [
    { icon: MapPin, label: "Addresses", value: addresses === null ? "–" : String(addresses), color: "#10b981" },
    { icon: CreditCard, label: "Saved Cards", value: cards === null ? "–" : String(cards), color: "#3b82f6" },
    { icon: Heart, label: "Wishlist", value: String(wishlistCount), color: "var(--red)" },
    { icon: User, label: "Member Since", value: memberSince ?? "–", color: "#f59e0b" },
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
              My Account
            </h1>
            <p className="text-sm sm:text-base" style={{ color: "var(--text-muted)" }}>
              Manage your profile, orders, and preferences
            </p>
          </div>

          <div className="flex gap-3 sm:gap-4 lg:gap-6 overflow-x-auto pb-2 lg:pb-0">
            {stats.map((stat) => {
              const Icon = stat.icon;
              return (
                <div
                  key={stat.label}
                  className="bg-white rounded-lg px-3 py-2 sm:px-4 sm:py-3 flex items-center gap-2 sm:gap-3 min-w-fit transition-all hover:shadow-md"
                  style={{ border: "1px solid var(--gray-mid)" }}
                >
                  <div
                    className="w-8 h-8 sm:w-10 sm:h-10 rounded-full flex items-center justify-center flex-shrink-0"
                    style={{ background: `color-mix(in srgb, ${stat.color} 9%, transparent)` }}
                  >
                    <Icon className="w-4 h-4 sm:w-5 sm:h-5" style={{ color: stat.color }} />
                  </div>
                  <div className="text-left">
                    <p className="font-black text-lg sm:text-xl leading-none mb-0.5" style={{ fontFamily: "var(--font-playfair)", color: "var(--black)" }}>
                      {stat.value}
                    </p>
                    <p className="text-[10px] sm:text-xs font-semibold whitespace-nowrap" style={{ color: "var(--text-muted)" }}>
                      {stat.label}
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

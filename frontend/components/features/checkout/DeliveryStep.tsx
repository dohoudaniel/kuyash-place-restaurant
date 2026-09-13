"use client";

import { useEffect, useState } from "react";
import { AlertCircle, Loader2, LogIn, Mail, MapPin, Phone, Plus, Store, Truck, User } from "lucide-react";
import { ApiError, api } from "@/lib/api/client";
import type { Address, Branch } from "@/lib/api/types";
import { useAuthModalStore } from "@/lib/store/authModalStore";
import { useAuthStore } from "@/lib/store/authStore";
import { useCartStore } from "@/lib/store/cartStore";
import AddressForm from "./AddressForm";

interface DeliveryStepProps {
  initial: DeliveryData | null;
  branch: Branch | null;
  onNext: (data: DeliveryData) => void;
}

export interface DeliveryData {
  fulfilment: "delivery" | "pickup";
  /** The saved address chosen for delivery. */
  address: Address | null;
  /** Contact details when checking out without an account. */
  guest: { full_name: string; email: string; phone: string } | null;
  customerNote: string;
}

const inputClass = "w-full px-4 py-3 rounded-lg border outline-none transition-colors focus:border-red-500";

/**
 * How the order reaches the customer.
 *
 * Delivery addresses belong to accounts, so guests can check out for pickup or
 * sign in to have their order delivered. The chosen address is sent to the cart,
 * which re-prices delivery for its zone before the customer sees the review.
 */
export default function DeliveryStep({ initial, branch, onNext }: DeliveryStepProps) {
  const user = useAuthStore((state) => state.user);
  const isSignedIn = useAuthStore((state) => state.status === "authenticated");
  const openAuth = useAuthModalStore((state) => state.open);
  const cart = useCartStore((state) => state.cart);
  const setFulfilment = useCartStore((state) => state.setFulfilment);

  const [fulfilment, setFulfilmentChoice] = useState<"delivery" | "pickup">(
    initial?.fulfilment ?? (isSignedIn ? (cart?.fulfilment_type === "pickup" ? "pickup" : "delivery") : "pickup")
  );
  const [addresses, setAddresses] = useState<Address[]>([]);
  const [addressesState, setAddressesState] = useState<"idle" | "loading" | "ready" | "error">("idle");
  const [selectedId, setSelectedId] = useState<string | null>(initial?.address?.id ?? cart?.delivery_address ?? null);
  const [showAddressForm, setShowAddressForm] = useState(false);
  const [guest, setGuest] = useState(initial?.guest ?? { full_name: "", email: "", phone: "" });
  const [customerNote, setCustomerNote] = useState(initial?.customerNote ?? "");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!isSignedIn) return;
    let cancelled = false;
    api<Address[]>("/accounts/addresses/")
      .then((list) => {
        if (cancelled) return;
        setAddresses(list);
        setAddressesState("ready");
        setSelectedId((current) => current ?? list.find((a) => a.is_default && a.is_deliverable)?.id ?? null);
        if (list.length === 0) setShowAddressForm(true);
      })
      .catch(() => {
        if (!cancelled) setAddressesState("error");
      });
    return () => {
      cancelled = true;
    };
  }, [isSignedIn]);

  const selected = addresses.find((address) => address.id === selectedId) ?? null;
  const effectiveFulfilment = isSignedIn ? fulfilment : "pickup";

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (effectiveFulfilment === "delivery" && (!selected || !selected.is_deliverable)) {
      setError(selected ? "We don't deliver to that address yet. Choose another, or switch to pickup." : "Choose a delivery address.");
      return;
    }

    setSaving(true);
    try {
      await setFulfilment(
        effectiveFulfilment === "delivery"
          ? { fulfilment_type: "delivery", delivery_address: selected!.id }
          : { fulfilment_type: "pickup" }
      );
      onNext({
        fulfilment: effectiveFulfilment,
        address: effectiveFulfilment === "delivery" ? selected : null,
        guest: isSignedIn ? null : { full_name: guest.full_name.trim(), email: guest.email.trim(), phone: guest.phone.trim() },
        customerNote: customerNote.trim(),
      });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong. Please try again.");
    } finally {
      setSaving(false);
    }
  };

  const options = [
    { id: "delivery" as const, label: "Delivery", icon: Truck, disabled: !isSignedIn },
    { id: "pickup" as const, label: "Pickup", icon: Store, disabled: false },
  ];

  return (
    <form onSubmit={handleSubmit} className="max-w-2xl mx-auto">
      <div className="bg-white rounded-xl border p-6 sm:p-8" style={{ borderColor: "var(--gray-mid)" }}>
        <h2 className="font-black text-xl sm:text-2xl mb-6" style={{ fontFamily: "var(--font-playfair)", color: "var(--black)" }}>
          Delivery Information
        </h2>

        {/* Delivery or pickup */}
        <div className="grid grid-cols-2 gap-4 mb-6" role="radiogroup" aria-label="How would you like your order?">
          {options.map((option) => {
            const Icon = option.icon;
            const isSelected = effectiveFulfilment === option.id;
            return (
              <button
                key={option.id}
                type="button"
                role="radio"
                aria-checked={isSelected}
                disabled={option.disabled}
                onClick={() => setFulfilmentChoice(option.id)}
                className="p-4 rounded-lg border-2 transition-all hover:scale-105 active:scale-95 disabled:opacity-50 disabled:hover:scale-100 disabled:cursor-not-allowed"
                style={{
                  borderColor: isSelected ? "var(--red)" : "var(--gray-mid)",
                  background: isSelected ? "rgba(217,4,41,0.05)" : "white",
                }}
              >
                <Icon className="w-6 h-6 mx-auto mb-2" style={{ color: isSelected ? "var(--red)" : "var(--text-muted)" }} />
                <p className="text-sm font-semibold" style={{ color: isSelected ? "var(--red)" : "var(--black)" }}>
                  {option.label}
                </p>
              </button>
            );
          })}
        </div>

        {!isSignedIn && (
          <div className="mb-6 p-4 rounded-lg flex items-start gap-3" style={{ background: "var(--off-white)" }}>
            <LogIn className="w-5 h-5 shrink-0 mt-0.5" style={{ color: "var(--red)" }} />
            <div className="flex-1">
              <p className="text-sm" style={{ color: "var(--text-muted)" }}>
                Delivery is available to signed-in customers, so your address is saved for next time.
              </p>
              <button
                type="button"
                onClick={() => openAuth("login", "/checkout")}
                className="text-sm font-bold mt-1 transition-all hover:opacity-80"
                style={{ color: "var(--red)" }}
              >
                Sign in for delivery
              </button>
            </div>
          </div>
        )}

        <div className="space-y-4">
          {/* Signed-in delivery: saved addresses */}
          {effectiveFulfilment === "delivery" && (
            <>
              {addressesState === "loading" || (addressesState === "idle" && isSignedIn) ? (
                <div className="flex items-center gap-2" role="status">
                  <Loader2 className="w-4 h-4 animate-spin" style={{ color: "var(--red)" }} />
                  <span className="text-sm" style={{ color: "var(--text-muted)" }}>Loading your addresses…</span>
                </div>
              ) : addressesState === "error" ? (
                <p role="alert" className="text-sm" style={{ color: "var(--red)" }}>We couldn&apos;t load your addresses. Please refresh.</p>
              ) : (
                <div className="space-y-3" role="radiogroup" aria-label="Delivery address">
                  {addresses.map((address) => {
                    const isSelected = address.id === selectedId;
                    return (
                      <button
                        key={address.id}
                        type="button"
                        role="radio"
                        aria-checked={isSelected}
                        onClick={() => setSelectedId(address.id)}
                        className="w-full text-left p-4 rounded-lg border-2 transition-all"
                        style={{
                          borderColor: isSelected ? "var(--red)" : "var(--gray-mid)",
                          background: isSelected ? "rgba(217,4,41,0.05)" : "white",
                        }}
                      >
                        <div className="flex items-start gap-3">
                          <MapPin className="w-5 h-5 shrink-0 mt-0.5" style={{ color: isSelected ? "var(--red)" : "var(--text-muted)" }} />
                          <div className="flex-1 min-w-0">
                            <p className="text-sm font-bold capitalize" style={{ color: "var(--black)" }}>
                              {address.label} · {address.recipient_name}
                            </p>
                            <p className="text-sm" style={{ color: "var(--text-muted)" }}>
                              {[address.street, address.area, address.city].filter(Boolean).join(", ")}
                            </p>
                            {address.zone ? (
                              <p className="text-xs font-semibold mt-1" style={{ color: "var(--black)" }}>
                                {address.zone.name} · delivery {address.zone.fee?.display} · about {address.zone.estimated_minutes} mins
                              </p>
                            ) : (
                              <p className="text-xs font-semibold mt-1" style={{ color: "var(--red)" }}>
                                Outside our delivery area — pickup only
                              </p>
                            )}
                          </div>
                        </div>
                      </button>
                    );
                  })}

                  {showAddressForm ? (
                    <AddressForm
                      defaults={{ recipient_name: user?.full_name, phone: user?.phone, city: branch?.city, state: branch?.state }}
                      onSaved={(address) => {
                        setAddresses((current) => [address, ...current]);
                        setSelectedId(address.id);
                        setShowAddressForm(false);
                      }}
                      onCancel={addresses.length > 0 ? () => setShowAddressForm(false) : undefined}
                    />
                  ) : (
                    <button
                      type="button"
                      onClick={() => setShowAddressForm(true)}
                      className="w-full flex items-center justify-center gap-2 p-3 rounded-lg text-sm font-bold transition-all hover:bg-red-50"
                      style={{ border: "2px dashed var(--gray-mid)", color: "var(--red)" }}
                    >
                      <Plus className="w-4 h-4" />
                      Add a New Address
                    </button>
                  )}
                </div>
              )}
            </>
          )}

          {/* Pickup */}
          {effectiveFulfilment === "pickup" && branch && (
            <div className="p-4 rounded-lg flex items-start gap-3" style={{ background: "var(--off-white)" }}>
              <Store className="w-5 h-5 shrink-0 mt-0.5" style={{ color: "var(--red)" }} />
              <div>
                <p className="text-sm font-semibold" style={{ color: "var(--black)" }}>Collect from {branch.name}</p>
                <p className="text-sm" style={{ color: "var(--text-muted)" }}>
                  {[branch.address_line, branch.city].filter(Boolean).join(", ")}
                </p>
              </div>
            </div>
          )}

          {/* Guest contact details */}
          {!isSignedIn && (
            <>
              <div>
                <label htmlFor="guest-name" className="flex items-center gap-2 text-sm font-semibold mb-2" style={{ color: "var(--black)" }}>
                  <User className="w-4 h-4" style={{ color: "var(--red)" }} />
                  Full Name
                </label>
                <input
                  id="guest-name"
                  type="text"
                  required
                  autoComplete="name"
                  value={guest.full_name}
                  onChange={(e) => setGuest({ ...guest, full_name: e.target.value })}
                  placeholder="Enter your full name"
                  className={inputClass}
                  style={{ borderColor: "var(--gray-mid)" }}
                />
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label htmlFor="guest-email" className="flex items-center gap-2 text-sm font-semibold mb-2" style={{ color: "var(--black)" }}>
                    <Mail className="w-4 h-4" style={{ color: "var(--red)" }} />
                    Email
                  </label>
                  <input
                    id="guest-email"
                    type="email"
                    required
                    autoComplete="email"
                    value={guest.email}
                    onChange={(e) => setGuest({ ...guest, email: e.target.value })}
                    placeholder="For your order confirmation"
                    className={inputClass}
                    style={{ borderColor: "var(--gray-mid)" }}
                  />
                </div>
                <div>
                  <label htmlFor="guest-phone" className="flex items-center gap-2 text-sm font-semibold mb-2" style={{ color: "var(--black)" }}>
                    <Phone className="w-4 h-4" style={{ color: "var(--red)" }} />
                    Phone Number
                  </label>
                  <input
                    id="guest-phone"
                    type="tel"
                    required
                    autoComplete="tel"
                    value={guest.phone}
                    onChange={(e) => setGuest({ ...guest, phone: e.target.value })}
                    placeholder="+234 800 000 0000"
                    className={inputClass}
                    style={{ borderColor: "var(--gray-mid)" }}
                  />
                </div>
              </div>
            </>
          )}

          {/* Note */}
          <div>
            <label htmlFor="customer-note" className="text-sm font-semibold mb-2 block" style={{ color: "var(--black)" }}>
              Note for the Restaurant (Optional)
            </label>
            <textarea
              id="customer-note"
              value={customerNote}
              onChange={(e) => setCustomerNote(e.target.value)}
              placeholder="Anything we should know about your order..."
              rows={3}
              maxLength={500}
              className={`${inputClass} resize-none`}
              style={{ borderColor: "var(--gray-mid)" }}
            />
          </div>
        </div>

        {error && (
          <p role="alert" className="flex items-center gap-2 text-sm font-semibold mt-4" style={{ color: "var(--red)" }}>
            <AlertCircle className="w-4 h-4" />
            {error}
          </p>
        )}

        <button
          type="submit"
          disabled={saving || (effectiveFulfilment === "delivery" && showAddressForm && addresses.length === 0)}
          className="w-full mt-6 px-6 py-3.5 rounded-full text-sm font-bold text-white flex items-center justify-center gap-2 transition-all duration-200 hover:opacity-90 hover:scale-[1.02] active:scale-95 disabled:opacity-50 disabled:hover:scale-100"
          style={{ background: "var(--red)" }}
        >
          {saving && <Loader2 className="w-4 h-4 animate-spin" />}
          Continue to Payment
        </button>
      </div>
    </form>
  );
}

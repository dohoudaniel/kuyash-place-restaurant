"use client";

import { useEffect, useState } from "react";
import { MapPin, Plus, Edit2, Trash2, Home, Briefcase, Loader2, X } from "lucide-react";
import { Dialog as DialogPrimitive } from "radix-ui";
import { Dialog, DialogClose, DialogOverlay, DialogPortal, DialogTitle } from "@/components/ui/dialog";
import AddressForm from "@/components/features/checkout/AddressForm";
import { ApiError, api } from "@/lib/api/client";
import type { Address } from "@/lib/api/types";
import { useAuthStore } from "@/lib/store/authStore";

const TYPE_ICONS = { home: Home, work: Briefcase, other: MapPin } as const;

/**
 * The account's delivery addresses. Previously two hardcoded Lagos addresses
 * shown to every visitor, and an "Add New" dialog whose form was a comment.
 */
export default function AddressesSection() {
  const user = useAuthStore((state) => state.user);
  const [addresses, setAddresses] = useState<Address[]>([]);
  const [loadState, setLoadState] = useState<"loading" | "ready" | "error">("loading");
  const [editing, setEditing] = useState<Address | "new" | null>(null);
  const [confirmDelete, setConfirmDelete] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    try {
      setAddresses(await api<Address[]>("/accounts/addresses/"));
      setLoadState("ready");
    } catch {
      setLoadState("error");
    }
  };

  useEffect(() => {
    let cancelled = false;
    api<Address[]>("/accounts/addresses/")
      .then((list) => {
        if (cancelled) return;
        setAddresses(list);
        setLoadState("ready");
      })
      .catch(() => !cancelled && setLoadState("error"));
    return () => {
      cancelled = true;
    };
  }, []);

  const run = async (id: string, action: () => Promise<void>) => {
    setBusy(id);
    setError(null);
    try {
      await action();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong. Please try again.");
    } finally {
      setBusy(null);
    }
  };

  const setDefault = (address: Address) =>
    run(address.id, async () => {
      const updated = await api<Address>(`/accounts/addresses/${address.id}/set-default/`, { method: "POST" });
      setAddresses((current) => current.map((a) => ({ ...a, is_default: a.id === updated.id })));
    });

  const remove = (address: Address) =>
    run(address.id, async () => {
      await api<void>(`/accounts/addresses/${address.id}/`, { method: "DELETE" });
      setConfirmDelete(null);
      // Deleting the default promotes another on the server; re-read to show it.
      await load();
    });

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h2 className="font-black text-2xl" style={{ fontFamily: "var(--font-playfair)", color: "var(--black)" }}>
          Delivery Addresses
        </h2>
        <button
          onClick={() => setEditing("new")}
          className="px-4 py-2 rounded-lg font-bold text-sm flex items-center gap-2 transition-all hover:opacity-90"
          style={{ background: "var(--red)", color: "white" }}
        >
          <Plus className="w-4 h-4" />
          Add New
        </button>
      </div>

      {error && <p role="alert" className="mb-4 text-sm font-semibold" style={{ color: "var(--red)" }}>{error}</p>}

      {loadState === "loading" ? (
        <div className="bg-white rounded-xl border p-8 flex items-center justify-center gap-2" style={{ borderColor: "var(--gray-mid)" }} role="status">
          <Loader2 className="w-5 h-5 animate-spin" style={{ color: "var(--red)" }} />
          <span className="text-sm" style={{ color: "var(--text-muted)" }}>Loading your addresses…</span>
        </div>
      ) : loadState === "error" ? (
        <div className="bg-white rounded-xl border p-8 text-center" style={{ borderColor: "var(--gray-mid)" }}>
          <p role="alert" className="text-sm" style={{ color: "var(--text-muted)" }}>We couldn&apos;t load your addresses. Please refresh.</p>
        </div>
      ) : addresses.length === 0 ? (
        <div className="bg-white rounded-xl border p-8 text-center" style={{ borderColor: "var(--gray-mid)" }}>
          <MapPin className="w-10 h-10 mx-auto mb-3" style={{ color: "var(--text-muted)" }} />
          <p className="font-black text-base" style={{ color: "var(--black)" }}>No saved addresses</p>
          <p className="text-sm mt-1" style={{ color: "var(--text-muted)" }}>Add one here, or at checkout.</p>
        </div>
      ) : (
        <div className="grid sm:grid-cols-2 gap-4">
          {addresses.map((address) => {
            const Icon = TYPE_ICONS[(address.label as keyof typeof TYPE_ICONS) ?? "other"] ?? MapPin;
            const isBusy = busy === address.id;
            return (
              <div
                key={address.id}
                className="bg-white rounded-xl border p-5 transition-all hover:shadow-md"
                style={{ borderColor: address.is_default ? "var(--red)" : "var(--gray-mid)", opacity: isBusy ? 0.6 : 1 }}
              >
                <div className="flex items-start justify-between mb-3">
                  <div className="flex items-center gap-2">
                    <div className="w-10 h-10 rounded-full flex items-center justify-center" style={{ background: "rgba(217,4,41,0.08)" }}>
                      <Icon className="w-5 h-5" style={{ color: "var(--red)" }} />
                    </div>
                    <div>
                      <h3 className="font-black text-base capitalize" style={{ color: "var(--black)" }}>
                        {address.label}
                      </h3>
                      {address.is_default && (
                        <span className="text-xs font-bold" style={{ color: "var(--red)" }}>
                          Default
                        </span>
                      )}
                    </div>
                  </div>
                  <div className="flex gap-2">
                    <button
                      onClick={() => setEditing(address)}
                      aria-label={`Edit ${address.label} address`}
                      className="w-8 h-8 rounded-lg flex items-center justify-center transition-all hover:bg-gray-100"
                      style={{ border: "1px solid var(--gray-mid)" }}
                    >
                      <Edit2 className="w-4 h-4" style={{ color: "var(--black)" }} />
                    </button>
                    <button
                      onClick={() => setConfirmDelete(address.id)}
                      aria-label={`Delete ${address.label} address`}
                      className="w-8 h-8 rounded-lg flex items-center justify-center transition-all hover:bg-red-50"
                      style={{ border: "1px solid var(--gray-mid)" }}
                    >
                      <Trash2 className="w-4 h-4" style={{ color: "var(--red)" }} />
                    </button>
                  </div>
                </div>

                <div className="space-y-1 text-sm" style={{ color: "var(--text-muted)" }}>
                  <p className="font-semibold" style={{ color: "var(--black)" }}>{address.recipient_name}</p>
                  <p className="font-semibold">{address.street}</p>
                  <p>{[address.area, address.city, address.state].filter(Boolean).join(", ")}</p>
                  <p className="font-semibold">{address.phone}</p>
                  <p className="text-xs pt-1" style={{ color: address.zone ? "var(--text-muted)" : "var(--red)" }}>
                    {address.zone ? `Delivery zone: ${address.zone.name}` : "Outside our delivery area — pickup only"}
                  </p>
                </div>

                {confirmDelete === address.id ? (
                  <div className="mt-4 flex gap-2">
                    <button onClick={() => setConfirmDelete(null)} className="flex-1 px-3 py-2 rounded-lg font-semibold text-xs" style={{ background: "var(--gray-light)", color: "var(--black)" }}>
                      Keep
                    </button>
                    <button onClick={() => remove(address)} disabled={isBusy} className="flex-1 px-3 py-2 rounded-lg font-bold text-xs text-white disabled:opacity-50" style={{ background: "var(--red)" }}>
                      Delete Address
                    </button>
                  </div>
                ) : (
                  !address.is_default && (
                    <button
                      onClick={() => setDefault(address)}
                      disabled={isBusy}
                      className="mt-4 w-full px-4 py-2 rounded-lg font-bold text-xs transition-all hover:opacity-80 disabled:opacity-50"
                      style={{ background: "var(--gray-light)", color: "var(--black)" }}
                    >
                      Set as Default
                    </button>
                  )
                )}
              </div>
            );
          })}
        </div>
      )}

      <Dialog open={editing !== null} onOpenChange={(open) => !open && setEditing(null)}>
        <DialogPortal>
          <DialogOverlay className="bg-black/50 supports-backdrop-filter:backdrop-blur-none" />
          <DialogPrimitive.Content
            aria-describedby={undefined}
            className="fixed top-1/2 left-1/2 z-50 -translate-x-1/2 -translate-y-1/2 bg-white rounded-xl w-[calc(100%-2rem)] max-w-lg max-h-[90vh] overflow-y-auto p-6 outline-none"
          >
            <div className="flex items-center justify-between mb-4">
              <DialogTitle className="font-black text-xl leading-normal" style={{ fontFamily: "var(--font-playfair)", color: "var(--black)" }}>
                {editing === "new" ? "Add New Address" : "Edit Address"}
              </DialogTitle>
              <DialogClose asChild>
                <button aria-label="Close" className="w-8 h-8 rounded-full flex items-center justify-center hover:bg-gray-100">
                  <X className="w-5 h-5" />
                </button>
              </DialogClose>
            </div>
            {editing !== null && (
              <AddressForm
                key={editing === "new" ? "new" : editing.id}
                address={editing === "new" ? undefined : editing}
                defaults={{ recipient_name: user?.full_name, phone: user?.phone }}
                onSaved={() => {
                  setEditing(null);
                  void load();
                }}
                onCancel={() => setEditing(null)}
              />
            )}
          </DialogPrimitive.Content>
        </DialogPortal>
      </Dialog>
    </div>
  );
}

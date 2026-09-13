"use client";

import { MapPin, CreditCard, Wallet, Banknote, Store } from "lucide-react";
import type { Branch, OrderDetail } from "@/lib/api/types";

interface OrderSummaryProps {
  order: OrderDetail;
  branch: Branch | null;
}

const PAYMENT_ICONS = { card: CreditCard, transfer: Wallet, cash: Banknote } as const;
const PAYMENT_LABELS = { card: "Pay Online", transfer: "Bank Transfer", cash: "Cash" } as const;

export default function OrderSummary({ order, branch }: OrderSummaryProps) {
  const method = (order.payment_method in PAYMENT_ICONS ? order.payment_method : "card") as keyof typeof PAYMENT_ICONS;
  const PaymentIcon = PAYMENT_ICONS[method];
  const address = order.delivery_address;
  const { totals } = order;
  const awaitingTransfer = order.payment_method === "transfer" && order.payment_status !== "paid";
  const bank = branch?.bank_transfer ?? null;

  return (
    <div className="bg-white rounded-xl border p-6 sm:p-8" style={{ borderColor: "var(--gray-mid)" }}>
      <h2 className="font-black text-xl sm:text-2xl mb-6" style={{ fontFamily: "var(--font-playfair)", color: "var(--black)" }}>
        Order Summary
      </h2>

      {/* Delivery Address or Pickup */}
      <div className="mb-6">
        <div className="flex items-center gap-2 mb-3">
          {address ? <MapPin className="w-5 h-5" style={{ color: "var(--red)" }} /> : <Store className="w-5 h-5" style={{ color: "var(--red)" }} />}
          <h3 className="font-bold text-sm" style={{ color: "var(--black)" }}>{address ? "Delivery Address" : "Pickup"}</h3>
        </div>
        <div className="pl-7 space-y-1">
          {address ? (
            <>
              <p className="font-semibold text-sm" style={{ color: "var(--black)" }}>{address.recipient_name}</p>
              <p className="text-sm" style={{ color: "var(--text-muted)" }}>{address.phone}</p>
              <p className="text-sm" style={{ color: "var(--text-muted)" }}>
                {[address.street, address.area, address.city, address.state].filter(Boolean).join(", ")}
              </p>
              {address.landmark && <p className="text-sm" style={{ color: "var(--text-muted)" }}>Near {address.landmark}</p>}
              {address.delivery_notes && (
                <p className="text-xs italic mt-2" style={{ color: "var(--text-muted)" }}>
                  Note: {address.delivery_notes}
                </p>
              )}
            </>
          ) : (
            <>
              <p className="font-semibold text-sm" style={{ color: "var(--black)" }}>{branch?.name ?? "Kuyash Place"}</p>
              <p className="text-sm" style={{ color: "var(--text-muted)" }}>
                {[branch?.address_line, branch?.city].filter(Boolean).join(", ")}
              </p>
            </>
          )}
        </div>
      </div>

      {/* Payment Method */}
      <div className="mb-6 pb-6 border-b" style={{ borderColor: "var(--gray-mid)" }}>
        <div className="flex items-center gap-2 mb-3">
          <PaymentIcon className="w-5 h-5" style={{ color: "var(--red)" }} />
          <h3 className="font-bold text-sm" style={{ color: "var(--black)" }}>Payment Method</h3>
        </div>
        <p className="pl-7 text-sm" style={{ color: "var(--text-muted)" }}>
          {PAYMENT_LABELS[method]} · <span className="font-semibold capitalize">{order.payment_status.replaceAll("_", " ")}</span>
        </p>

        {awaitingTransfer && bank && (
          <div className="mt-3 ml-7 p-3 rounded-lg text-sm" style={{ background: "var(--off-white)" }}>
            <p className="mb-2" style={{ color: "var(--text-muted)" }}>
              Transfer <strong style={{ color: "var(--black)" }}>{totals.grand_total.display}</strong> with the narration{" "}
              <strong style={{ color: "var(--black)" }}>{order.reference}</strong>:
            </p>
            <p style={{ color: "var(--black)" }}>{bank.bank_name}</p>
            <p style={{ color: "var(--black)" }}>{bank.account_name}</p>
            <p className="font-bold" style={{ color: "var(--black)" }}>{bank.account_number}</p>
          </div>
        )}
      </div>

      {/* Price Breakdown */}
      <div className="space-y-3">
        <div className="flex justify-between text-sm">
          <span style={{ color: "var(--text-muted)" }}>Subtotal</span>
          <span className="font-semibold" style={{ color: "var(--black)" }}>{totals.subtotal.display}</span>
        </div>
        {totals.discount.amount > 0 && (
          <div className="flex justify-between text-sm">
            <span style={{ color: "var(--red)" }}>Discount{order.promo_code ? ` (${order.promo_code})` : ""}</span>
            <span className="font-semibold" style={{ color: "var(--red)" }}>−{totals.discount.display}</span>
          </div>
        )}
        <div className="flex justify-between text-sm">
          <span style={{ color: "var(--text-muted)" }}>{address ? "Delivery Fee" : "Pickup"}</span>
          <span className="font-semibold" style={{ color: "var(--black)" }}>
            {totals.delivery_fee.amount > 0 ? totals.delivery_fee.display : "Free"}
          </span>
        </div>
        {totals.service_charge.amount > 0 && (
          <div className="flex justify-between text-sm">
            <span style={{ color: "var(--text-muted)" }}>Service Charge</span>
            <span className="font-semibold" style={{ color: "var(--black)" }}>{totals.service_charge.display}</span>
          </div>
        )}
        <div className="flex justify-between text-sm">
          <span style={{ color: "var(--text-muted)" }}>VAT</span>
          <span className="font-semibold" style={{ color: "var(--black)" }}>{totals.vat.display}</span>
        </div>
        {totals.tip.amount > 0 && (
          <div className="flex justify-between text-sm">
            <span style={{ color: "var(--text-muted)" }}>Tip</span>
            <span className="font-semibold" style={{ color: "var(--black)" }}>{totals.tip.display}</span>
          </div>
        )}
        <div className="pt-3 border-t" style={{ borderColor: "var(--gray-mid)" }}>
          <div className="flex justify-between items-center">
            <span className="font-bold text-base" style={{ color: "var(--black)" }}>Total</span>
            <span className="font-black text-xl" style={{ fontFamily: "var(--font-playfair)", color: "var(--red)" }}>
              {totals.grand_total.display}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}

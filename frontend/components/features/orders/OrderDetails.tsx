"use client";

import Image from "next/image";
import { mediaUrl } from "@/lib/api/media";
import type { OrderDetail } from "@/lib/api/types";
import { formatDate } from "./statusStyles";

interface OrderDetailsProps {
  order: OrderDetail;
}

export default function OrderDetails({ order }: OrderDetailsProps) {
  return (
    <div className="bg-white rounded-xl border p-6 sm:p-8" style={{ borderColor: "var(--gray-mid)" }}>
      <div className="flex items-center justify-between mb-6">
        <h2 className="font-black text-xl sm:text-2xl" style={{ fontFamily: "var(--font-playfair)", color: "var(--black)" }}>
          Order Details
        </h2>
        <div className="text-right">
          <p className="text-xs font-semibold" style={{ color: "var(--text-muted)" }}>Order Reference</p>
          <p className="text-sm font-bold mt-0.5" style={{ color: "var(--black)" }}>{order.reference}</p>
        </div>
      </div>

      {order.placed_at && (
        <div className="mb-4">
          <p className="text-xs font-semibold" style={{ color: "var(--text-muted)" }}>
            Placed on {formatDate(order.placed_at)}
          </p>
        </div>
      )}

      <div className="space-y-4">
        {order.items.map((line, index) => {
          const imageSrc = mediaUrl(line.image_url);
          const details = [line.variant_name, ...line.modifiers].filter(Boolean).join(" · ");
          return (
            <div key={`${line.slug}-${index}`} className="flex gap-4 pb-4 border-b last:border-b-0" style={{ borderColor: "var(--gray-mid)" }}>
              {/* Image */}
              <div className="shrink-0 w-16 h-16 sm:w-20 sm:h-20 rounded-lg overflow-hidden relative" style={{ background: "var(--off-white)" }}>
                {imageSrc ? (
                  <Image src={imageSrc} alt={line.name} fill sizes="80px" className="object-cover" />
                ) : (
                  <div className="w-full h-full flex items-center justify-center text-2xl">🍽️</div>
                )}
              </div>

              {/* Details */}
              <div className="flex-1 min-w-0">
                <h3 className="font-bold text-sm sm:text-base truncate" style={{ color: "var(--black)" }}>
                  {line.name}
                </h3>
                {details && (
                  <p className="text-xs sm:text-sm mt-1 line-clamp-1" style={{ color: "var(--text-muted)" }}>
                    {details}
                  </p>
                )}
                {line.special_instructions && (
                  <p className="text-xs mt-1 italic line-clamp-1" style={{ color: "var(--text-muted)" }}>
                    “{line.special_instructions}”
                  </p>
                )}
                <p className="text-xs font-semibold mt-2" style={{ color: "var(--text-muted)" }}>
                  Qty: {line.quantity}
                </p>
              </div>

              {/* Price */}
              <div className="text-right shrink-0">
                <p className="font-bold text-sm sm:text-base" style={{ color: "var(--black)" }}>
                  {line.line_subtotal.display}
                </p>
                <p className="text-xs mt-1" style={{ color: "var(--text-muted)" }}>
                  {line.unit_price.display} each
                </p>
              </div>
            </div>
          );
        })}
      </div>

      {/* Subtotal */}
      <div className="mt-6 pt-4 border-t" style={{ borderColor: "var(--gray-mid)" }}>
        <div className="flex justify-between items-center">
          <p className="font-semibold" style={{ color: "var(--text-muted)" }}>Subtotal</p>
          <p className="font-bold text-lg" style={{ color: "var(--black)" }}>{order.totals.subtotal.display}</p>
        </div>
      </div>
    </div>
  );
}

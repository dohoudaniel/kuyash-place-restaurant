import {
  CheckCircle,
  ChefHat,
  ClipboardCheck,
  Clock,
  CreditCard,
  Home,
  Package,
  Truck,
  XCircle,
  type LucideIcon,
} from "lucide-react";

/** How each real order status looks. Labels come from the API's `status_display`. */
const STYLES: Record<string, { icon: LucideIcon; color: string }> = {
  pending_payment: { icon: CreditCard, color: "#f59e0b" },
  paid: { icon: CheckCircle, color: "var(--red)" },
  confirmed: { icon: ClipboardCheck, color: "var(--red)" },
  preparing: { icon: ChefHat, color: "#f59e0b" },
  ready: { icon: Package, color: "#3b82f6" },
  out_for_delivery: { icon: Truck, color: "#3b82f6" },
  delivered: { icon: Home, color: "#10b981" },
  cancelled: { icon: XCircle, color: "#6b7280" },
  rejected: { icon: XCircle, color: "#6b7280" },
  expired: { icon: Clock, color: "#6b7280" },
  refunded: { icon: XCircle, color: "#6b7280" },
  failed: { icon: XCircle, color: "var(--red)" },
  failed_delivery: { icon: XCircle, color: "var(--red)" },
};

export function statusStyle(status: string): { icon: LucideIcon; color: string } {
  return STYLES[status] ?? { icon: Package, color: "var(--text-muted)" };
}

/** Statuses after which nothing more will happen, so polling stops. */
export const FINAL_STATUSES = new Set([
  "delivered",
  "cancelled",
  "rejected",
  "expired",
  "refunded",
  "failed",
  "failed_delivery",
]);

export const PAYMENT_METHOD_LABELS: Record<string, string> = {
  card: "Paid Online",
  transfer: "Bank Transfer",
  cash: "Cash",
};

export function formatTime(iso: string | null | undefined): string {
  if (!iso) return "";
  return new Date(iso).toLocaleTimeString("en-NG", { hour: "2-digit", minute: "2-digit" });
}

export function formatDate(iso: string | null | undefined, style: "long" | "short" = "long"): string {
  if (!iso) return "";
  return new Date(iso).toLocaleDateString("en-NG", style === "long"
    ? { weekday: "long", year: "numeric", month: "long", day: "numeric", hour: "2-digit", minute: "2-digit" }
    : { month: "short", day: "numeric", year: "numeric" });
}

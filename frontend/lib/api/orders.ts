/**
 * Orders and payments.
 *
 * Nothing here sends a price. `expected_total` is a guard: if the server's total
 * differs from the one the customer was shown, the order is refused rather than
 * charged at a figure they never saw.
 */
import { guestHeaders, rememberGuestOrder } from "@/lib/orders/guestTokens";
import { api, apiBlob, pathFromApiUrl } from "./client";
import type { OrderDetail, OrderRow, PaymentInitialised, PaymentVerification, ReorderResponse } from "./types";

export type PaymentMethod = "card" | "transfer" | "cash";

export interface PlaceOrderInput {
  payment_method: PaymentMethod;
  /** Kobo — the grand total the customer was shown. */
  expected_total: number;
  customer_note?: string;
  /** Required when not signed in. */
  guest?: { full_name: string; email: string; phone: string };
}

export async function placeOrder(input: PlaceOrderInput, idempotencyKey: string): Promise<OrderDetail> {
  const order = await api<OrderDetail>("/orders/", { method: "POST", body: input, idempotencyKey });
  if (order.guest_token) rememberGuestOrder(order.reference, order.guest_token);
  return order;
}

export const fetchOrder = (reference: string, init: { signal?: AbortSignal } = {}) =>
  api<OrderDetail>(`/orders/${encodeURIComponent(reference)}/`, { headers: guestHeaders(reference), signal: init.signal });

export interface OrderPage {
  next: string | null;
  previous: string | null;
  results: OrderRow[];
}

/** Signed-in history, newest first. Pass the previous page's `next` to continue. */
export const fetchMyOrders = (next?: string | null, limit = 20) =>
  api<OrderPage>(next ? pathFromApiUrl(next) : `/orders/mine/?limit=${limit}`);

export const cancelOrder = (reference: string, reason = "") =>
  api<OrderDetail>(`/orders/${encodeURIComponent(reference)}/cancel/`, {
    method: "POST",
    body: { reason },
    headers: guestHeaders(reference),
  });

export const reorder = (reference: string, replace = false) =>
  api<ReorderResponse>(`/orders/${encodeURIComponent(reference)}/reorder/`, { method: "POST", body: { replace } });

/** Start (or retry) a card payment. Returns the provider's hosted checkout URL. */
export const initialisePayment = (reference: string, saveCard = false) =>
  api<PaymentInitialised>("/payments/initialise/", {
    method: "POST",
    body: { order: reference, save_card: saveCard },
    headers: guestHeaders(reference),
  });

/** Ask the backend to confirm a payment with the provider. The browser's return is a hint, not proof. */
export const verifyPayment = (reference: string) =>
  api<PaymentVerification>(`/payments/verify/${encodeURIComponent(reference)}/`);

export const downloadReceipt = (reference: string) =>
  apiBlob(`/orders/${encodeURIComponent(reference)}/receipt/`, { headers: guestHeaders(reference) });

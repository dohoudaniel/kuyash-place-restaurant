/**
 * Kitchen Display System calls. Kitchen staff and managers only — the API
 * answers 403 to anyone else.
 */
import { api } from "./client";
import type { KDSItems, KDSQueue, KDSRiders, KDSSummary, KDSTicket } from "./types";

/** Where a ticket can be moved with the "advance" action. */
export type KitchenAdvanceTarget = "preparing" | "ready" | "out_for_delivery" | "delivered";

const ticketPath = (reference: string, action: string) => `/kds/orders/${encodeURIComponent(reference)}/${action}/`;

export const fetchKitchenQueue = () => api<KDSQueue>("/kds/orders/");

export const fetchKitchenSummary = () => api<KDSSummary>("/kds/summary/");

export const acceptTicket = (reference: string) => api<KDSTicket>(ticketPath(reference, "accept"), { method: "POST", body: {} });

/** `reason` is a code from the queue's `reject_reasons`; the API refuses anything else. */
export const rejectTicket = (reference: string, reason: string) =>
  api<KDSTicket>(ticketPath(reference, "reject"), { method: "POST", body: { reason } });

export const advanceTicket = (reference: string, to: KitchenAdvanceTarget) =>
  api<KDSTicket>(ticketPath(reference, "advance"), { method: "POST", body: { to } });

export const fetchRiders = () => api<KDSRiders>("/kds/riders/");

export const assignRider = (reference: string, riderId: string) =>
  api<unknown>(ticketPath(reference, "assign-rider"), { method: "POST", body: { rider: riderId } });

export const fetchKitchenItems = () => api<KDSItems>("/kds/items/");

/** "86" a dish (or bring it back). Applies to the public menu immediately. */
export const setItemAvailability = (slug: string, available: boolean) =>
  api<{ slug: string; is_available_now: boolean }>(`/kds/items/${encodeURIComponent(slug)}/availability/`, {
    method: "POST",
    body: { is_available_now: available },
  });

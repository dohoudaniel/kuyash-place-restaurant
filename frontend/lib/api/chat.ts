/**
 * The chat assistant. It answers only from stored FAQ entries, an order lookup
 * and opening hours, and hands anything else to the support team (ADR-012).
 */
import { api } from "./client";
import type { ChatEscalated, ChatExchange, ChatSession, ChatSessionCreated } from "./types";

const withToken = (token: string) => ({ "X-Chat-Token": token });
const base = (id: string) => `/support/chat/sessions/${encodeURIComponent(id)}`;

export const startChat = () => api<ChatSessionCreated>("/support/chat/sessions/", { method: "POST" });

export const fetchChat = (id: string, token: string) => api<ChatSession>(`${base(id)}/`, { headers: withToken(token) });

export const sendChatMessage = (id: string, token: string, body: string) =>
  api<ChatExchange>(`${base(id)}/messages/`, { method: "POST", body: { body }, headers: withToken(token) });

export interface EscalationInput {
  name?: string;
  email?: string;
  message?: string;
}

export const escalateChat = (id: string, token: string, input: EscalationInput) =>
  api<ChatEscalated>(`${base(id)}/escalate/`, { method: "POST", body: input, headers: withToken(token) });

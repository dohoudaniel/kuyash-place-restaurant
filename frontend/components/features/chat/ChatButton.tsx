"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import ChatPanel from "./ChatPanel";
import ChatEscalationForm from "./ChatEscalationForm";
import { ApiError } from "@/lib/api/client";
import { escalateChat, fetchChat, sendChatMessage, startChat, type EscalationInput } from "@/lib/api/chat";
import type { ChatMessage } from "@/lib/api/types";
import { clearStoredChat, loadStoredChat, storeChat, type StoredChat } from "@/lib/chat/session";
import { useAuthStore } from "@/lib/store/authStore";

type Status = "idle" | "loading" | "ready" | "sending" | "ended" | "error";

/** A conversation the server will no longer continue. */
const CLOSED_CODES = new Set(["chat_ended", "chat_expired"]);

/**
 * The chat assistant.
 *
 * Previously a keyword table in this file answered with a US phone number,
 * invented opening hours and "dishes start from ₦6.90", after a fake 600 ms
 * delay. Replies now come from the server, which can only repeat FAQ answers
 * the team wrote, look up an order, read the opening hours, or pass the
 * conversation to a person.
 */
export default function ChatButton() {
  const user = useAuthStore((state) => state.user);
  const [open, setOpen] = useState(false);
  const [hovered, setHovered] = useState(false);
  const [input, setInput] = useState("");
  const [session, setSession] = useState<StoredChat | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [status, setStatus] = useState<Status>("idle");
  const [notice, setNotice] = useState<string | null>(null);
  const [escalating, setEscalating] = useState(false);

  async function begin(fresh = false) {
    setStatus("loading");
    setNotice(null);
    setEscalating(false);
    try {
      const stored = fresh ? null : loadStoredChat();
      if (stored) {
        try {
          const existing = await fetchChat(stored.id, stored.token);
          setSession(stored);
          setMessages(existing.messages);
          if (existing.is_ended) {
            setStatus("ended");
            setNotice(existing.escalated_reference ? `Passed to our team — reference ${existing.escalated_reference}.` : "This conversation has ended.");
          } else {
            setStatus("ready");
          }
          return;
        } catch {
          clearStoredChat();
        }
      }
      const created = await startChat();
      const next = { id: created.id, token: created.token };
      storeChat(next);
      setSession(next);
      setMessages(created.messages);
      setStatus("ready");
    } catch {
      setStatus("error");
      setNotice("We couldn't reach our assistant. Please try again, or use the contact page.");
    }
  }

  function toggle() {
    const next = !open;
    setOpen(next);
    if (next && (status === "idle" || status === "error")) void begin();
  }

  async function send(text?: string) {
    const body = (text ?? input).trim();
    if (!body || !session || status !== "ready") return;
    setInput("");
    setNotice(null);
    setEscalating(false);
    const optimistic: ChatMessage = { sender: "user", body, created_at: new Date().toISOString(), suggestions: [], can_escalate: false, action: null };
    setMessages((current) => [...current, optimistic]);
    setStatus("sending");
    try {
      const exchange = await sendChatMessage(session.id, session.token, body);
      setMessages((current) => [...current.slice(0, -1), exchange.message, exchange.reply]);
      setStatus("ready");
      // Asked for a person outright: go straight to the handoff form.
      if (exchange.reply.can_escalate && exchange.reply.suggestions.length === 0) setEscalating(true);
    } catch (err) {
      setMessages((current) => current.slice(0, -1));
      if (err instanceof ApiError && CLOSED_CODES.has(err.code)) {
        clearStoredChat();
        setStatus("ended");
        setNotice(err.message);
        return;
      }
      setStatus("ready");
      setInput(body);
      if (err instanceof ApiError && err.code === "chat_limit") {
        setNotice(err.message);
        setEscalating(true);
        return;
      }
      setNotice(err instanceof ApiError ? err.message : "Message not sent. Check your connection and try again.");
    }
  }

  async function escalate(details: EscalationInput) {
    if (!session) return;
    const result = await escalateChat(session.id, session.token, details);
    const reply = result.reply;
    if (reply) setMessages((current) => [...current, reply]);
    setEscalating(false);
    setStatus("ended");
    setNotice(result.reference ? null : "Thanks — our team will be in touch.");
  }

  const last = messages[messages.length - 1];
  const lastFromBot = status === "ready" && !escalating && last?.sender === "bot";
  const suggestions = lastFromBot ? last.suggestions : [];
  const canEscalate = lastFromBot && last.can_escalate;

  const footer = escalating ? (
    <ChatEscalationForm signedInName={user ? user.full_name || user.email : null} onSubmit={escalate} onCancel={() => setEscalating(false)} />
  ) : status === "ended" || status === "error" ? (
    <div className="px-3 py-3" style={{ borderTop: "1px solid #F0F0F0" }}>
      <button
        onClick={() => void begin(true)}
        className="w-full py-2 rounded-full text-xs font-bold text-white transition-all hover:opacity-90"
        style={{ background: "var(--red)" }}
      >
        {status === "error" ? "Try again" : "Start a new conversation"}
      </button>
    </div>
  ) : undefined;

  return (
    <div className="fixed bottom-6 right-6 z-50 flex flex-col items-end gap-3">
      {/* ── Chat panel ── */}
      <AnimatePresence>
        {open && (
          <ChatPanel
            messages={messages}
            pending={status === "sending"}
            loading={status === "loading"}
            notice={notice}
            suggestions={suggestions}
            onSuggestion={(text) => void send(text)}
            canEscalate={canEscalate}
            onEscalate={() => setEscalating(true)}
            input={input}
            onInputChange={setInput}
            onSend={() => void send()}
            onClose={() => setOpen(false)}
            footer={footer}
          />
        )}
      </AnimatePresence>

      {/* ── Trigger button ── */}
      <div className="flex items-center gap-3">
        {/* Tooltip — only show when closed and hovered */}
        <AnimatePresence>
          {hovered && !open && (
            <motion.div
              initial={{ opacity: 0, x: 8 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: 8 }}
              transition={{ duration: 0.15 }}
              className="relative px-4 py-2 rounded-xl text-sm font-semibold text-white whitespace-nowrap pointer-events-none"
              style={{ background: "var(--black)", boxShadow: "0 4px 16px rgba(0,0,0,0.18)" }}
            >
              Chat with us
              <span
                className="absolute right-[-6px] top-1/2 -translate-y-1/2 w-0 h-0"
                style={{
                  borderTop: "6px solid transparent",
                  borderBottom: "6px solid transparent",
                  borderLeft: "6px solid var(--black)",
                }}
              />
            </motion.div>
          )}
        </AnimatePresence>

        <motion.button
          aria-label={open ? "Close chat" : "Open chat"}
          aria-expanded={open}
          onClick={toggle}
          onHoverStart={() => setHovered(true)}
          onHoverEnd={() => setHovered(false)}
          whileHover={{ scale: 1.08 }}
          whileTap={{ scale: 0.93 }}
          initial={{ opacity: 0, y: 24 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 1.2, ease: [0.25, 0.1, 0.25, 1] }}
          className="relative w-14 h-14 rounded-full flex items-center justify-center text-white"
          style={{
            background: "var(--red)",
            boxShadow: "0 8px 28px rgba(217,4,41,0.40), 0 2px 8px rgba(0,0,0,0.12)",
          }}
        >
          {/* Ping — only when closed */}
          {!open && (
            <span className="absolute inset-0 rounded-full animate-ping opacity-20" style={{ background: "var(--red)" }} />
          )}

          {/* Toggle icon */}
          <AnimatePresence mode="wait">
            {open ? (
              <motion.svg
                key="close"
                initial={{ rotate: -90, opacity: 0 }}
                animate={{ rotate: 0, opacity: 1 }}
                exit={{ rotate: 90, opacity: 0 }}
                transition={{ duration: 0.18 }}
                className="w-5 h-5 relative z-10"
                fill="none" stroke="currentColor" strokeWidth={2.5} viewBox="0 0 24 24"
              >
                <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
              </motion.svg>
            ) : (
              <motion.svg
                key="chat"
                initial={{ rotate: 90, opacity: 0 }}
                animate={{ rotate: 0, opacity: 1 }}
                exit={{ rotate: -90, opacity: 0 }}
                transition={{ duration: 0.18 }}
                className="w-6 h-6 relative z-10"
                fill="none" stroke="currentColor" strokeWidth={1.8} viewBox="0 0 24 24"
              >
                <path strokeLinecap="round" strokeLinejoin="round" d="M8 10h.01M12 10h.01M16 10h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
              </motion.svg>
            )}
          </AnimatePresence>
        </motion.button>
      </div>
    </div>
  );
}

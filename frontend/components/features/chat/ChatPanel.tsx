"use client";

import { useRef, useEffect, type ReactNode } from "react";
import { motion } from "framer-motion";
import ChatMessage from "./ChatMessage";
import type { ChatMessage as ChatMessageData } from "@/lib/api/types";

interface ChatPanelProps {
  messages: ChatMessageData[];
  /** Waiting for the assistant's reply. */
  pending: boolean;
  loading: boolean;
  notice: string | null;
  suggestions: string[];
  onSuggestion: (text: string) => void;
  canEscalate: boolean;
  onEscalate: () => void;
  input: string;
  onInputChange: (value: string) => void;
  onSend: () => void;
  onClose: () => void;
  /** Replaces the input row — the handoff form, or a "start again" prompt. */
  footer?: ReactNode;
}

export default function ChatPanel({
  messages,
  pending,
  loading,
  notice,
  suggestions,
  onSuggestion,
  canEscalate,
  onEscalate,
  input,
  onInputChange,
  onSend,
  onClose,
  footer,
}: ChatPanelProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, pending, notice, footer]);

  return (
    <motion.div
      role="dialog"
      aria-label="Chat with Kuyash Place"
      initial={{ opacity: 0, y: 20, scale: 0.95 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      exit={{ opacity: 0, y: 20, scale: 0.95 }}
      transition={{ duration: 0.25, ease: [0.25, 0.1, 0.25, 1] }}
      className="w-80 max-w-[calc(100vw-3rem)] rounded-2xl overflow-hidden flex flex-col"
      style={{
        background: "#fff",
        boxShadow: "0 24px 64px rgba(0,0,0,0.18), 0 4px 16px rgba(0,0,0,0.08)",
        border: "1px solid rgba(0,0,0,0.06)",
        maxHeight: footer ? "560px" : "460px",
      }}
    >
      {/* Header */}
      <div
        className="flex items-center justify-between px-4 py-3.5"
        style={{ background: "var(--red)" }}
      >
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-full bg-white/20 flex items-center justify-center text-base">
            👑
          </div>
          <div>
            <p className="text-sm font-bold text-white leading-none">Kuyash Place</p>
            <p className="text-[11px] text-white/70 mt-0.5">Tastefully Classy</p>
          </div>
        </div>
        <button
          onClick={onClose}
          className="text-white/70 hover:text-white transition-colors"
          aria-label="Close chat"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth={2.5} viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>

      {/* Messages */}
      <div className="flex-1 min-h-0 overflow-y-auto px-4 py-4 flex flex-col gap-3" style={{ maxHeight: "300px" }} aria-live="polite">
        {loading && (
          <p className="text-xs text-center" style={{ color: "var(--text-muted)" }}>Connecting…</p>
        )}
        {messages.map((msg, i) => (
          <ChatMessage key={i} message={msg} />
        ))}
        {pending && (
          <div className="flex justify-start" aria-label="The assistant is replying">
            <div className="px-3.5 py-3 rounded-2xl flex gap-1" style={{ background: "#F3F3F3", borderBottomLeftRadius: "4px" }}>
              {[0, 1, 2].map((dot) => (
                <span key={dot} className="w-1.5 h-1.5 rounded-full animate-pulse" style={{ background: "var(--text-muted)", animationDelay: `${dot * 150}ms` }} />
              ))}
            </div>
          </div>
        )}
        {(suggestions.length > 0 || canEscalate) && (
          <div className="flex flex-wrap gap-1.5">
            {suggestions.map((text) => (
              <button
                key={text}
                onClick={() => onSuggestion(text)}
                className="px-3 py-1.5 rounded-full text-xs font-semibold text-left transition-all hover:opacity-80"
                style={{ background: "#fff", color: "var(--red)", border: "1px solid var(--red)" }}
              >
                {text}
              </button>
            ))}
            {canEscalate && (
              <button
                onClick={onEscalate}
                className="px-3 py-1.5 rounded-full text-xs font-bold text-white transition-all hover:opacity-90"
                style={{ background: "var(--red)" }}
              >
                Pass to our team
              </button>
            )}
          </div>
        )}
        {notice && (
          <p role="status" className="text-xs text-center" style={{ color: "var(--text-muted)" }}>{notice}</p>
        )}
        <div ref={bottomRef} />
      </div>

      {footer ?? (
        /* Input */
        <div
          className="flex items-center gap-2 px-3 py-3"
          style={{ borderTop: "1px solid #F0F0F0" }}
        >
          <input
            type="text"
            value={input}
            onChange={(e) => onInputChange(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && onSend()}
            placeholder="Type a message…"
            aria-label="Message"
            maxLength={500}
            disabled={loading}
            className="flex-1 text-sm px-3.5 py-2 rounded-full outline-none transition-all"
            style={{ background: "#F3F3F3", color: "var(--black)", border: "1px solid transparent" }}
          />
          <button
            onClick={onSend}
            disabled={!input.trim() || pending || loading}
            className="w-9 h-9 rounded-full flex items-center justify-center text-white transition-all hover:opacity-90 active:scale-95 disabled:opacity-40"
            style={{ background: "var(--red)" }}
            aria-label="Send"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth={2.2} viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" d="M22 2L11 13M22 2l-7 20-4-9-9-4 20-7z" />
            </svg>
          </button>
        </div>
      )}
    </motion.div>
  );
}

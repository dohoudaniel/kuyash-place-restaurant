"use client";

import { useState, useRef, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";

interface Message {
  from: "user" | "bot";
  text: string;
}

const BOT_REPLIES: Record<string, string> = {
  default:      "Hi there! 👋 How can I help you today?",
  menu:         "Our menu has burgers, grills, salads, tacos, breakfast and desserts. Type 'order' to get started!",
  order:        "You can place an order by clicking the **Order Now** button at the top of the page, or call us on +1 555 96 36 36.",
  hours:        "We're open Mon–Sat 09:00am–10:00pm and Sunday 09:00am–08:00pm.",
  delivery:     "We deliver in an average of 30 minutes! 🚀 Fresh and hot to your door.",
  reservation:  "To make a reservation please scroll to the Reservations section or call +1 555 96 36 36.",
  hello:        "Hello! Welcome to Kuyash Place 👑 Tastefully Classy. How can I assist you?",
  hi:           "Hello! Welcome to Kuyash Place 👑 Tastefully Classy. How can I assist you?",
  price:        "Our dishes start from ₦6.90. Check out the full menu on this page for all prices.",
};

function getBotReply(input: string): string {
  const lower = input.toLowerCase();
  for (const key of Object.keys(BOT_REPLIES)) {
    if (key !== "default" && lower.includes(key)) return BOT_REPLIES[key];
  }
  return BOT_REPLIES.default;
}

export default function ChatButton() {
  const [open, setOpen]       = useState(false);
  const [hovered, setHovered] = useState(false);
  const [input, setInput]     = useState("");
  const [messages, setMessages] = useState<Message[]>([
    { from: "bot", text: "Hi! 👋 Welcome to Kuyash Place. Ask me anything — menu, hours, delivery, reservations!" },
  ]);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, open]);

  function send() {
    const text = input.trim();
    if (!text) return;
    const userMsg: Message = { from: "user", text };
    const botMsg: Message  = { from: "bot",  text: getBotReply(text) };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setTimeout(() => setMessages((prev) => [...prev, botMsg]), 600);
  }

  return (
    <div className="fixed bottom-6 right-6 z-50 flex flex-col items-end gap-3">

      {/* ── Chat panel ── */}
      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0, y: 20, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 20, scale: 0.95 }}
            transition={{ duration: 0.25, ease: [0.25, 0.1, 0.25, 1] }}
            className="w-80 rounded-2xl overflow-hidden flex flex-col"
            style={{
              background: "#fff",
              boxShadow: "0 24px 64px rgba(0,0,0,0.18), 0 4px 16px rgba(0,0,0,0.08)",
              border: "1px solid rgba(0,0,0,0.06)",
              maxHeight: "460px",
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
                onClick={() => setOpen(false)}
                className="text-white/70 hover:text-white transition-colors"
                aria-label="Close chat"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth={2.5} viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            {/* Messages */}
            <div className="flex-1 overflow-y-auto px-4 py-4 flex flex-col gap-3" style={{ maxHeight: "300px" }}>
              {messages.map((msg, i) => (
                <div key={i} className={`flex ${msg.from === "user" ? "justify-end" : "justify-start"}`}>
                  <div
                    className="px-3.5 py-2.5 rounded-2xl text-sm leading-relaxed max-w-[78%]"
                    style={
                      msg.from === "user"
                        ? { background: "var(--red)", color: "#fff", borderBottomRightRadius: "4px" }
                        : { background: "#F3F3F3", color: "var(--black)", borderBottomLeftRadius: "4px" }
                    }
                  >
                    {msg.text}
                  </div>
                </div>
              ))}
              <div ref={bottomRef} />
            </div>

            {/* Input */}
            <div
              className="flex items-center gap-2 px-3 py-3"
              style={{ borderTop: "1px solid #F0F0F0" }}
            >
              <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && send()}
                placeholder="Type a message…"
                className="flex-1 text-sm px-3.5 py-2 rounded-full outline-none transition-all"
                style={{ background: "#F3F3F3", color: "var(--black)", border: "1px solid transparent" }}
              />
              <button
                onClick={send}
                disabled={!input.trim()}
                className="w-9 h-9 rounded-full flex items-center justify-center text-white transition-all hover:opacity-90 active:scale-95 disabled:opacity-40"
                style={{ background: "var(--red)" }}
                aria-label="Send"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth={2.2} viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M22 2L11 13M22 2l-7 20-4-9-9-4 20-7z" />
                </svg>
              </button>
            </div>
          </motion.div>
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
          onClick={() => setOpen((v) => !v)}
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

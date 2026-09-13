"use client";

import Link from "next/link";
import type { ChatMessage as ChatMessageData } from "@/lib/api/types";

interface ChatMessageProps {
  message: Pick<ChatMessageData, "sender" | "body" | "action">;
}

export default function ChatMessage({ message }: ChatMessageProps) {
  const fromUser = message.sender === "user";
  return (
    <div className={`flex ${fromUser ? "justify-end" : "justify-start"}`}>
      <div
        className="px-3.5 py-2.5 rounded-2xl text-sm leading-relaxed max-w-[78%] whitespace-pre-line break-words"
        style={
          fromUser
            ? { background: "var(--red)", color: "#fff", borderBottomRightRadius: "4px" }
            : { background: "#F3F3F3", color: "var(--black)", borderBottomLeftRadius: "4px" }
        }
      >
        {message.body}
        {message.action && (
          <Link href={message.action.url} className="block mt-1.5 text-xs font-bold underline" style={{ color: "var(--red)" }}>
            {message.action.label} →
          </Link>
        )}
      </div>
    </div>
  );
}

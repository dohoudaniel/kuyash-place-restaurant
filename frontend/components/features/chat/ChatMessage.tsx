"use client";

interface Message {
  from: "user" | "bot";
  text: string;
}

interface ChatMessageProps {
  message: Message;
}

export default function ChatMessage({ message }: ChatMessageProps) {
  return (
    <div className={`flex ${message.from === "user" ? "justify-end" : "justify-start"}`}>
      <div
        className="px-3.5 py-2.5 rounded-2xl text-sm leading-relaxed max-w-[78%]"
        style={
          message.from === "user"
            ? { background: "var(--red)", color: "#fff", borderBottomRightRadius: "4px" }
            : { background: "#F3F3F3", color: "var(--black)", borderBottomLeftRadius: "4px" }
        }
      >
        {message.text}
      </div>
    </div>
  );
}

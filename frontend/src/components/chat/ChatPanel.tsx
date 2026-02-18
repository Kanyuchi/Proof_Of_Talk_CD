import { useState, useEffect, useRef } from "react";
import { X, Send, Brain, Sparkles } from "lucide-react";
import { useChat } from "../../hooks/useChat";
import { useAuth } from "../../hooks/useAuth";

const SUGGESTED_PROMPTS = [
  "Who should I meet at this conference?",
  "Tell me about CBDC-focused attendees",
  "Who is raising Series B capital?",
  "Find me someone interested in compliance infrastructure",
  "How should I prepare to meet Marcus Chen?",
];

interface ChatPanelProps {
  onClose: () => void;
}

export default function ChatPanel({ onClose }: ChatPanelProps) {
  const { user } = useAuth();
  const attendeeId = user?.attendee_id ?? undefined;
  const { history, isLoading, error, sendMessage } = useChat(attendeeId?.toString());
  const [input, setInput] = useState("");
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [history, isLoading]);

  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  const handleSend = async () => {
    const trimmed = input.trim();
    if (!trimmed || isLoading) return;
    setInput("");
    await sendMessage(trimmed);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-white/10">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-amber-400 to-amber-600 flex items-center justify-center">
            <Brain className="w-4 h-4 text-black" />
          </div>
          <div>
            <div className="text-sm font-semibold">AI Concierge</div>
            <div className="text-[10px] text-white/30">Proof of Talk 2026</div>
          </div>
        </div>
        <button
          onClick={onClose}
          className="w-7 h-7 flex items-center justify-center rounded-lg text-white/40 hover:text-white hover:bg-white/5 transition-all"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {history.length === 0 && (
          <div className="space-y-4">
            <div className="flex items-start gap-2.5">
              <div className="w-7 h-7 rounded-full bg-amber-400/10 flex items-center justify-center shrink-0 mt-0.5">
                <Sparkles className="w-3.5 h-3.5 text-amber-400" />
              </div>
              <div className="flex-1 bg-white/5 rounded-2xl rounded-tl-sm p-3 text-sm text-white/70">
                Hello! I'm your AI Concierge for Proof of Talk 2026. I can help you discover who to meet, prepare for meetings, and find non-obvious connections among our attendees. How can I help?
              </div>
            </div>
            <div className="space-y-2">
              <p className="text-[10px] text-white/20 uppercase font-medium px-1">Suggested questions</p>
              {SUGGESTED_PROMPTS.map((prompt) => (
                <button
                  key={prompt}
                  onClick={() => sendMessage(prompt)}
                  className="block w-full text-left px-3 py-2 rounded-xl bg-white/[0.03] border border-white/10 text-sm text-white/50 hover:text-white/80 hover:border-amber-400/20 transition-all"
                >
                  {prompt}
                </button>
              ))}
            </div>
          </div>
        )}

        {history.map((msg, i) => (
          <div
            key={i}
            className={`flex items-start gap-2.5 ${msg.role === "user" ? "flex-row-reverse" : ""}`}
          >
            <div
              className={`w-7 h-7 rounded-full flex items-center justify-center shrink-0 mt-0.5 ${
                msg.role === "user"
                  ? "bg-amber-400/20"
                  : "bg-amber-400/10"
              }`}
            >
              {msg.role === "user" ? (
                <span className="text-xs font-bold text-amber-400">
                  {user?.full_name?.[0] ?? "U"}
                </span>
              ) : (
                <Sparkles className="w-3.5 h-3.5 text-amber-400" />
              )}
            </div>
            <div
              className={`flex-1 max-w-[85%] rounded-2xl p-3 text-sm leading-relaxed ${
                msg.role === "user"
                  ? "bg-amber-400/10 text-white rounded-tr-sm"
                  : "bg-white/5 text-white/80 rounded-tl-sm"
              }`}
            >
              {msg.content}
            </div>
          </div>
        ))}

        {isLoading && (
          <div className="flex items-start gap-2.5">
            <div className="w-7 h-7 rounded-full bg-amber-400/10 flex items-center justify-center shrink-0">
              <Sparkles className="w-3.5 h-3.5 text-amber-400" />
            </div>
            <div className="bg-white/5 rounded-2xl rounded-tl-sm px-4 py-3">
              <div className="flex gap-1">
                {[0, 1, 2].map((i) => (
                  <div
                    key={i}
                    className="w-1.5 h-1.5 rounded-full bg-amber-400/60 animate-bounce"
                    style={{ animationDelay: `${i * 0.15}s` }}
                  />
                ))}
              </div>
            </div>
          </div>
        )}

        {error && (
          <div className="text-xs text-red-400 text-center py-1">{error}</div>
        )}

        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div className="p-3 border-t border-white/10">
        <div className="flex items-center gap-2 bg-white/5 border border-white/10 rounded-xl px-3 py-2 focus-within:border-amber-400/30 transition-all">
          <input
            ref={inputRef}
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask about attendees, meetings, connections…"
            className="flex-1 bg-transparent text-sm text-white placeholder:text-white/20 focus:outline-none"
          />
          <button
            onClick={handleSend}
            disabled={!input.trim() || isLoading}
            className="w-7 h-7 flex items-center justify-center rounded-lg bg-amber-400 text-black hover:bg-amber-300 transition-all disabled:opacity-40 shrink-0"
          >
            <Send className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>
    </div>
  );
}

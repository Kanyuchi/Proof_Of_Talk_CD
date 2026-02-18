import { useState } from "react";
import { useSearchParams } from "react-router-dom";
import { MessageSquare, Send, Crown, Mic, Megaphone, User } from "lucide-react";
import { useConversations, useConversation, useSendMessage } from "../hooks/useMessages";
import { useAuth } from "../hooks/useAuth";

const ticketColors: Record<string, string> = {
  vip: "text-amber-400",
  speaker: "text-purple-400",
  sponsor: "text-emerald-400",
  delegate: "text-blue-400",
};

const ticketIcons: Record<string, React.ReactNode> = {
  vip: <Crown className="w-3 h-3" />,
  speaker: <Mic className="w-3 h-3" />,
  sponsor: <Megaphone className="w-3 h-3" />,
  delegate: <User className="w-3 h-3" />,
};

function formatTime(iso: string) {
  const d = new Date(iso);
  const now = new Date();
  const diff = now.getTime() - d.getTime();
  if (diff < 60_000) return "Just now";
  if (diff < 3_600_000) return `${Math.floor(diff / 60_000)}m ago`;
  if (diff < 86_400_000) return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  return d.toLocaleDateString([], { month: "short", day: "numeric" });
}

export default function Messages() {
  const { isAuthenticated } = useAuth();
  const [searchParams, setSearchParams] = useSearchParams();
  const activeMatchId = searchParams.get("match");
  const [messageInput, setMessageInput] = useState("");

  const { data: convsData, isLoading: loadingConvs } = useConversations();
  const { data: thread, isLoading: loadingThread } = useConversation(activeMatchId);
  const sendMutation = useSendMessage(activeMatchId);

  const handleSend = async () => {
    const content = messageInput.trim();
    if (!content || sendMutation.isPending) return;
    setMessageInput("");
    await sendMutation.mutateAsync(content);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  if (!isAuthenticated) {
    return (
      <div className="flex flex-col items-center justify-center py-24 text-center">
        <MessageSquare className="w-12 h-12 text-white/10 mb-4" />
        <h2 className="text-xl font-bold mb-2">Sign in to message</h2>
        <p className="text-white/40 text-sm">
          Accept a match to start a direct conversation with them.
        </p>
      </div>
    );
  }

  const conversations = convsData?.conversations ?? [];

  return (
    <div className="flex h-[calc(100vh-8rem)] -mt-8 -mx-6 overflow-hidden rounded-none">
      {/* Left panel — conversation list */}
      <div className="w-72 shrink-0 border-r border-white/10 flex flex-col bg-white/[0.01]">
        <div className="px-4 py-4 border-b border-white/10">
          <h2 className="font-semibold">Messages</h2>
          <p className="text-xs text-white/30 mt-0.5">{conversations.length} conversations</p>
        </div>

        <div className="flex-1 overflow-y-auto">
          {loadingConvs ? (
            <div className="text-center py-8 text-white/20 text-sm">Loading…</div>
          ) : conversations.length === 0 ? (
            <div className="p-4 text-center">
              <MessageSquare className="w-8 h-8 text-white/10 mx-auto mb-2" />
              <p className="text-xs text-white/30">
                No conversations yet. Accept a match to start messaging.
              </p>
            </div>
          ) : (
            conversations.map((conv) => (
              <button
                key={conv.match_id}
                onClick={() => setSearchParams({ match: conv.match_id })}
                className={`w-full px-4 py-3 text-left border-b border-white/5 hover:bg-white/5 transition-all ${
                  activeMatchId === conv.match_id ? "bg-white/5" : ""
                }`}
              >
                <div className="flex items-center gap-2.5">
                  <div className="w-9 h-9 rounded-full bg-gradient-to-br from-white/5 to-white/10 flex items-center justify-center text-white/60 font-semibold shrink-0">
                    {conv.other_attendee_name[0]}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-1.5">
                      <span className="text-sm font-medium truncate">{conv.other_attendee_name}</span>
                      <span className={`shrink-0 ${ticketColors[conv.other_attendee_ticket] ?? "text-white/40"}`}>
                        {ticketIcons[conv.other_attendee_ticket]}
                      </span>
                      {conv.unread_count > 0 && (
                        <span className="ml-auto shrink-0 w-5 h-5 rounded-full bg-amber-400 text-black text-[10px] font-bold flex items-center justify-center">
                          {conv.unread_count}
                        </span>
                      )}
                    </div>
                    <div className="text-[11px] text-white/30 truncate">{conv.other_attendee_company}</div>
                    {conv.last_message && (
                      <div className="text-xs text-white/25 truncate mt-0.5">{conv.last_message}</div>
                    )}
                  </div>
                </div>
              </button>
            ))
          )}
        </div>
      </div>

      {/* Right panel — message thread */}
      <div className="flex-1 flex flex-col">
        {!activeMatchId ? (
          <div className="flex-1 flex flex-col items-center justify-center text-center">
            <MessageSquare className="w-12 h-12 text-white/10 mb-3" />
            <p className="text-white/30 text-sm">Select a conversation to start chatting</p>
          </div>
        ) : loadingThread ? (
          <div className="flex-1 flex items-center justify-center text-white/20 text-sm">Loading…</div>
        ) : (
          <>
            {/* Thread header */}
            {thread?.other_attendee && (
              <div className="px-5 py-4 border-b border-white/10 flex items-center gap-3">
                <div className="w-9 h-9 rounded-full bg-gradient-to-br from-white/5 to-white/10 flex items-center justify-center text-white/60 font-semibold">
                  {thread.other_attendee.name[0]}
                </div>
                <div>
                  <div className="font-semibold text-sm">{thread.other_attendee.name}</div>
                  <div className="text-xs text-white/40">
                    {thread.other_attendee.title} · {thread.other_attendee.company}
                  </div>
                </div>
              </div>
            )}

            {/* Messages */}
            <div className="flex-1 overflow-y-auto p-4 space-y-3">
              {thread?.messages.length === 0 && (
                <div className="text-center py-8 text-white/20 text-sm">
                  No messages yet. Say hello!
                </div>
              )}
              {thread?.messages.map((msg) => (
                <div
                  key={msg.id}
                  className={`flex items-end gap-2 ${msg.is_mine ? "flex-row-reverse" : ""}`}
                >
                  <div
                    className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold shrink-0 ${
                      msg.is_mine ? "bg-amber-400/20 text-amber-400" : "bg-white/10 text-white/50"
                    }`}
                  >
                    {msg.sender_name[0]}
                  </div>
                  <div className="max-w-[70%]">
                    <div
                      className={`px-4 py-2.5 rounded-2xl text-sm ${
                        msg.is_mine
                          ? "bg-amber-400/15 text-white rounded-br-sm"
                          : "bg-white/5 text-white/80 rounded-bl-sm"
                      }`}
                    >
                      {msg.content}
                    </div>
                    <div className={`text-[10px] text-white/20 mt-1 ${msg.is_mine ? "text-right" : ""}`}>
                      {formatTime(msg.created_at)}
                    </div>
                  </div>
                </div>
              ))}
            </div>

            {/* Input */}
            <div className="p-4 border-t border-white/10">
              <div className="flex items-center gap-2 bg-white/5 border border-white/10 rounded-xl px-4 py-2.5 focus-within:border-amber-400/30 transition-all">
                <input
                  type="text"
                  value={messageInput}
                  onChange={(e) => setMessageInput(e.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder="Type a message…"
                  className="flex-1 bg-transparent text-sm text-white placeholder:text-white/20 focus:outline-none"
                />
                <button
                  onClick={handleSend}
                  disabled={!messageInput.trim() || sendMutation.isPending}
                  className="w-8 h-8 flex items-center justify-center rounded-lg bg-amber-400 text-black hover:bg-amber-300 transition-all disabled:opacity-40 shrink-0"
                >
                  <Send className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}

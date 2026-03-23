import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  MessageCircle, Send, ArrowLeft, Users, Clock, Star,
} from "lucide-react";
import { listThreads, getThread, postToThread } from "../api/client";
import type { ThreadSummary } from "../api/client";

function timeAgo(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "Just now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  const days = Math.floor(hrs / 24);
  return `${days}d ago`;
}

export default function Threads() {
  const [activeSlug, setActiveSlug] = useState<string | null>(null);
  const [input, setInput] = useState("");
  const queryClient = useQueryClient();

  const { data: threadList, isLoading: loadingList } = useQuery({
    queryKey: ["threads"],
    queryFn: listThreads,
    staleTime: 10_000,
  });

  const { data: threadDetail, isLoading: loadingThread } = useQuery({
    queryKey: ["thread", activeSlug],
    queryFn: () => getThread(activeSlug!),
    enabled: !!activeSlug,
    staleTime: 5_000,
    refetchInterval: 5_000,
  });

  const postMutation = useMutation({
    mutationFn: (content: string) => postToThread(activeSlug!, content),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["thread", activeSlug] });
      queryClient.invalidateQueries({ queryKey: ["threads"] });
      setInput("");
    },
  });

  const handleSend = () => {
    const trimmed = input.trim();
    if (!trimmed || !activeSlug) return;
    postMutation.mutate(trimmed);
  };

  const threads = threadList?.threads ?? [];

  // Thread list view
  if (!activeSlug) {
    return (
      <div className="max-w-3xl mx-auto space-y-6">
        <div className="text-center space-y-2 pt-4">
          <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-[#E76315]/10 border border-[#E76315]/20">
            <MessageCircle className="w-4 h-4 text-[#E76315]" />
            <span className="text-sm font-medium text-[#E76315]">Pre-Event Warm-Up</span>
          </div>
          <h1 className="text-2xl font-bold mt-3">Discussion Threads</h1>
          <p className="text-white/40 text-sm max-w-md mx-auto">
            Start conversations with fellow attendees before the event.
            Threads are organised by sector — your sectors are highlighted.
          </p>
        </div>

        {loadingList ? (
          <div className="text-center py-12">
            <div className="inline-block w-6 h-6 border-2 border-[#E76315] border-t-transparent rounded-full animate-spin" />
          </div>
        ) : (
          <div className="space-y-3">
            {threads.map((t: ThreadSummary) => (
              <button
                key={t.slug}
                onClick={() => setActiveSlug(t.slug)}
                className={`w-full text-left p-5 rounded-xl border transition-all hover:border-white/20 ${
                  t.is_member
                    ? "bg-[#E76315]/[0.04] border-[#E76315]/20 hover:border-[#E76315]/40"
                    : "bg-white/[0.03] border-white/10"
                }`}
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <h3 className="font-semibold truncate">{t.title}</h3>
                      {t.is_member && (
                        <Star className="w-3.5 h-3.5 text-[#E76315] shrink-0" fill="currentColor" />
                      )}
                    </div>
                    {t.description && (
                      <p className="text-sm text-white/40 mt-1 line-clamp-1">{t.description}</p>
                    )}
                  </div>
                  <div className="text-right shrink-0">
                    <div className="flex items-center gap-1 text-white/40">
                      <MessageCircle className="w-3.5 h-3.5" />
                      <span className="text-sm font-medium">{t.post_count}</span>
                    </div>
                    {t.latest_post_at && (
                      <div className="flex items-center gap-1 text-[10px] text-white/30 mt-1">
                        <Clock className="w-3 h-3" />
                        {timeAgo(t.latest_post_at)}
                      </div>
                    )}
                  </div>
                </div>
              </button>
            ))}
          </div>
        )}
      </div>
    );
  }

  // Thread detail view
  const thread = threadDetail?.thread;
  const posts = threadDetail?.posts ?? [];

  return (
    <div className="max-w-3xl mx-auto space-y-4">
      {/* Header */}
      <div className="flex items-center gap-3">
        <button
          onClick={() => setActiveSlug(null)}
          className="p-2 rounded-lg hover:bg-white/5 text-white/40 hover:text-white transition-all"
        >
          <ArrowLeft className="w-5 h-5" />
        </button>
        <div className="flex-1 min-w-0">
          <h1 className="text-xl font-bold truncate">{thread?.title ?? "Loading…"}</h1>
          {thread?.description && (
            <p className="text-sm text-white/40 truncate">{thread.description}</p>
          )}
        </div>
        <div className="flex items-center gap-1 text-white/30 text-sm">
          <Users className="w-4 h-4" />
          {posts.length} post{posts.length !== 1 ? "s" : ""}
        </div>
      </div>

      {/* Posts */}
      <div className="space-y-3 min-h-[200px]">
        {loadingThread ? (
          <div className="text-center py-12">
            <div className="inline-block w-6 h-6 border-2 border-[#E76315] border-t-transparent rounded-full animate-spin" />
          </div>
        ) : posts.length === 0 ? (
          <div className="text-center py-16 text-white/30">
            <MessageCircle className="w-8 h-8 mx-auto mb-3 opacity-30" />
            <p>No posts yet. Be the first to start the conversation.</p>
          </div>
        ) : (
          posts.map((post) => (
            <div
              key={post.id}
              className={`p-4 rounded-xl border ${
                post.is_mine
                  ? "bg-[#E76315]/[0.06] border-[#E76315]/15"
                  : "bg-white/[0.03] border-white/10"
              }`}
            >
              <div className="flex items-center gap-2 mb-2">
                <div className="w-7 h-7 rounded-full bg-gradient-to-br from-[#E76315]/20 to-[#D35400]/20 flex items-center justify-center text-[#E76315] text-xs font-bold shrink-0">
                  {post.sender_name.charAt(0)}
                </div>
                <div className="flex-1 min-w-0">
                  <span className="text-sm font-medium">{post.sender_name}</span>
                  <span className="text-xs text-white/30 ml-2">
                    {post.sender_title} · {post.sender_company}
                  </span>
                </div>
                <span className="text-[10px] text-white/30 shrink-0">{timeAgo(post.created_at)}</span>
              </div>
              <p className="text-sm text-white/70 leading-relaxed pl-9">{post.content}</p>
            </div>
          ))
        )}
      </div>

      {/* Input */}
      <div className="sticky bottom-4 flex items-center gap-2 p-3 rounded-xl bg-[#0d0d1a]/90 border border-white/10 backdrop-blur-sm">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && handleSend()}
          placeholder="Share a thought with the group…"
          maxLength={2000}
          className="flex-1 bg-transparent text-sm text-white placeholder:text-white/30 outline-none"
        />
        <button
          onClick={handleSend}
          disabled={!input.trim() || postMutation.isPending}
          className="p-2.5 rounded-lg bg-[#E76315] text-white disabled:opacity-30 hover:bg-[#D35400] transition-all"
        >
          <Send className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
}

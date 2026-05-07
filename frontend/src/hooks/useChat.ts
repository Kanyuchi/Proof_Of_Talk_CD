import { useState, useCallback, useEffect } from "react";
import type { ChatMessage } from "../types";
import { chatWithConcierge, fetchChatHistory, clearChatHistory } from "../api/client";

export function useChat(attendeeId?: string) {
  const [history, setHistory] = useState<ChatMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isLoadingHistory, setIsLoadingHistory] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // On mount (and when attendee changes), pull persisted history from the
  // server. Backend writes every exchange to chat_messages so users can
  // resume a conversation across sessions / devices.
  useEffect(() => {
    if (!attendeeId) return;
    let cancelled = false;
    setIsLoadingHistory(true);
    fetchChatHistory()
      .then(({ messages }) => {
        if (cancelled) return;
        setHistory(
          messages.map((m) => ({
            role: m.role,
            content: m.content,
          }))
        );
      })
      .catch(() => {
        // Silent — empty history is a fine fallback
      })
      .finally(() => {
        if (!cancelled) setIsLoadingHistory(false);
      });
    return () => {
      cancelled = true;
    };
  }, [attendeeId]);

  const sendMessage = useCallback(
    async (message: string) => {
      const userMsg: ChatMessage = { role: "user", content: message };
      const newHistory = [...history, userMsg];
      setHistory(newHistory);
      setIsLoading(true);
      setError(null);

      try {
        const { response } = await chatWithConcierge({
          message,
          attendee_id: attendeeId,
          history: history, // server-side history wins for authed users; this is a fallback
        });
        setHistory([...newHistory, { role: "assistant", content: response }]);
      } catch {
        setError("Failed to get a response. Please try again.");
        // Revert user message on error
        setHistory(history);
      } finally {
        setIsLoading(false);
      }
    },
    [history, attendeeId]
  );

  const clearHistory = useCallback(async () => {
    setHistory([]);
    setError(null);
    if (attendeeId) {
      try {
        await clearChatHistory();
      } catch {
        // Best-effort — local UI is already cleared
      }
    }
  }, [attendeeId]);

  return { history, isLoading, isLoadingHistory, error, sendMessage, clearHistory };
}

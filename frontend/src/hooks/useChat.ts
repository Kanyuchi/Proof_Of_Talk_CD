import { useState, useCallback } from "react";
import type { ChatMessage } from "../types";
import { chatWithConcierge } from "../api/client";

export function useChat(attendeeId?: string) {
  const [history, setHistory] = useState<ChatMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

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
          history: history, // send existing history (before current message)
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

  const clearHistory = useCallback(() => {
    setHistory([]);
    setError(null);
  }, []);

  return { history, isLoading, error, sendMessage, clearHistory };
}

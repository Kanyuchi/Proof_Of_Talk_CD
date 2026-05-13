import { useState, useCallback, useEffect } from "react";
import type { ChatMessage } from "../types";
import {
  chatWithConcierge,
  fetchChatHistory,
  clearChatHistory,
  getProfilePrompt,
  type OfferableField,
} from "../api/client";

export interface ProfilePromptOffer {
  field: OfferableField;
  current_completeness_pct: number;
  is_sparse: boolean;
}

export function useChat(attendeeId?: string) {
  const [history, setHistory] = useState<ChatMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isLoadingHistory, setIsLoadingHistory] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [profilePromptOffer, setProfilePromptOffer] =
    useState<ProfilePromptOffer | null>(null);

  // On mount (and when attendee changes), pull persisted history from the
  // server AND check whether a proactive profile-field offer should fire.
  // We surface the offer only when chat history is empty — otherwise the
  // user is mid-conversation and a nag would be intrusive.
  useEffect(() => {
    if (!attendeeId) return;
    let cancelled = false;
    setIsLoadingHistory(true);

    Promise.allSettled([fetchChatHistory(), getProfilePrompt()])
      .then(([historyRes, promptRes]) => {
        if (cancelled) return;

        const messages =
          historyRes.status === "fulfilled" ? historyRes.value.messages : [];
        setHistory(messages.map((m) => ({ role: m.role, content: m.content })));

        if (
          promptRes.status === "fulfilled" &&
          promptRes.value.field &&
          messages.length === 0
        ) {
          setProfilePromptOffer({
            field: promptRes.value.field,
            current_completeness_pct: promptRes.value.current_completeness_pct,
            is_sparse: promptRes.value.is_sparse,
          });
        }
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
      // First real user message hides the proactive offer — we never want
      // the offer card competing with an in-progress conversation.
      setProfilePromptOffer(null);

      try {
        const { response } = await chatWithConcierge({
          message,
          attendee_id: attendeeId,
          history: history,
        });
        setHistory([...newHistory, { role: "assistant", content: response }]);
      } catch {
        setError("Failed to get a response. Please try again.");
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

  // Allow the offer component to dismiss itself locally after the user
  // accepts/declines/saves. Backend persistence is the source of truth
  // for future visits; this just clears the in-session card.
  const dismissProfilePromptOffer = useCallback(() => {
    setProfilePromptOffer(null);
  }, []);

  return {
    history,
    isLoading,
    isLoadingHistory,
    error,
    sendMessage,
    clearHistory,
    profilePromptOffer,
    dismissProfilePromptOffer,
  };
}

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  listConversations,
  getConversation,
  sendMessage,
  getUnreadCount,
} from "../api/client";

function isAuthed() {
  return !!localStorage.getItem("token");
}

export function useConversations() {
  return useQuery({
    queryKey: ["conversations"],
    queryFn: listConversations,
    enabled: isAuthed(),
    refetchInterval: 5_000,
    staleTime: 3_000,
  });
}

export function useConversation(matchId: string | null) {
  return useQuery({
    queryKey: ["conversation", matchId],
    queryFn: () => getConversation(matchId!),
    enabled: !!matchId && isAuthed(),
    refetchInterval: 3_000,
    staleTime: 1_000,
  });
}

export function useSendMessage(matchId: string | null) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (content: string) => sendMessage(matchId!, content),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["conversation", matchId] });
      queryClient.invalidateQueries({ queryKey: ["conversations"] });
    },
  });
}

export function useUnreadCount() {
  return useQuery({
    queryKey: ["unread-count"],
    queryFn: getUnreadCount,
    enabled: isAuthed(),
    refetchInterval: 10_000,
    staleTime: 5_000,
  });
}

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { getMatches, updateMatchStatus, scheduleMeeting, updateMeetingFeedback, deferMatch } from "../api/client";
import type { Match, MatchListResult } from "../types";

// 2026-05-30: Previously fell back to demoMatches (Amara/Marcus seed data) on
// any error or empty result. That masked transient /matches/{id} failures by
// painting Amara Okafor's identity onto the viewer's page — a real attendee
// (Kiril Tsenkov, Nexo) saw himself as Amara with VaultBridge demo matches.
// The hook now propagates loading/error/empty cleanly; consumer pages render
// explicit states. Matches the post-2026-04-14 pattern in useDashboard.ts.
export function useMatches(attendeeId: string | undefined) {
  return useQuery<MatchListResult>({
    queryKey: ["matches", attendeeId],
    queryFn: () => getMatches(attendeeId!),
    enabled: !!attendeeId,
    staleTime: 30_000,
  });
}

export function useUpdateMatchStatus(attendeeId: string | undefined) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      matchId,
      status,
      decline_reason,
    }: {
      matchId: string;
      status: "accepted" | "declined" | "met";
      decline_reason?: string;
    }) => updateMatchStatus(matchId, status, decline_reason),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["matches", attendeeId] });
    },
    // Optimistic update: immediately reflect status in UI even if API is slow/offline
    onMutate: async ({ matchId, status }) => {
      await queryClient.cancelQueries({ queryKey: ["matches", attendeeId] });
      queryClient.setQueryData(["matches", attendeeId], (old: { matches: Match[] } | undefined) => {
        if (!old) return old;
        return {
          ...old,
          matches: old.matches.map((m) => (m.id === matchId ? { ...m, status } : m)),
        };
      });
    },
  });
}

export function useDeferMatch(attendeeId: string | undefined) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (matchId: string) => deferMatch(matchId),
    // Optimistically drop the deferred card so the next-best slides in instantly.
    onMutate: async (matchId: string) => {
      await queryClient.cancelQueries({ queryKey: ["matches", attendeeId] });
      const prev = queryClient.getQueryData(["matches", attendeeId]);
      queryClient.setQueryData(
        ["matches", attendeeId],
        (old: { matches: { id: string }[] } | undefined) => {
          if (!old) return old;
          return { ...old, matches: old.matches.filter((m) => m.id !== matchId) };
        }
      );
      return { prev };
    },
    onError: (_e, _id, ctx) => {
      if (ctx?.prev) queryClient.setQueryData(["matches", attendeeId], ctx.prev);
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ["matches", attendeeId] });
    },
  });
}

export function useScheduleMeeting(attendeeId: string | undefined) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      matchId,
      meeting_time,
      meeting_location,
    }: {
      matchId: string;
      meeting_time: string;
      meeting_location?: string;
    }) => scheduleMeeting(matchId, meeting_time, meeting_location),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["matches", attendeeId] });
    },
    onError: (err: unknown) => {
      // 409 = the slot was just taken by another match; refresh so the stale chip disappears.
      const status = (err as { response?: { status?: number } })?.response?.status;
      if (status === 409) {
        queryClient.invalidateQueries({ queryKey: ["matches", attendeeId] });
      }
    },
  });
}

export function useMeetingFeedback(attendeeId: string | undefined) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      matchId,
      meeting_outcome,
      satisfaction_score,
      met_at,
      hidden_by_user,
    }: {
      matchId: string;
      meeting_outcome?: string;
      satisfaction_score?: number;
      met_at?: string;
      hidden_by_user?: boolean;
    }) =>
      updateMeetingFeedback(matchId, {
        meeting_outcome,
        satisfaction_score,
        met_at,
        hidden_by_user,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["matches", attendeeId] });
    },
  });
}

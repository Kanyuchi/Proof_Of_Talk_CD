import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { getMatches, updateMatchStatus, scheduleMeeting, updateMeetingFeedback, deferMatch } from "../api/client";
import { demoMatches } from "../data/demo";

export function useMatches(attendeeId: string | undefined) {
  return useQuery({
    queryKey: ["matches", attendeeId],
    queryFn: async () => {
      if (!attendeeId) return { matches: demoMatches, attendee_id: "" };
      try {
        const result = await getMatches(attendeeId);
        return result.matches.length > 0 ? result : { matches: demoMatches, attendee_id: attendeeId };
      } catch {
        return { matches: demoMatches, attendee_id: attendeeId };
      }
    },
    enabled: !!attendeeId,
    staleTime: 30_000,
  });
}

// Mirror of the backend's _compute_overall_status (matches.py). The aggregate
// `status` is the single source of truth for `isMutual` in the cards, so it must
// ONLY read "accepted" when BOTH sides accepted. Optimistically stamping the raw
// clicked value onto `status` was the cause of the "Mutual match — both accepted!"
// label appearing the instant the viewer accepted, before the other party had.
function computeOverallStatus(statusA: string, statusB: string): string {
  if (statusA === "declined" || statusB === "declined") return "declined";
  if (statusA === "met" && statusB === "met") return "met";
  const acceptedish = (s: string) => s === "accepted" || s === "met";
  if (acceptedish(statusA) && acceptedish(statusB)) return "accepted";
  return "pending";
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
    // Optimistic update: immediately reflect status in UI even if API is slow/offline.
    // Set only the VIEWER's per-side status (status_a/status_b) and recompute the
    // aggregate the same way the backend does, so a one-sided accept stays "pending"
    // (no false "Mutual match" flash before the other party responds).
    onMutate: async ({ matchId, status }) => {
      await queryClient.cancelQueries({ queryKey: ["matches", attendeeId] });
      const prev = queryClient.getQueryData(["matches", attendeeId]);
      queryClient.setQueryData(["matches", attendeeId], (old: { matches: typeof demoMatches } | undefined) => {
        if (!old) return old;
        return {
          ...old,
          matches: old.matches.map((m) => {
            if (m.id !== matchId) return m;
            const iAmA = m.attendee_a_id === attendeeId;
            const statusA = iAmA ? status : m.status_a;
            const statusB = iAmA ? m.status_b : status;
            return {
              ...m,
              status_a: statusA,
              status_b: statusB,
              status: computeOverallStatus(statusA, statusB),
            };
          }),
        };
      });
      return { prev };
    },
    onError: (_e, _vars, ctx) => {
      if (ctx?.prev) queryClient.setQueryData(["matches", attendeeId], ctx.prev);
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

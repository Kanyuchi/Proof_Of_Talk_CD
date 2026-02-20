import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { getMatches, updateMatchStatus, scheduleMeeting } from "../api/client";
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

export function useUpdateMatchStatus(attendeeId: string | undefined) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ matchId, status }: { matchId: string; status: "accepted" | "declined" }) =>
      updateMatchStatus(matchId, status),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["matches", attendeeId] });
    },
    // Optimistic update: immediately reflect status in UI even if API is slow/offline
    onMutate: async ({ matchId, status }) => {
      await queryClient.cancelQueries({ queryKey: ["matches", attendeeId] });
      queryClient.setQueryData(["matches", attendeeId], (old: { matches: typeof demoMatches } | undefined) => {
        if (!old) return old;
        return {
          ...old,
          matches: old.matches.map((m) => (m.id === matchId ? { ...m, status } : m)),
        };
      });
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
  });
}

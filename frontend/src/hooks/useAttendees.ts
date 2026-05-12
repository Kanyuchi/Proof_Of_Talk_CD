import { useQuery } from "@tanstack/react-query";
import { listAttendees } from "../api/client";
import { demoAttendees } from "../data/demo";

export function useAttendees(params?: { ticket_type?: string; limit?: number }) {
  return useQuery({
    queryKey: ["attendees", params],
    queryFn: async () => {
      try {
        // Limit set to 1000 (backend cap, raised today from 200). At 353
        // attendees the previous 200 cap silently truncated the list, so
        // searching for anyone past position 200 (Laurence Filby,
        // Kaushik Sthankiya, etc.) returned "No attendees found" even
        // though the header showed "353 decision-makers registered".
        const result = await listAttendees({ limit: params?.limit ?? 1000 });
        return result.attendees.length > 0
          ? result
          : { attendees: demoAttendees, total: demoAttendees.length };
      } catch {
        return { attendees: demoAttendees, total: demoAttendees.length };
      }
    },
    // No placeholderData — the demo seeds (5 entries) used to flash through
    // the UI as "5 decision-makers registered" before the real data resolved.
    staleTime: 30_000,
  });
}

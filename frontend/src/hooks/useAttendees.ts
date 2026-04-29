import { useQuery } from "@tanstack/react-query";
import { listAttendees } from "../api/client";
import { demoAttendees } from "../data/demo";

export function useAttendees(params?: { ticket_type?: string; limit?: number }) {
  return useQuery({
    queryKey: ["attendees", params],
    queryFn: async () => {
      try {
        // Limit raised to 200 (the backend's max) so the list reflects the
        // real attendee count, not a stale-looking 100 cap.
        const result = await listAttendees({ limit: params?.limit ?? 200 });
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

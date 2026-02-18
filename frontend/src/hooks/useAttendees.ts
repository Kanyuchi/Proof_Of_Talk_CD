import { useQuery } from "@tanstack/react-query";
import { listAttendees } from "../api/client";
import { demoAttendees } from "../data/demo";

export function useAttendees(params?: { ticket_type?: string; limit?: number }) {
  return useQuery({
    queryKey: ["attendees", params],
    queryFn: async () => {
      try {
        const result = await listAttendees({ limit: params?.limit ?? 100 });
        return result.attendees.length > 0
          ? result
          : { attendees: demoAttendees, total: demoAttendees.length };
      } catch {
        return { attendees: demoAttendees, total: demoAttendees.length };
      }
    },
    placeholderData: { attendees: demoAttendees, total: demoAttendees.length },
    staleTime: 30_000,
  });
}

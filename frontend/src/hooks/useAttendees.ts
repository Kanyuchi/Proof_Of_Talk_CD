import { useQuery, keepPreviousData } from "@tanstack/react-query";
import { listAttendees } from "../api/client";

export function useAttendees(params?: { ticket_type?: string; limit?: number }) {
  return useQuery({
    queryKey: ["attendees", params],
    queryFn: async () => {
      // Limit set to 1000 (backend cap, raised from 200 on 2026-05-12).
      // Removed the demo-fallback (May 12) — a transient 401 on token
      // refresh or an empty initial response was causing 5 hardcoded
      // demo seeds to flash through the UI as "5 decision-makers
      // registered" until the real fetch completed. Let errors surface
      // naturally so React Query retries with backoff instead of
      // showing fake data.
      return await listAttendees({ limit: params?.limit ?? 1000 });
    },
    // Keep prior data visible across refetches so the list never collapses
    // to 0 mid-render. Also raised staleTime 30s → 5min — the attendees
    // list rarely changes within a single session and the previous
    // setting caused constant refetching.
    placeholderData: keepPreviousData,
    staleTime: 5 * 60_000,
    gcTime: 15 * 60_000,
  });
}

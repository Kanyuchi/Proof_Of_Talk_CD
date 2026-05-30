import { useQuery } from "@tanstack/react-query";
import { getAttendee } from "../api/client";

// 2026-05-30: Previously fell back to demoAttendees[0] (= Amara Okafor) on any
// /attendees/{id} error. Combined with the same fallback in useMatches, this
// painted Amara's identity onto a real attendee's page when the backend hit
// a transient pool-exhaustion or pgbouncer prepared-statement error. The hook
// now propagates the error; consumer pages render an explicit empty state.
export function useAttendee(id: string | undefined) {
  return useQuery({
    queryKey: ["attendee", id],
    queryFn: () => getAttendee(id!),
    enabled: !!id,
    staleTime: 30_000,
  });
}

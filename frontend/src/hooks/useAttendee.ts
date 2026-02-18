import { useQuery } from "@tanstack/react-query";
import { getAttendee } from "../api/client";
import { demoAttendees } from "../data/demo";

export function useAttendee(id: string | undefined) {
  return useQuery({
    queryKey: ["attendee", id],
    queryFn: async () => {
      if (!id) throw new Error("No ID");
      try {
        return await getAttendee(id);
      } catch {
        return demoAttendees.find((a) => a.id === id) ?? demoAttendees[0];
      }
    },
    enabled: !!id,
    staleTime: 30_000,
  });
}

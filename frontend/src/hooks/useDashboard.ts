import { useQuery, useMutation } from "@tanstack/react-query";
import {
  getDashboardStats,
  getMatchQuality,
  getMatchesByType,
  getAttendeesBySector,
  triggerProcessing,
  triggerMatching,
} from "../api/client";
import { demoStats, demoQuality } from "../data/demo";

export function useDashboardStats() {
  return useQuery({
    queryKey: ["dashboard-stats"],
    queryFn: async () => {
      try {
        const s = await getDashboardStats();
        return s.total_attendees > 0 ? s : demoStats;
      } catch {
        return demoStats;
      }
    },
    placeholderData: demoStats,
    staleTime: 15_000,
    refetchInterval: 30_000,
  });
}

export function useMatchQuality() {
  return useQuery({
    queryKey: ["match-quality"],
    queryFn: async () => {
      try {
        const q = await getMatchQuality();
        return q.total_matches > 0 ? q : demoQuality;
      } catch {
        return demoQuality;
      }
    },
    placeholderData: demoQuality,
    staleTime: 15_000,
  });
}

export function useMatchesByType(matchType: string | null) {
  return useQuery({
    queryKey: ["matches-by-type", matchType],
    queryFn: () => getMatchesByType(matchType!),
    enabled: !!matchType,
    staleTime: 30_000,
  });
}

export function useAttendeesBySector(sector: string | null) {
  return useQuery({
    queryKey: ["attendees-by-sector", sector],
    queryFn: () => getAttendeesBySector(sector!),
    enabled: !!sector,
    staleTime: 30_000,
  });
}

export function useTriggerProcessing() {
  return useMutation({ mutationFn: triggerProcessing });
}

export function useTriggerMatching() {
  return useMutation({ mutationFn: triggerMatching });
}

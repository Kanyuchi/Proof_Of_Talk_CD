import { useQuery, useMutation } from "@tanstack/react-query";
import {
  getDashboardStats,
  getMatchQuality,
  getMatchesByType,
  getAttendeesBySector,
  triggerProcessing,
  triggerMatching,
} from "../api/client";

export function useDashboardStats() {
  return useQuery({
    queryKey: ["dashboard-stats"],
    queryFn: getDashboardStats,
    staleTime: 15_000,
    refetchInterval: 30_000,
  });
}

export function useMatchQuality() {
  return useQuery({
    queryKey: ["match-quality"],
    queryFn: getMatchQuality,
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

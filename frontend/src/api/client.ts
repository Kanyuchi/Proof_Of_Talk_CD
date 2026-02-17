import axios from "axios";
import type { Attendee, Match, DashboardStats, MatchQuality } from "../types";

const api = axios.create({
  baseURL: "/api/v1",
});

// ── Attendees ──────────────────────────────────────────────────────────

export async function listAttendees(params?: {
  skip?: number;
  limit?: number;
  ticket_type?: string;
}): Promise<{ attendees: Attendee[]; total: number }> {
  const { data } = await api.get("/attendees", { params });
  return data;
}

export async function getAttendee(id: string): Promise<Attendee> {
  const { data } = await api.get(`/attendees/${id}`);
  return data;
}

export async function createAttendee(
  attendee: Omit<Attendee, "id" | "created_at" | "ai_summary" | "intent_tags" | "deal_readiness_score" | "enriched_profile">
): Promise<Attendee> {
  const { data } = await api.post("/attendees", attendee);
  return data;
}

// ── Matches ────────────────────────────────────────────────────────────

export async function getMatches(
  attendeeId: string,
  limit = 10
): Promise<{ matches: Match[]; attendee_id: string }> {
  const { data } = await api.get(`/matches/${attendeeId}`, {
    params: { limit },
  });
  return data;
}

export async function generateMatchesForAttendee(
  attendeeId: string
): Promise<{ status: string; matches_generated: number }> {
  const { data } = await api.post(`/matches/generate/${attendeeId}`);
  return data;
}

export async function generateAllMatches(): Promise<{
  status: string;
  total_matches: number;
}> {
  const { data } = await api.post("/matches/generate-all");
  return data;
}

export async function processAllAttendees(): Promise<{
  status: string;
  attendees_processed: number;
}> {
  const { data } = await api.post("/matches/process-all");
  return data;
}

export async function updateMatchStatus(
  matchId: string,
  status: "accepted" | "declined"
): Promise<Match> {
  const { data } = await api.patch(`/matches/${matchId}/status`, { status });
  return data;
}

// ── Enrichment ─────────────────────────────────────────────────────────

export async function enrichAttendee(
  attendeeId: string
): Promise<{ status: string; sources_enriched: string[] }> {
  const { data } = await api.post(`/enrichment/${attendeeId}`);
  return data;
}

export async function enrichAll(): Promise<{ status: string }> {
  const { data } = await api.post("/enrichment/batch");
  return data;
}

// ── Dashboard ──────────────────────────────────────────────────────────

export async function getDashboardStats(): Promise<DashboardStats> {
  const { data } = await api.get("/dashboard/stats");
  return data;
}

export async function getMatchQuality(): Promise<MatchQuality> {
  const { data } = await api.get("/dashboard/match-quality");
  return data;
}

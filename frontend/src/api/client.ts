import axios from "axios";
import type {
  Attendee,
  Match,
  DashboardStats,
  MatchQuality,
  Token,
  User,
  ConversationSummary,
  ConversationDetail,
  MessageData,
} from "../types";

export const api = axios.create({
  baseURL: "/api/v1",
});

// Restore auth token on load
const stored = localStorage.getItem("token");
if (stored) {
  api.defaults.headers.common["Authorization"] = `Bearer ${stored}`;
}

// ── Attendees ─────────────────────────────────────────────────────────

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

export async function searchAttendees(q: string): Promise<{ attendees: Attendee[] }> {
  const { data } = await api.get("/attendees/search", { params: { q } });
  return data;
}

export async function submitOnboarding(body: {
  ticket_code: string;
  title?: string;
  company?: string;
  goals?: string;
  interests?: string[];
  seeking?: string[];
  deal_stage?: string;
  linkedin_url?: string;
  twitter_handle?: string;
  company_website?: string;
}): Promise<{ status: string; attendee_id: string; name: string; message: string }> {
  const { data } = await api.post("/attendees/onboarding", body);
  return data;
}

// ── Matches ──────────────────────────────────────────────────────────

export async function getMatches(
  attendeeId: string,
  limit = 10
): Promise<{ matches: Match[]; attendee_id: string }> {
  const { data } = await api.get(`/matches/${attendeeId}`, { params: { limit } });
  return data;
}

export async function updateProfileViaMagicLink(
  token: string,
  data: { twitter_handle?: string; target_companies?: string; photo_url?: string }
): Promise<{ status: string }> {
  const { data: resp } = await api.patch(`/matches/m/${token}/profile`, data);
  return resp;
}

export async function getMatchesByMagicLink(
  token: string,
  limit = 10
): Promise<{ matches: Match[]; attendee_id: string }> {
  const { data } = await api.get(`/matches/m/${token}`, { params: { limit } });
  return data;
}

export async function getPendingMatchCount(): Promise<{ pending_count: number }> {
  const { data } = await api.get("/matches/pending-count");
  return data;
}

export async function generateMatchesForAttendee(
  attendeeId: string
): Promise<{ status: string; matches_generated: number }> {
  const { data } = await api.post(`/matches/generate/${attendeeId}`);
  return data;
}

export async function generateAllMatches(): Promise<{ status: string; total_matches: number }> {
  const { data } = await api.post("/matches/generate-all");
  return data;
}

export async function processAllAttendees(): Promise<{ status: string; attendees_processed: number }> {
  const { data } = await api.post("/matches/process-all");
  return data;
}

export async function updateMatchStatus(
  matchId: string,
  status: "accepted" | "declined" | "met",
  decline_reason?: string
): Promise<Match> {
  const { data } = await api.patch(`/matches/${matchId}/status`, { status, decline_reason });
  return data;
}

export async function scheduleMeeting(
  matchId: string,
  meeting_time: string,
  meeting_location?: string
): Promise<Match> {
  const { data } = await api.patch(`/matches/${matchId}/schedule`, {
    meeting_time,
    meeting_location,
  });
  return data;
}

export async function updateMeetingFeedback(
  matchId: string,
  body: {
    meeting_outcome?: string;
    satisfaction_score?: number;
    met_at?: string;
    hidden_by_user?: boolean;
  }
): Promise<Match> {
  const { data } = await api.patch(`/matches/${matchId}/feedback`, body);
  return data;
}

// ── Enrichment ───────────────────────────────────────────────────────

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

// ── Dashboard ────────────────────────────────────────────────────────

export async function getDashboardStats(): Promise<DashboardStats> {
  const { data } = await api.get("/dashboard/stats");
  return data;
}

export async function getMatchQuality(): Promise<MatchQuality> {
  const { data } = await api.get("/dashboard/match-quality");
  return data;
}

export async function getMatchesByType(
  matchType: string
): Promise<{ matches: Match[] }> {
  const { data } = await api.get("/dashboard/matches-by-type", { params: { match_type: matchType } });
  return data;
}

export async function getAttendeesBySector(
  sector: string
): Promise<{ attendees: Attendee[] }> {
  const { data } = await api.get("/dashboard/attendees-by-sector", { params: { sector } });
  return data;
}

export async function getRevenueStats(): Promise<{
  funnel: { total_orders: number; paid: number; redeemed: number; failed: number; refunded: number; pending: number; valid: number; conversion_rate: number };
  revenue: { total: number; avg_ticket_price: number; paid_tickets: number; comp_tickets: number; by_type: { type: string; count: number; revenue: number }[] };
  growth: { week: string; registrations: number }[];
  source_breakdown: { extasy: number; speakers_1000minds: number; seed: number; other: number; total: number };
  profile_completeness: { total: number; with_goals: number; with_linkedin: number; with_twitter: number; with_website: number; with_grid: number; with_photo: number; with_targets: number };
}> {
  const { data } = await api.get("/dashboard/revenue");
  return data;
}

export async function getInvestorHeatmap(): Promise<{
  heatmap: {
    vertical: string;
    label: string;
    attendee_count: number;
    capital_active: number;
    avg_deal_readiness: number;
  }[];
  total_attendees: number;
  deal_readiness_distribution: { high: number; medium: number; low: number };
}> {
  const { data } = await api.get("/dashboard/investor-heatmap");
  return data;
}

export async function triggerProcessing(): Promise<{ attendees_processed: number }> {
  const { data } = await api.post("/dashboard/trigger-processing");
  return data;
}

export async function triggerMatching(): Promise<{ total_matches: number }> {
  const { data } = await api.post("/dashboard/trigger-matching");
  return data;
}

export async function syncExtasy(): Promise<{
  status: string;
  total_fetched: number;
  paid_count: number;
  inserted: number;
  upgraded: number;
  skipped: number;
  errors: number;
}> {
  const { data } = await api.post("/dashboard/sync-extasy");
  return data;
}

// ── Auth ─────────────────────────────────────────────────────────────

export async function loginUser(email: string, password: string): Promise<Token> {
  const { data } = await api.post("/auth/login", { email, password });
  return data;
}

export async function registerUser(body: {
  email: string;
  password: string;
  name: string;
  company?: string;
  title?: string;
  ticket_type?: string;
  interests?: string[];
  goals?: string;
  seeking?: string[];
  not_looking_for?: string[];
  preferred_geographies?: string[];
  deal_stage?: string;
  linkedin_url?: string;
  twitter_handle?: string;
  company_website?: string;
}): Promise<Token> {
  const { data } = await api.post("/auth/register", body);
  return data;
}

export async function forgotPassword(email: string): Promise<{ message: string }> {
  const { data } = await api.post("/auth/forgot-password", { email });
  return data;
}

export async function resetPassword(token: string, new_password: string): Promise<{ message: string }> {
  const { data } = await api.post("/auth/reset-password", { token, new_password });
  return data;
}

export async function getMyMagicLink(): Promise<{ magic_token: string }> {
  const { data } = await api.get("/auth/my-magic-link");
  return data;
}

export async function getMe(): Promise<User> {
  const { data } = await api.get("/auth/me");
  return data;
}

export async function updateProfile(body: {
  name?: string;
  company?: string;
  title?: string;
  goals?: string;
  interests?: string[];
  seeking?: string[];
  not_looking_for?: string[];
  preferred_geographies?: string[];
  deal_stage?: string;
  linkedin_url?: string;
  twitter_handle?: string;
  company_website?: string;
  photo_url?: string;
}): Promise<{ user: User; attendee: Attendee }> {
  const { data } = await api.put("/auth/profile", body);
  return data;
}

// ── Chat ─────────────────────────────────────────────────────────────

export async function chatWithConcierge(body: {
  message: string;
  attendee_id?: string;
  history: { role: string; content: string }[];
}): Promise<{ response: string }> {
  const { data } = await api.post("/chat/concierge", body);
  return data;
}

// ── Messages ─────────────────────────────────────────────────────────

export async function listConversations(): Promise<{ conversations: ConversationSummary[] }> {
  const { data } = await api.get("/messages/conversations");
  return data;
}

export async function getConversation(matchId: string): Promise<ConversationDetail> {
  const { data } = await api.get(`/messages/conversations/${matchId}`);
  return data;
}

export async function sendMessage(matchId: string, content: string): Promise<MessageData> {
  const { data } = await api.post(`/messages/conversations/${matchId}`, { content });
  return data;
}

export async function getUnreadCount(): Promise<{ unread_count: number }> {
  const { data } = await api.get("/messages/unread-count");
  return data;
}

// ── Threads ─────────────────────────────────────────────────────────

export interface ThreadSummary {
  id: string;
  slug: string;
  title: string;
  description: string | null;
  post_count: number;
  latest_post_at: string | null;
  is_member: boolean;
}

export interface ThreadPost {
  id: string;
  sender_name: string;
  sender_title: string;
  sender_company: string;
  sender_attendee_id: string;
  content: string;
  created_at: string;
  is_mine: boolean;
}

export async function listThreads(): Promise<{ threads: ThreadSummary[] }> {
  const { data } = await api.get("/threads");
  return data;
}

export async function getThread(slug: string): Promise<{
  thread: { id: string; slug: string; title: string; description: string | null };
  posts: ThreadPost[];
}> {
  const { data } = await api.get(`/threads/${slug}`);
  return data;
}

export async function postToThread(slug: string, content: string): Promise<ThreadPost> {
  const { data } = await api.post(`/threads/${slug}`, { content });
  return data;
}

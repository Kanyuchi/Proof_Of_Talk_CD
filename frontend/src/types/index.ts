export interface Attendee {
  id: string;
  name: string;
  email: string;
  company: string;
  title: string;
  ticket_type: "delegate" | "sponsor" | "speaker" | "vip";
  interests: string[];
  goals: string | null;
  linkedin_url: string | null;
  twitter_handle: string | null;
  company_website: string | null;
  ai_summary: string | null;
  intent_tags: string[];
  deal_readiness_score: number | null;
  enriched_profile: Record<string, unknown>;
  created_at: string;
}

export interface Match {
  id: string;
  attendee_a_id: string;
  attendee_b_id: string;
  similarity_score: number;
  complementary_score: number;
  overall_score: number;
  match_type: "complementary" | "non_obvious" | "deal_ready";
  explanation: string;
  shared_context: {
    sectors?: string[];
    synergies?: string[];
    action_items?: string[];
  };
  status: "pending" | "accepted" | "declined" | "met";
  created_at: string;
  matched_attendee?: Attendee;
}

export interface DashboardStats {
  total_attendees: number;
  matches_generated: number;
  matches_accepted: number;
  matches_declined: number;
  enrichment_coverage: number;
  avg_match_score: number;
  top_sectors: { sector: string; count: number }[];
  match_type_distribution: Record<string, number>;
}

export interface MatchQuality {
  total_matches: number;
  score_distribution: Record<string, number>;
  acceptance_rate: number;
}

// ── Auth ────────────────────────────────────────────────────────────────

export interface User {
  id: string;
  email: string;
  full_name: string;
  is_admin: boolean;
  attendee_id: string | null;
}

export interface Token {
  access_token: string;
  token_type: string;
}

// ── Chat ────────────────────────────────────────────────────────────────

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}

// ── Messages ────────────────────────────────────────────────────────────

export interface MessageData {
  id: string;
  conversation_id: string;
  sender_attendee_id: string;
  sender_name: string;
  content: string;
  created_at: string;
  read_at: string | null;
  is_mine: boolean;
}

export interface ConversationSummary {
  match_id: string;
  match_status: string;
  conversation_id: string | null;
  other_attendee_id: string | null;
  other_attendee_name: string;
  other_attendee_company: string;
  other_attendee_title: string;
  other_attendee_ticket: string;
  last_message: string | null;
  last_message_at: string | null;
  unread_count: number;
}

export interface ConversationDetail {
  conversation_id: string;
  match_id: string;
  match_status: string;
  other_attendee: {
    id: string;
    name: string;
    company: string;
    title: string;
    ticket_type: string;
  } | null;
  messages: MessageData[];
}

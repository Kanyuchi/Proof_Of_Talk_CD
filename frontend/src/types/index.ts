export interface Attendee {
  id: string;
  name: string;
  email: string;
  company: string;
  title: string;
  ticket_type: "delegate" | "sponsor" | "speaker" | "vip" | "team";
  interests: string[];
  goals: string | null;
  target_companies: string | null;
  seeking: string[];
  not_looking_for: string[];
  preferred_geographies: string[];
  deal_stage: string | null;
  photo_url: string | null;
  linkedin_url: string | null;
  twitter_handle: string | null;
  company_website: string | null;
  ai_summary: string | null;
  intent_tags: string[];
  vertical_tags: string[];
  deal_readiness_score: number | null;
  privacy_mode: string;
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
  status_a: string;
  status_b: string;
  meeting_time: string | null;
  meeting_location: string | null;
  met_at: string | null;
  meeting_outcome: string | null;
  satisfaction_score: number | null;
  decline_reason: string | null;
  hidden_by_user: boolean;
  explanation_confidence: number | null;
  created_at: string;
  matched_attendee?: Attendee;
  // Slots both parties are free for. Populated server-side on mutual matches with no booking yet.
  mutual_free_slots?: string[];
  tier?: "curated" | "deep";
}

export interface DashboardStats {
  total_attendees: number;
  matches_generated: number;
  matches_accepted: number;
  matches_declined: number;
  enrichment_coverage: number;
  avg_match_score: number;
  mutual_accept_rate: number;
  scheduled_rate: number;
  show_rate: number;
  post_meeting_satisfaction: number;
  top_sectors: { sector: string; count: number }[];
  match_type_distribution: Record<string, number>;
}

export interface MatchQuality {
  total_matches: number;
  score_distribution: Record<string, number>;
  acceptance_rate: number;
}

export interface Adoption {
  tracking_started_at: string;
  accounts: {
    total: number;
    real: number;
    linked_to_attendee: number;
    pct_of_directory: number;
    directory_size: number;
  };
  signups_by_day: { day: string; n: number }[];
  usage: {
    cumulative_active: number;
    active_last_7d: number;
    magic_link_active: number;
    login_active: number;
  };
  usage_by_day: { day: string; active_today: number; cumulative_active: number }[];
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

export interface MatchListResult {
  matches: Match[];
  attendee_id: string;
  // The viewer's own profile. Lets the no-login magic-link page render its
  // enrichment card + avatar without the auth-gated GET /attendees/{id}.
  viewer?: Attendee | null;
  tier?: "SPARSE" | "PARTIAL" | "GOOD";
  visible_count?: number;
  locked_count?: number;
  next_tier_at?: number | null;
  completeness_pct?: number | null;
  // True iff the viewer already has a `users` row (claimed their account).
  // Drives the magic-link "Set your password" panel's default-expanded state.
  has_account?: boolean;
}

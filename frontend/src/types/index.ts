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

import { useState, useEffect } from "react";
import { useParams, Link } from "react-router-dom";
import {
  ArrowLeft,
  Handshake,
  Lightbulb,
  DollarSign,
  Check,
  X,
  Brain,
  Target,
  MessageSquare,
  Sparkles,
  Crown,
  Mic,
  Megaphone,
  User,
} from "lucide-react";
import type { Attendee, Match } from "../types";
import { getAttendee, getMatches, updateMatchStatus } from "../api/client";

const matchTypeConfig = {
  complementary: {
    icon: Handshake,
    label: "Complementary",
    color: "text-blue-400",
    bg: "bg-blue-400/10 border-blue-400/20",
    description: "One party has what the other needs",
  },
  non_obvious: {
    icon: Lightbulb,
    label: "Non-Obvious",
    color: "text-purple-400",
    bg: "bg-purple-400/10 border-purple-400/20",
    description: "Different sectors, similar underlying problems",
  },
  deal_ready: {
    icon: DollarSign,
    label: "Deal Ready",
    color: "text-emerald-400",
    bg: "bg-emerald-400/10 border-emerald-400/20",
    description: "Both parties positioned to transact",
  },
};

const ticketIcons: Record<string, React.ReactNode> = {
  vip: <Crown className="w-3 h-3" />,
  speaker: <Mic className="w-3 h-3" />,
  sponsor: <Megaphone className="w-3 h-3" />,
  delegate: <User className="w-3 h-3" />,
};

// Demo matches for when API isn't connected
const demoMatches: Match[] = [
  {
    id: "m1",
    attendee_a_id: "1",
    attendee_b_id: "2",
    similarity_score: 0.574,
    complementary_score: 0.85,
    overall_score: 0.85,
    match_type: "complementary",
    explanation:
      "Amara Okafor is looking to deploy $200M into tokenised real-world assets and blockchain infrastructure, while Marcus Chen's VaultBridge offers institutional custody and settlement infrastructure for tokenised securities. With VaultBridge already integrated with European banks and asset managers, this presents a strategic investment opportunity aligned with Amara's focus on regulated custody solutions.",
    shared_context: {
      sectors: ["tokenised securities", "institutional custody"],
      synergies: ["regulated custody solutions", "Middle Eastern sovereign wealth fund connections"],
      action_items: ["Discuss strategic investment and partnership opportunities", "Explore integration with Abu Dhabi Sovereign Wealth Fund"],
    },
    status: "pending",
    created_at: new Date().toISOString(),
    matched_attendee: {
      id: "2", name: "Marcus Chen", email: "marcus@example.com", company: "VaultBridge",
      title: "CEO & Co-Founder", ticket_type: "speaker",
      interests: ["institutional custody", "tokenised securities", "settlement infrastructure"],
      goals: "Series B ($40M raised). Looking for strategic investors.", linkedin_url: null,
      twitter_handle: null, company_website: null,
      ai_summary: "CEO of VaultBridge, Series B custody platform live with 3 European banks.",
      intent_tags: ["raising_capital", "seeking_partnerships", "deal_making"],
      deal_readiness_score: 0.5, enriched_profile: {}, created_at: new Date().toISOString(),
    },
  },
  {
    id: "m2",
    attendee_a_id: "1",
    attendee_b_id: "3",
    similarity_score: 0.607,
    complementary_score: 0.80,
    overall_score: 0.80,
    match_type: "deal_ready",
    explanation:
      "Dr. Elena Vasquez is seeking Series A-B companies with institutional traction, which aligns with Amara's interest in institutional-grade DeFi protocols. Both are looking for co-investment opportunities, making them ideal partners to explore joint ventures in blockchain infrastructure.",
    shared_context: {
      sectors: ["institutional DeFi", "blockchain infrastructure"],
      synergies: ["institutional traction", "co-investment opportunities"],
      action_items: ["Explore co-investment in Series A-B companies", "Discuss strategic partnerships in DeFi infrastructure"],
    },
    status: "pending",
    created_at: new Date().toISOString(),
    matched_attendee: {
      id: "3", name: "Dr. Elena Vasquez", email: "elena@example.com", company: "Meridian Crypto Ventures",
      title: "General Partner", ticket_type: "vip",
      interests: ["TradFi-DeFi convergence", "infrastructure", "Series A-B investing"],
      goals: "$500M AUM. Thesis: infrastructure at TradFi-DeFi intersection.", linkedin_url: null,
      twitter_handle: null, company_website: null,
      ai_summary: "GP at Meridian Crypto Ventures ($500M AUM), investing in TradFi-DeFi infra.",
      intent_tags: ["deploying_capital", "seeking_partnerships", "deal_making", "co_investment"],
      deal_readiness_score: 0.5, enriched_profile: {}, created_at: new Date().toISOString(),
    },
  },
  {
    id: "m3",
    attendee_a_id: "1",
    attendee_b_id: "4",
    similarity_score: 0.508,
    complementary_score: 0.65,
    overall_score: 0.65,
    match_type: "non_obvious",
    explanation:
      "James Whitfield's NexaLayer focuses on enterprise-grade Layer-2 solutions with compliance modules, which could complement Amara's interest in regulated custody. Both parties are interested in regulatory engagement and could explore synergies in compliance-focused blockchain solutions.",
    shared_context: {
      sectors: ["compliance infrastructure", "enterprise blockchain"],
      synergies: ["compliance modules", "KYC/AML capabilities"],
      action_items: ["Discuss potential pilot projects", "Explore cross-chain settlement opportunities"],
    },
    status: "pending",
    created_at: new Date().toISOString(),
    matched_attendee: {
      id: "4", name: "James Whitfield", email: "james@example.com", company: "NexaLayer",
      title: "CTO", ticket_type: "sponsor",
      interests: ["Layer-2 scaling", "enterprise blockchain", "compliance modules"],
      goals: "Enterprise L2 with compliance. Seeking bank pilots.", linkedin_url: null,
      twitter_handle: null, company_website: null,
      ai_summary: "CTO of NexaLayer, building enterprise L2 with compliance modules.",
      intent_tags: ["seeking_partnerships", "seeking_customers"],
      deal_readiness_score: 0.25, enriched_profile: {}, created_at: new Date().toISOString(),
    },
  },
  {
    id: "m4",
    attendee_a_id: "1",
    attendee_b_id: "5",
    similarity_score: 0.565,
    complementary_score: 0.50,
    overall_score: 0.50,
    match_type: "non_obvious",
    explanation:
      "Sophie Bergmann's focus on CBDC infrastructure and regulatory frameworks for tokenised securities under MiCA could provide valuable insights for Amara's interest in regulatory clarity. Their shared interest in regulation and compliance offers a foundation for knowledge exchange.",
    shared_context: {
      sectors: ["regulatory frameworks", "tokenised securities"],
      synergies: ["regulatory frameworks", "compliance-first technology"],
      action_items: ["Engage in regulatory sandbox discussions", "Exchange insights on MiCA compliance"],
    },
    status: "pending",
    created_at: new Date().toISOString(),
    matched_attendee: {
      id: "5", name: "Sophie Bergmann", email: "sophie@example.com", company: "Deutsche Bundesbank",
      title: "Head of Digital Assets Innovation", ticket_type: "delegate",
      interests: ["CBDC", "regulatory frameworks", "MiCA"],
      goals: "Exploring CBDC infrastructure and MiCA regulatory frameworks.", linkedin_url: null,
      twitter_handle: null, company_website: null,
      ai_summary: "Leads digital assets innovation at Deutsche Bundesbank. Focused on CBDC and MiCA.",
      intent_tags: ["regulatory_engagement", "technology_evaluation", "knowledge_exchange"],
      deal_readiness_score: 0.0, enriched_profile: {}, created_at: new Date().toISOString(),
    },
  },
];

export default function AttendeeMatches() {
  const { id } = useParams<{ id: string }>();
  const [attendee, setAttendee] = useState<Attendee | null>(null);
  const [matches, setMatches] = useState<Match[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      if (!id) return;
      try {
        const [a, m] = await Promise.all([
          getAttendee(id),
          getMatches(id),
        ]);
        setAttendee(a);
        setMatches(m.matches.length > 0 ? m.matches : demoMatches);
      } catch {
        // Use demo data
        setAttendee({
          id: "1", name: "Amara Okafor", email: "amara@example.com",
          company: "Abu Dhabi Sovereign Wealth Fund", title: "Director of Digital Assets",
          ticket_type: "vip",
          interests: ["tokenised real-world assets", "blockchain infrastructure", "regulated custody", "institutional DeFi"],
          goals: "Deploy $200M into tokenised real-world assets and blockchain infrastructure over 18 months.",
          linkedin_url: null, twitter_handle: null, company_website: null,
          ai_summary: "Senior sovereign wealth fund allocator with a $200M mandate for tokenised RWA and blockchain infrastructure.",
          intent_tags: ["deploying_capital", "seeking_partnerships", "co_investment", "deal_making"],
          deal_readiness_score: 0.5, enriched_profile: {}, created_at: new Date().toISOString(),
        });
        setMatches(demoMatches);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [id]);

  const handleStatus = async (matchId: string, status: "accepted" | "declined") => {
    try {
      await updateMatchStatus(matchId, status);
    } catch {
      // Update locally even if API fails (demo mode)
    }
    setMatches((prev) =>
      prev.map((m) => (m.id === matchId ? { ...m, status } : m))
    );
  };

  if (loading) {
    return <div className="text-center py-20 text-white/30">Loading matches...</div>;
  }

  if (!attendee) {
    return <div className="text-center py-20 text-white/30">Attendee not found</div>;
  }

  return (
    <div className="space-y-8">
      {/* Back link */}
      <Link
        to="/attendees"
        className="inline-flex items-center gap-2 text-sm text-white/40 hover:text-white transition-colors"
      >
        <ArrowLeft className="w-4 h-4" />
        Back to Attendees
      </Link>

      {/* Attendee header */}
      <div className="p-6 rounded-2xl bg-white/[0.03] border border-white/10">
        <div className="flex items-start gap-4">
          <div className="w-16 h-16 rounded-xl bg-gradient-to-br from-amber-400/20 to-amber-600/20 flex items-center justify-center text-amber-400 font-bold text-2xl shrink-0">
            {attendee.name[0]}
          </div>
          <div className="flex-1">
            <h1 className="text-2xl font-bold">{attendee.name}</h1>
            <p className="text-white/50">
              {attendee.title} &middot; {attendee.company}
            </p>
            {attendee.ai_summary && (
              <p className="text-sm text-white/40 mt-2 flex items-start gap-2">
                <Brain className="w-4 h-4 mt-0.5 shrink-0 text-amber-400" />
                {attendee.ai_summary}
              </p>
            )}
            <div className="flex flex-wrap gap-1.5 mt-3">
              {attendee.intent_tags.map((tag) => (
                <span
                  key={tag}
                  className="px-2.5 py-1 rounded-full bg-amber-400/10 text-amber-400 text-xs border border-amber-400/20"
                >
                  {tag.replace(/_/g, " ")}
                </span>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Match heading */}
      <div className="flex items-center gap-3">
        <Sparkles className="w-5 h-5 text-amber-400" />
        <h2 className="text-xl font-bold">AI-Recommended Matches</h2>
        <span className="text-white/30 text-sm">({matches.length} connections)</span>
      </div>

      {/* Match cards */}
      <div className="space-y-4">
        {matches.map((match, idx) => {
          const config = matchTypeConfig[match.match_type] || matchTypeConfig.complementary;
          const Icon = config.icon;
          const person = match.matched_attendee;

          return (
            <div
              key={match.id}
              className={`rounded-2xl border overflow-hidden transition-all ${
                match.status === "accepted"
                  ? "border-emerald-400/30 bg-emerald-400/[0.03]"
                  : match.status === "declined"
                  ? "border-white/5 bg-white/[0.01] opacity-50"
                  : "border-white/10 bg-white/[0.03] hover:border-white/20"
              }`}
            >
              {/* Match header bar */}
              <div className="px-5 py-3 bg-white/[0.02] border-b border-white/5 flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <span className="text-lg font-bold text-white/20">
                    #{idx + 1}
                  </span>
                  <span
                    className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium border ${config.bg}`}
                  >
                    <Icon className="w-3 h-3" />
                    {config.label}
                  </span>
                  <span className="text-xs text-white/30">{config.description}</span>
                </div>
                <div className="flex items-center gap-4">
                  <div className="text-right">
                    <div className="text-xs text-white/30">Match Score</div>
                    <div className="text-lg font-bold text-amber-400">
                      {(match.overall_score * 100).toFixed(0)}%
                    </div>
                  </div>
                </div>
              </div>

              {/* Match body */}
              <div className="p-5 space-y-4">
                {/* Person info */}
                {person && (
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-white/5 to-white/10 flex items-center justify-center text-white/60 font-semibold">
                      {person.name[0]}
                    </div>
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-semibold">{person.name}</span>
                        <span className="text-white/30">{ticketIcons[person.ticket_type]}</span>
                      </div>
                      <div className="text-sm text-white/50">
                        {person.title} &middot; {person.company}
                      </div>
                    </div>
                    {person.deal_readiness_score != null && person.deal_readiness_score > 0 && (
                      <div className="ml-auto text-right">
                        <div className="text-[10px] text-white/30 uppercase">Deal Ready</div>
                        <div className="text-sm font-mono text-emerald-400">
                          {(person.deal_readiness_score * 100).toFixed(0)}%
                        </div>
                      </div>
                    )}
                  </div>
                )}

                {/* AI Explanation */}
                <div className="p-4 rounded-xl bg-amber-400/5 border border-amber-400/10">
                  <div className="flex items-center gap-2 text-xs text-amber-400 font-medium mb-2">
                    <Brain className="w-3.5 h-3.5" />
                    WHY YOU SHOULD MEET
                  </div>
                  <p className="text-sm text-white/70 leading-relaxed">
                    {match.explanation}
                  </p>
                </div>

                {/* Shared context */}
                {match.shared_context && (
                  <div className="grid md:grid-cols-3 gap-3">
                    {match.shared_context.sectors && match.shared_context.sectors.length > 0 && (
                      <div className="p-3 rounded-lg bg-white/[0.02]">
                        <div className="text-[10px] text-white/30 uppercase font-medium mb-1.5 flex items-center gap-1">
                          <Target className="w-3 h-3" /> Sectors
                        </div>
                        <div className="flex flex-wrap gap-1">
                          {match.shared_context.sectors.map((s) => (
                            <span key={s} className="text-xs text-white/50 bg-white/5 px-2 py-0.5 rounded-full">
                              {s}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}
                    {match.shared_context.synergies && match.shared_context.synergies.length > 0 && (
                      <div className="p-3 rounded-lg bg-white/[0.02]">
                        <div className="text-[10px] text-white/30 uppercase font-medium mb-1.5 flex items-center gap-1">
                          <Sparkles className="w-3 h-3" /> Synergies
                        </div>
                        <div className="flex flex-wrap gap-1">
                          {match.shared_context.synergies.map((s) => (
                            <span key={s} className="text-xs text-white/50 bg-white/5 px-2 py-0.5 rounded-full">
                              {s}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}
                    {match.shared_context.action_items && match.shared_context.action_items.length > 0 && (
                      <div className="p-3 rounded-lg bg-white/[0.02]">
                        <div className="text-[10px] text-white/30 uppercase font-medium mb-1.5 flex items-center gap-1">
                          <MessageSquare className="w-3 h-3" /> Discuss
                        </div>
                        <ul className="space-y-1">
                          {match.shared_context.action_items.map((a) => (
                            <li key={a} className="text-xs text-white/50">
                              &bull; {a}
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                )}

                {/* Actions */}
                {match.status === "pending" && (
                  <div className="flex items-center gap-2 pt-2">
                    <button
                      onClick={() => handleStatus(match.id, "accepted")}
                      className="flex items-center gap-2 px-4 py-2 bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 rounded-lg text-sm font-medium hover:bg-emerald-500/20 transition-all"
                    >
                      <Check className="w-4 h-4" />
                      Accept Meeting
                    </button>
                    <button
                      onClick={() => handleStatus(match.id, "declined")}
                      className="flex items-center gap-2 px-4 py-2 bg-white/5 text-white/40 border border-white/10 rounded-lg text-sm font-medium hover:text-white/60 transition-all"
                    >
                      <X className="w-4 h-4" />
                      Not Now
                    </button>
                  </div>
                )}
                {match.status === "accepted" && (
                  <div className="flex items-center gap-2 text-sm text-emerald-400">
                    <Check className="w-4 h-4" />
                    Meeting accepted
                  </div>
                )}
                {match.status === "declined" && (
                  <div className="flex items-center gap-2 text-sm text-white/30">
                    <X className="w-4 h-4" />
                    Declined
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

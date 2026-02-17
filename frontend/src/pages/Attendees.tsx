import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import {
  Search,
  Crown,
  Mic,
  Megaphone,
  User,
  ChevronRight,
  Brain,
} from "lucide-react";
import type { Attendee } from "../types";
import { listAttendees } from "../api/client";

const ticketIcons: Record<string, React.ReactNode> = {
  vip: <Crown className="w-3.5 h-3.5 text-amber-400" />,
  speaker: <Mic className="w-3.5 h-3.5 text-purple-400" />,
  sponsor: <Megaphone className="w-3.5 h-3.5 text-emerald-400" />,
  delegate: <User className="w-3.5 h-3.5 text-blue-400" />,
};

const ticketColors: Record<string, string> = {
  vip: "bg-amber-400/10 text-amber-400 border-amber-400/20",
  speaker: "bg-purple-400/10 text-purple-400 border-purple-400/20",
  sponsor: "bg-emerald-400/10 text-emerald-400 border-emerald-400/20",
  delegate: "bg-blue-400/10 text-blue-400 border-blue-400/20",
};

// Demo data for when API isn't connected
const demoAttendees: Attendee[] = [
  {
    id: "1",
    name: "Amara Okafor",
    email: "amara@example.com",
    company: "Abu Dhabi Sovereign Wealth Fund",
    title: "Director of Digital Assets",
    ticket_type: "vip",
    interests: ["tokenised real-world assets", "blockchain infrastructure", "regulated custody", "institutional DeFi"],
    goals: "Deploy $200M into tokenised real-world assets and blockchain infrastructure over 18 months.",
    linkedin_url: null,
    twitter_handle: null,
    company_website: null,
    ai_summary: "Senior sovereign wealth fund allocator with a $200M mandate for tokenised RWA and blockchain infrastructure, focused on regulated custody and institutional-grade DeFi.",
    intent_tags: ["deploying_capital", "seeking_partnerships", "co_investment", "deal_making"],
    deal_readiness_score: 0.5,
    enriched_profile: {},
    created_at: new Date().toISOString(),
  },
  {
    id: "2",
    name: "Marcus Chen",
    email: "marcus@example.com",
    company: "VaultBridge",
    title: "CEO & Co-Founder",
    ticket_type: "speaker",
    interests: ["institutional custody", "tokenised securities", "settlement infrastructure", "banking partnerships"],
    goals: "Series B ($40M raised). Looking for strategic investors and Middle Eastern sovereign wealth fund introductions.",
    linkedin_url: null,
    twitter_handle: null,
    company_website: null,
    ai_summary: "CEO of VaultBridge, a Series B custody and settlement platform live with 3 European banks. Seeking strategic capital and sovereign fund partnerships.",
    intent_tags: ["raising_capital", "seeking_partnerships", "deal_making"],
    deal_readiness_score: 0.5,
    enriched_profile: {},
    created_at: new Date().toISOString(),
  },
  {
    id: "3",
    name: "Dr. Elena Vasquez",
    email: "elena@example.com",
    company: "Meridian Crypto Ventures",
    title: "General Partner",
    ticket_type: "vip",
    interests: ["TradFi-DeFi convergence", "infrastructure", "Series A-B investing", "institutional traction"],
    goals: "$500M AUM. Thesis: infrastructure at the TradFi-DeFi intersection. Seeking deal flow and co-investors.",
    linkedin_url: null,
    twitter_handle: null,
    company_website: null,
    ai_summary: "GP at Meridian Crypto Ventures ($500M AUM), investing in TradFi-DeFi infrastructure. Actively seeking Series A-B companies with institutional traction.",
    intent_tags: ["deploying_capital", "seeking_partnerships", "deal_making", "co_investment"],
    deal_readiness_score: 0.5,
    enriched_profile: {},
    created_at: new Date().toISOString(),
  },
  {
    id: "4",
    name: "James Whitfield",
    email: "james@example.com",
    company: "NexaLayer",
    title: "CTO",
    ticket_type: "sponsor",
    interests: ["Layer-2 scaling", "enterprise blockchain", "compliance modules", "KYC/AML", "cross-chain settlement"],
    goals: "Enterprise-grade L2 with compliance modules. Seeking bank pilots and infrastructure partnerships.",
    linkedin_url: null,
    twitter_handle: null,
    company_website: null,
    ai_summary: "CTO of NexaLayer, building enterprise L2 with compliance modules. Targeting regulated financial institutions for pilot programs.",
    intent_tags: ["seeking_partnerships", "seeking_customers", "regulatory_engagement", "technology_evaluation"],
    deal_readiness_score: 0.25,
    enriched_profile: {},
    created_at: new Date().toISOString(),
  },
  {
    id: "5",
    name: "Sophie Bergmann",
    email: "sophie@example.com",
    company: "Deutsche Bundesbank",
    title: "Head of Digital Assets Innovation",
    ticket_type: "delegate",
    interests: ["CBDC", "regulatory frameworks", "MiCA", "tokenised securities regulation", "compliance-first technology"],
    goals: "Exploring CBDC infrastructure and regulatory frameworks for tokenised securities under MiCA.",
    linkedin_url: null,
    twitter_handle: null,
    company_website: null,
    ai_summary: "Leads digital assets innovation at Deutsche Bundesbank. Focused on CBDC infrastructure and MiCA regulatory frameworks. Seeking compliance-first technology partners.",
    intent_tags: ["seeking_partnerships", "regulatory_engagement", "technology_evaluation", "knowledge_exchange"],
    deal_readiness_score: 0.0,
    enriched_profile: {},
    created_at: new Date().toISOString(),
  },
];

export default function Attendees() {
  const [attendees, setAttendees] = useState<Attendee[]>([]);
  const [search, setSearch] = useState("");
  const [filter, setFilter] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        const { attendees: data } = await listAttendees({ limit: 100 });
        setAttendees(data.length > 0 ? data : demoAttendees);
      } catch {
        setAttendees(demoAttendees);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  const filtered = attendees.filter((a) => {
    const matchesSearch =
      !search ||
      a.name.toLowerCase().includes(search.toLowerCase()) ||
      a.company.toLowerCase().includes(search.toLowerCase()) ||
      a.title.toLowerCase().includes(search.toLowerCase());
    const matchesFilter = !filter || a.ticket_type === filter;
    return matchesSearch && matchesFilter;
  });

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Attendees</h1>
          <p className="text-white/50 mt-1">
            {attendees.length} decision-makers registered
          </p>
        </div>
      </div>

      {/* Search and filter */}
      <div className="flex gap-3">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-white/30" />
          <input
            type="text"
            placeholder="Search by name, company, or title..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-10 pr-4 py-2.5 bg-white/5 border border-white/10 rounded-xl text-sm text-white placeholder:text-white/30 focus:outline-none focus:border-amber-400/50"
          />
        </div>
        <div className="flex gap-1.5">
          {["vip", "speaker", "sponsor", "delegate"].map((type) => (
            <button
              key={type}
              onClick={() => setFilter(filter === type ? null : type)}
              className={`px-3 py-2 rounded-lg text-xs font-medium border transition-all flex items-center gap-1.5 capitalize ${
                filter === type
                  ? ticketColors[type]
                  : "border-white/10 text-white/40 hover:text-white/60"
              }`}
            >
              {ticketIcons[type]}
              {type}
            </button>
          ))}
        </div>
      </div>

      {/* Attendee list */}
      {loading ? (
        <div className="text-center py-20 text-white/30">Loading...</div>
      ) : (
        <div className="grid gap-3">
          {filtered.map((attendee) => (
            <Link
              key={attendee.id}
              to={`/attendees/${attendee.id}`}
              className="flex items-center gap-4 p-4 rounded-xl bg-white/[0.03] border border-white/10 hover:border-amber-400/30 hover:bg-white/[0.05] transition-all group"
            >
              {/* Avatar */}
              <div className="w-12 h-12 rounded-full bg-gradient-to-br from-amber-400/20 to-amber-600/20 flex items-center justify-center text-amber-400 font-semibold text-lg shrink-0">
                {attendee.name[0]}
              </div>

              {/* Info */}
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className="font-semibold text-white">
                    {attendee.name}
                  </span>
                  <span
                    className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-medium border uppercase ${
                      ticketColors[attendee.ticket_type]
                    }`}
                  >
                    {ticketIcons[attendee.ticket_type]}
                    {attendee.ticket_type}
                  </span>
                </div>
                <div className="text-sm text-white/50">
                  {attendee.title} &middot; {attendee.company}
                </div>
                {attendee.ai_summary && (
                  <div className="text-xs text-white/30 mt-1 truncate">
                    <Brain className="w-3 h-3 inline mr-1" />
                    {attendee.ai_summary}
                  </div>
                )}
              </div>

              {/* Intent tags */}
              <div className="hidden md:flex flex-wrap gap-1 max-w-xs">
                {attendee.intent_tags.slice(0, 3).map((tag) => (
                  <span
                    key={tag}
                    className="px-2 py-0.5 rounded-full bg-white/5 text-white/40 text-[10px]"
                  >
                    {tag.replace(/_/g, " ")}
                  </span>
                ))}
              </div>

              {/* Deal readiness */}
              {attendee.deal_readiness_score != null && (
                <div className="hidden md:block text-right">
                  <div className="text-xs text-white/30">Deal Ready</div>
                  <div
                    className={`text-sm font-mono font-semibold ${
                      attendee.deal_readiness_score >= 0.5
                        ? "text-emerald-400"
                        : attendee.deal_readiness_score > 0
                        ? "text-amber-400"
                        : "text-white/20"
                    }`}
                  >
                    {(attendee.deal_readiness_score * 100).toFixed(0)}%
                  </div>
                </div>
              )}

              <ChevronRight className="w-4 h-4 text-white/20 group-hover:text-amber-400 transition-colors" />
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}

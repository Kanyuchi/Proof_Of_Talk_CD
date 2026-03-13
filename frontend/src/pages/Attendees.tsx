import { useState, useMemo } from "react";
import { Link } from "react-router-dom";
import {
  Search, Crown, Mic, Megaphone, User, ChevronRight, Brain, ShieldOff,
} from "lucide-react";
import { useAttendees } from "../hooks/useAttendees";
import { useMatches } from "../hooks/useMatches";
import { useAuth } from "../hooks/useAuth";
import EmptyState from "../components/EmptyState";

const ticketIcons: Record<string, React.ReactNode> = {
  vip: <Crown className="w-3.5 h-3.5 text-[#E76315]" />,
  speaker: <Mic className="w-3.5 h-3.5 text-purple-400" />,
  sponsor: <Megaphone className="w-3.5 h-3.5 text-emerald-400" />,
  delegate: <User className="w-3.5 h-3.5 text-blue-400" />,
};

const ticketColors: Record<string, string> = {
  vip: "bg-[#E76315]/10 text-[#E76315] border-[#E76315]/20",
  speaker: "bg-purple-400/10 text-purple-400 border-purple-400/20",
  sponsor: "bg-emerald-400/10 text-emerald-400 border-emerald-400/20",
  delegate: "bg-blue-400/10 text-blue-400 border-blue-400/20",
};

const TICKET_TYPES = ["vip", "speaker", "sponsor", "delegate"] as const;

const matchScoreColor: Record<string, string> = {
  deal_ready:    "bg-emerald-400/15 text-emerald-400 border-emerald-400/25",
  complementary: "bg-blue-400/15 text-blue-400 border-blue-400/25",
  non_obvious:   "bg-purple-400/15 text-purple-400 border-purple-400/25",
};

export default function Attendees() {
  const { data, isLoading } = useAttendees();
  const attendees = data?.attendees ?? [];
  const { user } = useAuth();
  const { data: matchData } = useMatches(user?.attendee_id ?? undefined);

  // Map each matched attendee's id → { score, type } for badge display
  const matchMap = useMemo(
    () =>
      new Map(
        (matchData?.matches ?? []).map((m) => [
          m.matched_attendee?.id,
          { score: m.overall_score, type: m.match_type },
        ]),
      ),
    [matchData],
  );

  const [search, setSearch] = useState("");
  const [filters, setFilters] = useState<string[]>([]);

  if (!user?.is_admin) {
    return (
      <div className="flex flex-col items-center justify-center h-64 gap-4 text-center">
        <ShieldOff className="w-10 h-10 text-white/20" />
        <div>
          <p className="text-white/50 font-medium">Admin access required</p>
          <p className="text-white/30 text-sm mt-1">The attendee directory is restricted to organisers.</p>
        </div>
        <Link to="/matches" className="text-sm text-[#E76315] hover:underline">
          Go to your matches →
        </Link>
      </div>
    );
  }

  const toggleFilter = (type: string) =>
    setFilters((prev) =>
      prev.includes(type) ? prev.filter((t) => t !== type) : [...prev, type]
    );

  const filtered = attendees.filter((a) => {
    const q = search.toLowerCase();
    const matchesSearch =
      !search ||
      a.name.toLowerCase().includes(q) ||
      a.company.toLowerCase().includes(q) ||
      a.title.toLowerCase().includes(q) ||
      (a.ai_summary?.toLowerCase().includes(q) ?? false);
    const matchesFilter = filters.length === 0 || filters.includes(a.ticket_type);
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
      <div className="flex flex-col sm:flex-row gap-3">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-white/30" />
          <input
            type="text"
            placeholder="Search by name, company, title, or summary…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-10 pr-4 py-2.5 bg-white/5 border border-white/10 rounded-xl text-sm text-white placeholder:text-white/30 focus:outline-none focus:border-[#E76315]/50"
          />
        </div>
        <div className="flex gap-1.5 flex-wrap">
          {TICKET_TYPES.map((type) => (
            <button
              key={type}
              onClick={() => toggleFilter(type)}
              className={`px-3 py-2 rounded-lg text-xs font-medium border transition-all flex items-center gap-1.5 capitalize ${
                filters.includes(type)
                  ? ticketColors[type]
                  : "border-white/10 text-white/40 hover:text-white/60"
              }`}
            >
              {ticketIcons[type]}
              {type}
            </button>
          ))}
          {filters.length > 0 && (
            <button
              onClick={() => setFilters([])}
              className="px-3 py-2 rounded-lg text-xs text-white/30 border border-white/5 hover:text-white/50 transition-all"
            >
              Clear
            </button>
          )}
        </div>
      </div>

      {/* Attendee list */}
      {isLoading ? (
        <div className="text-center py-20 text-white/30">Loading…</div>
      ) : filtered.length === 0 ? (
        <EmptyState
          title="No attendees found"
          description="Try a different search term or clear your filters."
          action={
            (search || filters.length > 0)
              ? { label: "Clear all filters", onClick: () => { setSearch(""); setFilters([]); } }
              : undefined
          }
        />
      ) : (
        <div className="grid gap-3">
          {filtered.map((attendee) => (
            <Link
              key={attendee.id}
              to={`/attendees/${attendee.id}`}
              className="flex items-center gap-4 p-4 rounded-xl bg-white/[0.03] border border-white/10 hover:border-[#E76315]/30 hover:bg-white/[0.05] transition-all group"
            >
              {/* Avatar */}
              <div className="w-12 h-12 rounded-full bg-gradient-to-br from-[#E76315]/20 to-[#D35400]/20 flex items-center justify-center text-[#E76315] font-semibold text-lg shrink-0">
                {attendee.name[0]}
              </div>

              {/* Info */}
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className="font-semibold text-white">{attendee.name}</span>
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

              {/* Match score badge (shown when logged in and this person is a match) */}
              {(() => {
                const myMatch = matchMap.get(attendee.id);
                if (!myMatch) return null;
                const colorClass = matchScoreColor[myMatch.type] ?? "bg-white/10 text-white/50 border-white/10";
                return (
                  <div className={`hidden md:block text-xs font-mono font-semibold px-2 py-0.5 rounded-full border ${colorClass}`}>
                    {(myMatch.score * 100).toFixed(0)}% match
                  </div>
                );
              })()}

              {/* Intent tags */}
              <div className="hidden md:flex flex-wrap gap-1 max-w-xs">
                {(attendee.intent_tags ?? []).slice(0, 3).map((tag) => (
                  <span key={tag} className="px-2 py-0.5 rounded-full bg-white/5 text-white/40 text-[10px]">
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
                        ? "text-[#E76315]"
                        : "text-white/20"
                    }`}
                  >
                    {(attendee.deal_readiness_score * 100).toFixed(0)}%
                  </div>
                </div>
              )}

              <ChevronRight className="w-4 h-4 text-white/20 group-hover:text-[#E76315] transition-colors" />
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}

import { useParams, Link, useNavigate } from "react-router-dom";
import {
  ArrowLeft, Handshake, Lightbulb, DollarSign, Check, X, Brain,
  Target, MessageSquare, Sparkles, Crown, Mic, Megaphone, User,
  Linkedin, Twitter, Globe, RefreshCw,
} from "lucide-react";
import { useAttendee } from "../hooks/useAttendee";
import { useMatches, useUpdateMatchStatus } from "../hooks/useMatches";
import { useAuth } from "../hooks/useAuth";
import { enrichAttendee } from "../api/client";
import { useState } from "react";

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

export default function AttendeeMatches() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { user } = useAuth();
  const { data: attendee, isLoading: loadingAttendee } = useAttendee(id);
  const { data: matchData, isLoading: loadingMatches } = useMatches(id);
  const updateStatus = useUpdateMatchStatus(id);
  const [enriching, setEnriching] = useState(false);

  const matches = matchData?.matches ?? [];
  const isLoading = loadingAttendee || loadingMatches;

  const handleStatus = (matchId: string, status: "accepted" | "declined") => {
    updateStatus.mutate({ matchId, status });
  };

  const handleMessage = (matchId: string) => {
    navigate(`/messages?match=${matchId}`);
  };

  const handleEnrich = async () => {
    if (!id) return;
    setEnriching(true);
    try {
      await enrichAttendee(id);
    } finally {
      setEnriching(false);
    }
  };

  if (isLoading) {
    return <div className="text-center py-20 text-white/30">Loading…</div>;
  }

  if (!attendee) {
    return <div className="text-center py-20 text-white/30">Attendee not found</div>;
  }

  const enriched = attendee.enriched_profile as Record<string, unknown>;
  const hasEnrichedData = Object.keys(enriched).length > 0;

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

      {/* Attendee profile card */}
      <div className="p-6 rounded-2xl bg-white/[0.03] border border-white/10">
        <div className="flex items-start gap-4">
          <div className="w-16 h-16 rounded-xl bg-gradient-to-br from-amber-400/20 to-amber-600/20 flex items-center justify-center text-amber-400 font-bold text-2xl shrink-0">
            {attendee.name[0]}
          </div>
          <div className="flex-1">
            <div className="flex items-center gap-3 flex-wrap">
              <h1 className="text-2xl font-bold">{attendee.name}</h1>
              {attendee.deal_readiness_score != null && attendee.deal_readiness_score > 0 && (
                <span className="px-2.5 py-1 rounded-full bg-emerald-400/10 text-emerald-400 text-xs border border-emerald-400/20 font-medium">
                  {(attendee.deal_readiness_score * 100).toFixed(0)}% Deal Ready
                </span>
              )}
            </div>
            <p className="text-white/50 mt-0.5">
              {attendee.title} &middot; {attendee.company}
            </p>

            {/* Social links */}
            <div className="flex items-center gap-3 mt-2">
              {attendee.linkedin_url && (
                <a href={attendee.linkedin_url} target="_blank" rel="noopener noreferrer"
                  className="text-white/30 hover:text-blue-400 transition-colors">
                  <Linkedin className="w-4 h-4" />
                </a>
              )}
              {attendee.twitter_handle && (
                <a href={`https://twitter.com/${attendee.twitter_handle.replace("@", "")}`} target="_blank" rel="noopener noreferrer"
                  className="text-white/30 hover:text-sky-400 transition-colors">
                  <Twitter className="w-4 h-4" />
                </a>
              )}
              {attendee.company_website && (
                <a href={attendee.company_website} target="_blank" rel="noopener noreferrer"
                  className="text-white/30 hover:text-amber-400 transition-colors">
                  <Globe className="w-4 h-4" />
                </a>
              )}
              {/* Enrich button */}
              <button
                onClick={handleEnrich}
                disabled={enriching}
                className="ml-auto flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-white/10 text-white/40 text-xs hover:border-amber-400/30 hover:text-amber-400 transition-all disabled:opacity-40"
              >
                <RefreshCw className={`w-3 h-3 ${enriching ? "animate-spin" : ""}`} />
                {enriching ? "Enriching…" : "Enrich Profile"}
              </button>
            </div>

            {attendee.ai_summary && (
              <p className="text-sm text-white/40 mt-3 flex items-start gap-2">
                <Brain className="w-4 h-4 mt-0.5 shrink-0 text-amber-400" />
                {attendee.ai_summary}
              </p>
            )}

            {attendee.goals && (
              <div className="mt-3 p-3 rounded-xl bg-white/[0.02] border border-white/5">
                <div className="text-[10px] text-white/30 uppercase font-medium mb-1">Goals</div>
                <p className="text-sm text-white/60">{attendee.goals}</p>
              </div>
            )}

            <div className="flex flex-wrap gap-1.5 mt-3">
              {(attendee.intent_tags ?? []).map((tag) => (
                <span key={tag} className="px-2.5 py-1 rounded-full bg-amber-400/10 text-amber-400 text-xs border border-amber-400/20">
                  {tag.replace(/_/g, " ")}
                </span>
              ))}
            </div>

            {/* Interests */}
            {(attendee.interests ?? []).length > 0 && (
              <div className="flex flex-wrap gap-1 mt-2">
                {attendee.interests.map((i) => (
                  <span key={i} className="px-2 py-0.5 rounded-full bg-white/5 text-white/30 text-xs">
                    {i}
                  </span>
                ))}
              </div>
            )}

            {/* Enriched data */}
            {hasEnrichedData && (
              <div className="mt-4 p-4 rounded-xl bg-white/[0.02] border border-white/5 space-y-2">
                <div className="text-[10px] text-white/30 uppercase font-medium">Enriched Data</div>
                {(enriched.linkedin_summary as string) && (
                  <div>
                    <div className="text-xs text-blue-400 mb-0.5 flex items-center gap-1"><Linkedin className="w-3 h-3" /> LinkedIn</div>
                    <p className="text-xs text-white/50">{enriched.linkedin_summary as string}</p>
                  </div>
                )}
                {(enriched.twitter_summary as string) && (
                  <div>
                    <div className="text-xs text-sky-400 mb-0.5 flex items-center gap-1"><Twitter className="w-3 h-3" /> Twitter/X</div>
                    <p className="text-xs text-white/50">{enriched.twitter_summary as string}</p>
                  </div>
                )}
                {(enriched.website_summary as string) && (
                  <div>
                    <div className="text-xs text-amber-400 mb-0.5 flex items-center gap-1"><Globe className="w-3 h-3" /> Website</div>
                    <p className="text-xs text-white/50">{enriched.website_summary as string}</p>
                  </div>
                )}
              </div>
            )}
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
          const config = matchTypeConfig[match.match_type] ?? matchTypeConfig.complementary;
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
              {/* Match header */}
              <div className="px-5 py-3 bg-white/[0.02] border-b border-white/5 flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <span className="text-lg font-bold text-white/20">#{idx + 1}</span>
                  <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium border ${config.bg}`}>
                    <Icon className="w-3 h-3" />
                    {config.label}
                  </span>
                  <span className="text-xs text-white/30 hidden sm:block">{config.description}</span>
                </div>
                <div className="text-right">
                  <div className="text-xs text-white/30">Match Score</div>
                  <div className="text-lg font-bold text-amber-400">
                    {(match.overall_score * 100).toFixed(0)}%
                  </div>
                </div>
              </div>

              {/* Match body */}
              <div className="p-5 space-y-4">
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
                  <p className="text-sm text-white/70 leading-relaxed">{match.explanation}</p>
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
                            <span key={s} className="text-xs text-white/50 bg-white/5 px-2 py-0.5 rounded-full">{s}</span>
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
                            <span key={s} className="text-xs text-white/50 bg-white/5 px-2 py-0.5 rounded-full">{s}</span>
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
                            <li key={a} className="text-xs text-white/50">&bull; {a}</li>
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
                  <div className="flex items-center gap-3 pt-2">
                    <div className="flex items-center gap-2 text-sm text-emerald-400">
                      <Check className="w-4 h-4" />
                      Meeting accepted
                    </div>
                    {user && (
                      <button
                        onClick={() => handleMessage(match.id)}
                        className="flex items-center gap-2 px-3 py-1.5 bg-amber-400/10 text-amber-400 border border-amber-400/20 rounded-lg text-sm font-medium hover:bg-amber-400/20 transition-all"
                      >
                        <MessageSquare className="w-3.5 h-3.5" />
                        Send Message
                      </button>
                    )}
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

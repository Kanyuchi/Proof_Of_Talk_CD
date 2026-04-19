import { useParams, Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import {
  FileText, Printer, ArrowLeft, Sparkles, Brain, Target,
  Linkedin, Twitter, Globe, Calendar, MapPin, Clock,
  ChevronRight, Shield, TrendingUp,
} from "lucide-react";
import { getMatchesByMagicLink, getAttendee } from "../api/client";
import { matchTypeConfig, twitterUrl, formatMeetingTime } from "../utils/matchHelpers";
import AttendeeAvatar from "../components/AttendeeAvatar";
import type { Match, Attendee } from "../types";
import type { LucideIcon } from "lucide-react";

/* ── helpers ─────────────────────────────────────────────────────────── */

const scoreLabel = (s: number) =>
  s >= 0.8 ? "Very Strong" : s >= 0.7 ? "Strong" : s >= 0.6 ? "Good" : "Moderate";

const scoreColor = (s: number) =>
  s >= 0.8 ? "text-emerald-400" : s >= 0.7 ? "text-[#E76315]" : s >= 0.6 ? "text-yellow-400" : "text-white/50";

function gridData(a: Attendee) {
  const ep = a.enriched_profile as Record<string, unknown> | undefined;
  if (!ep) return null;
  const g = ep.grid as Record<string, unknown> | undefined;
  if (!g || !g.grid_name) return null;
  return g;
}

/* ── main page ───────────────────────────────────────────────────────── */

export default function Briefing() {
  const { token } = useParams<{ token: string }>();

  const { data, isLoading, error } = useQuery({
    queryKey: ["magic-matches", token],
    queryFn: () => getMatchesByMagicLink(token!, 10),
    enabled: !!token,
  });

  const attendeeId = data?.attendee_id;
  const { data: attendee } = useQuery({
    queryKey: ["attendee", attendeeId],
    queryFn: () => getAttendee(attendeeId!),
    enabled: !!attendeeId,
  });

  const matches: Match[] = data?.matches ?? [];
  const scheduled = matches.filter((m) => m.meeting_time);
  const accepted = matches.filter(
    (m) => m.status_a === "accepted" && m.status_b === "accepted",
  );

  /* ── loading / error states ──────────────────────────────────────── */

  if (isLoading) {
    return (
      <div className="text-center py-20">
        <div className="inline-block w-8 h-8 border-2 border-[#E76315] border-t-transparent rounded-full animate-spin" />
        <p className="text-white/30 mt-4 text-sm">Preparing your meeting brief...</p>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="max-w-xl mx-auto py-20 text-center">
        <FileText className="w-12 h-12 text-white/20 mx-auto mb-4" />
        <h2 className="text-xl text-white mb-2">Briefing not available</h2>
        <p className="text-white/40 text-sm">
          This link may be invalid or expired. Contact the Proof of Talk team for help.
        </p>
      </div>
    );
  }

  /* ── render ───────────────────────────────────────────────────────── */

  return (
    <div className="max-w-4xl mx-auto px-4 py-8 print:px-0 print:py-0">
      {/* ── toolbar (hidden in print) ──────────────────────────────── */}
      <div className="flex items-center justify-between mb-8 print:hidden">
        <Link
          to={`/m/${token}`}
          className="flex items-center gap-2 text-white/40 hover:text-white text-sm"
        >
          <ArrowLeft className="w-4 h-4" /> Back to matches
        </Link>
        <button
          onClick={() => window.print()}
          className="flex items-center gap-2 px-4 py-2 bg-[#E76315] text-white rounded-lg hover:bg-[#c5520f] text-sm font-medium"
        >
          <Printer className="w-4 h-4" /> Print / Save PDF
        </button>
      </div>

      {/* ── header ─────────────────────────────────────────────────── */}
      <div className="bg-gradient-to-br from-[#1a1a2e] to-[#16213e] rounded-2xl p-8 mb-8 border border-white/5 print:border-none print:bg-white print:text-black">
        <div className="flex items-center gap-2 text-[#E76315] text-sm font-semibold mb-4 print:text-[#E76315]">
          <FileText className="w-5 h-5" />
          MEETING PREP BRIEF
        </div>

        <h1 className="text-3xl font-bold text-white mb-1 print:text-black">
          Proof of Talk 2026
        </h1>
        <p className="text-white/40 text-sm mb-6 print:text-gray-500">
          Louvre Palace, Paris &middot; June 2&ndash;3, 2026
        </p>

        {attendee && (
          <div className="flex items-center gap-4">
            <AttendeeAvatar attendee={attendee} size="lg" />
            <div>
              <h2 className="text-xl font-semibold text-white print:text-black">
                {attendee.name}
              </h2>
              <p className="text-white/50 text-sm print:text-gray-500">
                {attendee.title} &middot; {attendee.company}
              </p>
              {attendee.ai_summary && (
                <p className="text-white/30 text-xs mt-1 max-w-2xl print:text-gray-400">
                  {attendee.ai_summary}
                </p>
              )}
            </div>
          </div>
        )}

        {/* ── quick stats ── */}
        <div className="grid grid-cols-3 gap-4 mt-6 pt-6 border-t border-white/10 print:border-gray-200">
          <div>
            <p className="text-2xl font-bold text-white print:text-black">{matches.length}</p>
            <p className="text-white/40 text-xs print:text-gray-500">AI Matches</p>
          </div>
          <div>
            <p className="text-2xl font-bold text-emerald-400 print:text-emerald-600">{accepted.length}</p>
            <p className="text-white/40 text-xs print:text-gray-500">Mutual Accepts</p>
          </div>
          <div>
            <p className="text-2xl font-bold text-[#E76315]">{scheduled.length}</p>
            <p className="text-white/40 text-xs print:text-gray-500">Meetings Scheduled</p>
          </div>
        </div>
      </div>

      {/* ── scheduled meetings ─────────────────────────────────────── */}
      {scheduled.length > 0 && (
        <div className="mb-8">
          <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2 print:text-black">
            <Calendar className="w-5 h-5 text-[#E76315]" />
            Scheduled Meetings
          </h2>
          <div className="space-y-3">
            {scheduled.map((m) => {
              const other = m.matched_attendee;
              return (
                <div
                  key={m.id}
                  className="bg-[#1a1a2e] rounded-xl p-4 border border-white/5 flex items-center gap-4 print:bg-gray-50 print:border-gray-200"
                >
                  <div className="flex-shrink-0 w-12 h-12 bg-[#E76315]/20 rounded-lg flex items-center justify-center">
                    <Clock className="w-5 h-5 text-[#E76315]" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-white font-medium truncate print:text-black">
                      {other?.name ?? "TBD"}{" "}
                      <span className="text-white/30 font-normal print:text-gray-400">
                        {other?.title} &middot; {other?.company}
                      </span>
                    </p>
                    <p className="text-white/50 text-sm print:text-gray-500">
                      {m.meeting_time ? formatMeetingTime(m.meeting_time) : "Time TBD"}
                      {m.meeting_location && (
                        <>
                          {" "}&middot;{" "}
                          <MapPin className="w-3 h-3 inline" /> {m.meeting_location}
                        </>
                      )}
                    </p>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* ── match briefings ────────────────────────────────────────── */}
      <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2 print:text-black">
        <Sparkles className="w-5 h-5 text-[#E76315]" />
        Your AI-Matched Connections ({matches.length})
      </h2>

      <div className="space-y-6">
        {matches.map((m, i) => (
          <MatchBriefCard key={m.id} match={m} index={i + 1} />
        ))}
      </div>

      {/* ── footer ─────────────────────────────────────────────────── */}
      <div className="mt-12 pt-6 border-t border-white/10 text-center text-white/20 text-xs print:border-gray-200 print:text-gray-400">
        <p>Generated by POT Matchmaker &middot; Proof of Talk 2026</p>
        <p className="mt-1">
          This briefing combines verified company data, self-reported goals, and AI analysis.
          Fields marked as AI-inferred should be verified before acting on them.
        </p>
      </div>
    </div>
  );
}


/* ── per-match card ──────────────────────────────────────────────────── */

function MatchBriefCard({ match, index }: { match: Match; index: number }) {
  const other = match.matched_attendee;
  if (!other) return null;

  const cfg = matchTypeConfig[match.match_type] || matchTypeConfig.complementary;
  const Icon = cfg.icon as LucideIcon;
  const grid = gridData(other);
  const actionItems = match.shared_context?.action_items ?? [];
  const synergies = match.shared_context?.synergies ?? [];
  const sectors = match.shared_context?.sectors ?? [];

  return (
    <div className="bg-[#1a1a2e] rounded-2xl border border-white/5 overflow-hidden print:bg-white print:border-gray-200 print:break-inside-avoid">
      {/* ── header bar ── */}
      <div className="flex items-center justify-between px-6 py-3 bg-white/[0.02] border-b border-white/5 print:bg-gray-50 print:border-gray-200">
        <div className="flex items-center gap-3">
          <span className="text-white/20 text-sm font-mono print:text-gray-400">#{index}</span>
          <span className={`text-xs font-semibold px-2 py-0.5 rounded flex items-center gap-1 ${cfg.bg}`}>
            <Icon className="w-3 h-3" /> {cfg.label}
          </span>
        </div>
        <div className="flex items-center gap-2">
          <span className={`text-sm font-semibold ${scoreColor(match.overall_score)}`}>
            {Math.round(match.overall_score * 100)}%
          </span>
          <span className="text-white/20 text-xs print:text-gray-400">
            {scoreLabel(match.overall_score)}
          </span>
        </div>
      </div>

      <div className="p-6">
        {/* ── person info ── */}
        <div className="flex items-start gap-4 mb-5">
          <AttendeeAvatar attendee={other} size="md" />
          <div className="flex-1 min-w-0">
            <h3 className="text-lg font-semibold text-white print:text-black">
              {other.name}
            </h3>
            <p className="text-white/50 text-sm print:text-gray-500">
              {other.title} &middot; {other.company}
            </p>

            {/* social links */}
            <div className="flex items-center gap-3 mt-2 print:hidden">
              {other.linkedin_url && (
                <a
                  href={other.linkedin_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-white/30 hover:text-blue-400"
                >
                  <Linkedin className="w-4 h-4" />
                </a>
              )}
              {other.twitter_handle && (
                <a
                  href={twitterUrl(other.twitter_handle)}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-white/30 hover:text-sky-400"
                >
                  <Twitter className="w-4 h-4" />
                </a>
              )}
              {other.company_website && (
                <a
                  href={other.company_website}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-white/30 hover:text-white"
                >
                  <Globe className="w-4 h-4" />
                </a>
              )}
            </div>
          </div>
        </div>

        {/* ── AI summary of the match ── */}
        {other.ai_summary && (
          <div className="mb-5 p-3 bg-white/[0.03] rounded-lg border border-white/5 print:bg-gray-50 print:border-gray-200">
            <p className="text-white/50 text-sm leading-relaxed print:text-gray-600">
              {other.ai_summary}
            </p>
          </div>
        )}

        {/* ── why you should meet ── */}
        <div className="mb-5">
          <h4 className="text-[#E76315] text-xs font-semibold uppercase tracking-wider mb-2 flex items-center gap-1.5">
            <Brain className="w-3.5 h-3.5" /> Why You Should Meet
          </h4>
          <p className="text-white/70 text-sm leading-relaxed print:text-gray-700">
            {match.explanation}
          </p>
        </div>

        {/* ── talking points ── */}
        {actionItems.length > 0 && (
          <div className="mb-5">
            <h4 className="text-emerald-400 text-xs font-semibold uppercase tracking-wider mb-2 flex items-center gap-1.5 print:text-emerald-600">
              <Target className="w-3.5 h-3.5" /> Talking Points
            </h4>
            <ul className="space-y-2">
              {actionItems.map((item, j) => (
                <li key={j} className="flex items-start gap-2 text-sm">
                  <ChevronRight className="w-4 h-4 text-emerald-400/50 flex-shrink-0 mt-0.5 print:text-emerald-600" />
                  <span className="text-white/60 print:text-gray-600">{item}</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* ── shared context ── */}
        {(sectors.length > 0 || synergies.length > 0) && (
          <div className="mb-5">
            <h4 className="text-purple-400 text-xs font-semibold uppercase tracking-wider mb-2 flex items-center gap-1.5 print:text-purple-600">
              <TrendingUp className="w-3.5 h-3.5" /> Shared Context
            </h4>
            {sectors.length > 0 && (
              <div className="flex flex-wrap gap-1.5 mb-2">
                {sectors.map((s, j) => (
                  <span
                    key={j}
                    className="text-xs px-2 py-0.5 rounded bg-purple-500/10 text-purple-300 print:bg-purple-50 print:text-purple-700"
                  >
                    {s}
                  </span>
                ))}
              </div>
            )}
            {synergies.length > 0 && (
              <ul className="space-y-1">
                {synergies.map((s, j) => (
                  <li key={j} className="text-white/40 text-xs print:text-gray-500">
                    &bull; {s}
                  </li>
                ))}
              </ul>
            )}
          </div>
        )}

        {/* ── Grid company intelligence ── */}
        {grid && (
          <div className="p-3 bg-emerald-500/5 rounded-lg border border-emerald-500/10 print:bg-emerald-50 print:border-emerald-200">
            <div className="flex items-center gap-1.5 mb-1.5">
              <Shield className="w-3.5 h-3.5 text-emerald-400 print:text-emerald-600" />
              <span className="text-emerald-400 text-xs font-semibold print:text-emerald-600">
                Verified by The Grid
              </span>
            </div>
            <p className="text-white/40 text-xs leading-relaxed print:text-gray-500">
              {String((grid as Record<string, unknown>).grid_description ?? "")}
            </p>
            {typeof (grid as Record<string, unknown>).grid_sector === "string" && (
              <span className="inline-block text-xs px-2 py-0.5 mt-2 rounded bg-emerald-500/10 text-emerald-300 print:bg-emerald-100 print:text-emerald-700">
                {(grid as Record<string, string>).grid_sector}
              </span>
            )}
          </div>
        )}

        {/* ── meeting status (if scheduled) ── */}
        {match.meeting_time && (
          <div className="mt-4 p-3 bg-[#E76315]/10 rounded-lg border border-[#E76315]/20 print:bg-orange-50 print:border-orange-200">
            <div className="flex items-center gap-2">
              <Calendar className="w-4 h-4 text-[#E76315]" />
              <span className="text-[#E76315] text-sm font-medium">
                Meeting scheduled: {formatMeetingTime(match.meeting_time)}
              </span>
            </div>
            {match.meeting_location && (
              <p className="text-white/40 text-xs mt-1 pl-6 print:text-gray-500">
                <MapPin className="w-3 h-3 inline" /> {match.meeting_location}
              </p>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

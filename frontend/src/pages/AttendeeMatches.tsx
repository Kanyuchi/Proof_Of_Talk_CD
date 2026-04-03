import { useParams, Link, useNavigate } from "react-router-dom";
import { verticalDisplayName } from "../utils/verticals";
import GridOrgCard from "../components/GridOrgCard";
import {
  ArrowLeft, Check, X, Brain,
  Target, MessageSquare, Sparkles,
  Linkedin, Twitter, Globe, RefreshCw, AlertTriangle, Copy, CheckCheck,
  Calendar, Clock, Download,
} from "lucide-react";
import { useAttendee } from "../hooks/useAttendee";
import { useMatches, useUpdateMatchStatus, useScheduleMeeting, useMeetingFeedback } from "../hooks/useMatches";
import { useAuth } from "../hooks/useAuth";
import { enrichAttendee } from "../api/client";
import { useState } from "react";
import {
  CONFERENCE_SLOTS, slotToISO, formatMeetingTime, downloadICS,
  matchTypeConfig, ticketIcons, buildIcebreaker, twitterUrl,
} from "../utils/matchHelpers";

export default function AttendeeMatches() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { user } = useAuth();
  const { data: attendee, isLoading: loadingAttendee } = useAttendee(id);
  const { data: matchData, isLoading: loadingMatches } = useMatches(id);
  const updateStatus = useUpdateMatchStatus(id);
  const scheduleMeeting = useScheduleMeeting(id);
  const feedback = useMeetingFeedback(id);
  const [enriching, setEnriching] = useState(false);
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [schedulingMatchId, setSchedulingMatchId] = useState<string | null>(null);
  const [selectedDay, setSelectedDay] = useState<string>("June 2");
  const [selectedTime, setSelectedTime] = useState<string | null>(null);
  const [decliningMatchId, setDecliningMatchId] = useState<string | null>(null);
  const [declineReason, setDeclineReason] = useState("");

  const matches = matchData?.matches ?? [];
  const isLoading = loadingAttendee || loadingMatches;

  const handleStatus = (
    matchId: string,
    status: "accepted" | "declined" | "met",
    decline_reason?: string
  ) => {
    updateStatus.mutate({ matchId, status, decline_reason });
  };

  const handleDecline = (matchId: string) => {
    setDecliningMatchId(matchId);
    setDeclineReason("");
  };

  const confirmDecline = (matchId: string) => {
    handleStatus(matchId, "declined", declineReason.trim() || undefined);
    setDecliningMatchId(null);
    setDeclineReason("");
  };

  const handleMarkMet = (matchId: string) => {
    handleStatus(matchId, "met");
    feedback.mutate({
      matchId,
      meeting_outcome: "met",
      met_at: new Date().toISOString(),
    });
  };

  const handleCopyIcebreaker = (text: string, matchId: string) => {
    navigator.clipboard.writeText(text).then(() => {
      setCopiedId(matchId);
      setTimeout(() => setCopiedId(null), 2000);
    });
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

  // Determine this attendee's own status on a match (which side they're on)
  const myStatusFor = (match: { attendee_a_id: string; attendee_b_id: string; status_a: string; status_b: string }) => {
    if (!id) return null;
    if (match.attendee_a_id === id) return match.status_a;
    if (match.attendee_b_id === id) return match.status_b;
    return null;
  };

  const otherStatusFor = (match: { attendee_a_id: string; attendee_b_id: string; status_a: string; status_b: string }) => {
    if (!id) return null;
    if (match.attendee_a_id === id) return match.status_b;
    if (match.attendee_b_id === id) return match.status_a;
    return null;
  };

  if (isLoading) {
    return <div className="text-center py-20 text-white/30">Loading…</div>;
  }

  if (!attendee) {
    return <div className="text-center py-20 text-white/30">Attendee not found</div>;
  }

  const enriched = attendee.enriched_profile as Record<string, unknown>;
  // Show enriched section only when at least one display field has content
  const hasEnrichedData = !!(enriched.linkedin_summary || enriched.twitter_summary || enriched.website_summary);

  // Profile completeness — labelled fields for tooltip
  const completenessFields = [
    { label: "Goals",       ok: !!attendee.goals },
    { label: "Interests",   ok: (attendee.interests?.length ?? 0) > 0 },
    { label: "LinkedIn",    ok: !!attendee.linkedin_url },
    { label: "Twitter",     ok: !!attendee.twitter_handle },
    { label: "Website",     ok: !!attendee.company_website },
    { label: "AI Summary",  ok: !!attendee.ai_summary },
    { label: "Intent Tags", ok: (attendee.intent_tags?.length ?? 0) > 0 },
  ];
  const completeness = Math.round(
    (completenessFields.filter((f) => f.ok).length / completenessFields.length) * 100
  );
  const missingGoals = !attendee.goals;

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

      {/* Goals warning — missing goals reduces match accuracy */}
      {missingGoals && (
        <div className="flex items-start gap-3 p-4 rounded-xl border border-[#E76315]/30 bg-[#E76315]/5">
          <AlertTriangle className="w-4 h-4 text-[#E76315] mt-0.5 shrink-0" />
          <div>
            <p className="text-sm font-medium text-[#E76315]">Goals not set — match quality may be reduced</p>
            <p className="text-xs text-white/40 mt-0.5">
              Adding your conference goals helps the AI find the most relevant connections for you.
              Edit your profile to complete this field.
            </p>
          </div>
        </div>
      )}

      {/* Attendee profile card */}
      <div className="p-6 rounded-2xl bg-white/[0.03] border border-white/10">
        <div className="flex items-start gap-4">
          <div className="w-16 h-16 rounded-xl bg-gradient-to-br from-[#E76315]/20 to-[#D35400]/20 flex items-center justify-center text-[#E76315] font-bold text-2xl shrink-0">
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
                <a href={twitterUrl(attendee.twitter_handle)} target="_blank" rel="noopener noreferrer"
                  className="text-white/30 hover:text-sky-400 transition-colors">
                  <Twitter className="w-4 h-4" />
                </a>
              )}
              {attendee.company_website && (
                <a href={attendee.company_website} target="_blank" rel="noopener noreferrer"
                  className="text-white/30 hover:text-[#E76315] transition-colors">
                  <Globe className="w-4 h-4" />
                </a>
              )}
              {/* Enrich button — admin only */}
              {user?.is_admin && (
                <button
                  onClick={handleEnrich}
                  disabled={enriching}
                  className="ml-auto flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-white/10 text-white/40 text-xs hover:border-[#E76315]/30 hover:text-[#E76315] transition-all disabled:opacity-40"
                >
                  <RefreshCw className={`w-3 h-3 ${enriching ? "animate-spin" : ""}`} />
                  {enriching ? "Enriching…" : "Enrich Profile"}
                </button>
              )}
            </div>

            {/* Profile completeness indicator with hover tooltip */}
            <div className="mt-3 group relative">
              <div className="flex items-center gap-3">
                <div className="flex-1 h-1.5 bg-white/5 rounded-full overflow-hidden">
                  <div
                    className={`h-full rounded-full transition-all ${
                      completeness >= 80 ? "bg-emerald-400" : completeness >= 50 ? "bg-[#E76315]" : "bg-red-400"
                    }`}
                    style={{ width: `${completeness}%` }}
                  />
                </div>
                <span className="text-[10px] text-white/30 shrink-0">
                  Profile {completeness}% complete
                </span>
              </div>
              {/* Tooltip */}
              <div className="absolute bottom-full left-0 mb-2 hidden group-hover:block z-10
                bg-[#1a1a2e] border border-white/10 rounded-lg p-3 text-xs min-w-48 shadow-xl">
                {completenessFields.map((f) => (
                  <div
                    key={f.label}
                    className={`flex items-center gap-2 py-0.5 ${f.ok ? "text-emerald-400" : "text-white/30"}`}
                  >
                    <span>{f.ok ? "✓" : "✗"}</span>
                    {f.label}
                  </div>
                ))}
              </div>
            </div>

            {attendee.ai_summary && (
              <p className="text-sm text-white/40 mt-3 flex items-start gap-2">
                <Brain className="w-4 h-4 mt-0.5 shrink-0 text-[#E76315]" />
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
                <span key={tag} className="px-2.5 py-1 rounded-full bg-[#E76315]/10 text-[#E76315] text-xs border border-[#E76315]/20">
                  {tag.replace(/_/g, " ")}
                </span>
              ))}
            </div>

            {(attendee.vertical_tags ?? []).length > 0 && (
              <div className="flex flex-wrap gap-1.5 mt-2">
                {attendee.vertical_tags.map((tag) => (
                  <span key={tag} className="px-2.5 py-1 rounded-full bg-purple-500/10 text-purple-400 text-xs border border-purple-500/20">
                    {verticalDisplayName(tag)}
                  </span>
                ))}
              </div>
            )}

            {/* Grid B2B data */}
            {(attendee.enriched_profile as Record<string, any>)?.grid?.grid_description && (
              <div className="mt-3">
                <GridOrgCard grid={(attendee.enriched_profile as Record<string, any>).grid} />
              </div>
            )}

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

            {/* Enriched data — admin only (raw scraped data, not for public view) */}
            {user?.is_admin && hasEnrichedData && (
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
                    <div className="text-xs text-[#E76315] mb-0.5 flex items-center gap-1"><Globe className="w-3 h-3" /> Website</div>
                    <p className="text-xs text-white/50">{enriched.website_summary as string}</p>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Match section — admin sees all matches; attendees only see their own */}
      {!user?.is_admin && user?.attendee_id !== id ? (
        <div className="p-6 rounded-2xl bg-white/[0.03] border border-white/10 text-center space-y-2">
          <Sparkles className="w-6 h-6 text-[#E76315] mx-auto" />
          <p className="text-sm text-white/40">
            Match recommendations are private to each attendee.
          </p>
          <Link to="/matches" className="inline-block text-xs text-[#E76315] hover:underline mt-1">
            View your own matches →
          </Link>
        </div>
      ) : (
      <>
      {/* Match heading */}
      <div className="flex items-center gap-3">
        <Sparkles className="w-5 h-5 text-[#E76315]" />
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
              className={`rounded-2xl border border-l-4 ${config.leftBorder} overflow-hidden transition-all ${
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
                  <div className="text-lg font-bold text-[#E76315]">
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
                      {/* Social links */}
                      <div className="flex items-center gap-2 mt-1">
                        {person.linkedin_url && (
                          <a href={person.linkedin_url} target="_blank" rel="noopener noreferrer"
                            className="text-white/30 hover:text-blue-400 transition-colors">
                            <Linkedin className="w-3.5 h-3.5" />
                          </a>
                        )}
                        {person.twitter_handle && (
                          <a href={twitterUrl(person.twitter_handle)} target="_blank" rel="noopener noreferrer"
                            className="text-white/30 hover:text-sky-400 transition-colors">
                            <Twitter className="w-3.5 h-3.5" />
                          </a>
                        )}
                        {person.company_website && (
                          <a href={person.company_website} target="_blank" rel="noopener noreferrer"
                            className="text-white/30 hover:text-[#E76315] transition-colors">
                            <Globe className="w-3.5 h-3.5" />
                          </a>
                        )}
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

                {/* Vertical tags */}
                {person && (person.vertical_tags ?? []).length > 0 && (
                  <div className="flex flex-wrap gap-1.5">
                    {person.vertical_tags.map((tag: string) => (
                      <span key={tag} className="px-2 py-0.5 rounded-full bg-purple-500/10 text-purple-300 text-xs border border-purple-500/20">
                        {tag.replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase())}
                      </span>
                    ))}
                  </div>
                )}

                {/* Grid card */}
                {person && (person.enriched_profile as Record<string, any>)?.grid?.grid_description && (
                  <GridOrgCard grid={(person.enriched_profile as Record<string, any>).grid} />
                )}

                {/* AI Explanation */}
                <div className="p-4 rounded-xl bg-[#E76315]/5 border border-[#E76315]/10">
                  <div className="flex items-center gap-2 text-xs text-[#E76315] font-medium mb-2">
                    <Brain className="w-3.5 h-3.5" />
                    Why this meeting matters
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

                {/* Actions — two-sided consent */}
                {(() => {
                  const myStatus = myStatusFor(match);
                  const otherStatus = otherStatusFor(match);
                  const isMutual = match.status === "accepted";
                  const iDeclined = myStatus === "declined";
                  const iAccepted = myStatus === "accepted";

                  if (iDeclined || match.status === "declined") {
                    return (
                      <div className="flex items-center gap-2 text-sm text-white/30 pt-2">
                        <X className="w-4 h-4" />
                        Declined
                      </div>
                    );
                  }

                  if (isMutual) {
                    const icebreaker = person
                      ? buildIcebreaker(
                          person.name,
                          person.title,
                          person.company,
                          match.shared_context?.action_items,
                        )
                      : "";
                    const isScheduling = schedulingMatchId === match.id;
                    const daySlots = CONFERENCE_SLOTS.filter((g) => g.day === selectedDay);

                    return (
                      <div className="space-y-3 pt-2">
                        {/* Mutual match header */}
                        <div className="flex items-center gap-3 flex-wrap">
                          <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-emerald-400/10 border border-emerald-400/20 text-sm text-emerald-400 font-medium">
                            <Check className="w-4 h-4" />
                            Mutual match — both accepted!
                          </div>
                          {user && (
                            <button
                              onClick={() => handleMessage(match.id)}
                              className="flex items-center gap-2 px-3 py-1.5 bg-[#E76315]/10 text-[#E76315] border border-[#E76315]/20 rounded-lg text-sm font-medium hover:bg-[#E76315]/20 transition-all"
                            >
                              <MessageSquare className="w-3.5 h-3.5" />
                              Send Message
                            </button>
                          )}
                        </div>

                        {/* Scheduled meeting — if already booked */}
                        {match.meeting_time ? (
                          <div className="p-3 rounded-xl bg-emerald-400/5 border border-emerald-400/20 flex items-center justify-between gap-3 flex-wrap">
                            <div className="flex items-center gap-2 text-sm">
                              <Calendar className="w-4 h-4 text-emerald-400 shrink-0" />
                              <div>
                                <div className="text-emerald-400 font-medium">
                                  {formatMeetingTime(match.meeting_time)}
                                </div>
                                <div className="text-xs text-white/40 mt-0.5">
                                  {match.meeting_location}
                                </div>
                              </div>
                            </div>
                            <button
                              onClick={() =>
                                person &&
                                downloadICS(
                                  match.meeting_time!,
                                  attendee.name,
                                  person.name,
                                  person.company,
                                  match.meeting_location ?? "Louvre Palace, Paris",
                                  match.explanation,
                                )
                              }
                              className="flex items-center gap-1.5 px-3 py-1.5 bg-white/5 text-white/50 border border-white/10 rounded-lg text-xs hover:text-[#E76315] hover:border-[#E76315]/30 transition-all"
                            >
                              <Download className="w-3 h-3" />
                              Add to Calendar
                            </button>
                          </div>
                        ) : (
                          /* Schedule meeting block */
                          <div className="rounded-xl border border-white/10 overflow-hidden">
                            <button
                              onClick={() => {
                                setSchedulingMatchId(isScheduling ? null : match.id);
                                setSelectedTime(null);
                              }}
                              className="w-full flex items-center gap-2 px-4 py-2.5 bg-white/[0.02] text-sm text-white/50 hover:text-[#E76315] hover:bg-[#E76315]/5 transition-all text-left"
                            >
                              <Clock className="w-4 h-4" />
                              {isScheduling ? "Cancel scheduling" : "Schedule a meeting at POT 2026"}
                            </button>

                            {isScheduling && (
                              <div className="p-4 space-y-3 bg-white/[0.02]">
                                {/* Day selector */}
                                <div className="flex gap-2">
                                  {["June 2", "June 3"].map((day) => (
                                    <button
                                      key={day}
                                      onClick={() => { setSelectedDay(day); setSelectedTime(null); }}
                                      className={`flex-1 py-1.5 rounded-lg text-xs font-medium border transition-all ${
                                        selectedDay === day
                                          ? "bg-[#E76315]/10 border-[#E76315]/30 text-[#E76315]"
                                          : "bg-white/5 border-white/10 text-white/40 hover:text-white/60"
                                      }`}
                                    >
                                      {day === "June 2" ? "Mon, Jun 2" : "Tue, Jun 3"}
                                    </button>
                                  ))}
                                </div>

                                {/* Time slots grouped by period */}
                                {daySlots.map((group) => (
                                  <div key={group.label}>
                                    <div className="text-[10px] text-white/20 uppercase font-medium mb-1.5">
                                      {group.label.split("—")[1].trim()}
                                    </div>
                                    <div className="flex flex-wrap gap-1.5">
                                      {group.slots.map((time) => (
                                        <button
                                          key={time}
                                          onClick={() => setSelectedTime(time)}
                                          className={`px-3 py-1 rounded-lg text-xs font-mono border transition-all ${
                                            selectedTime === time
                                              ? "bg-[#E76315]/20 border-[#E76315]/40 text-[#E76315]"
                                              : "bg-white/5 border-white/10 text-white/40 hover:text-white/70 hover:border-white/20"
                                          }`}
                                        >
                                          {time}
                                        </button>
                                      ))}
                                    </div>
                                  </div>
                                ))}

                                {/* Confirm button */}
                                {selectedTime && (
                                  <button
                                    onClick={() => {
                                      const iso = slotToISO(selectedDay, selectedTime);
                                      scheduleMeeting.mutate(
                                        { matchId: match.id, meeting_time: iso },
                                        { onSuccess: () => setSchedulingMatchId(null) },
                                      );
                                    }}
                                    disabled={scheduleMeeting.isPending}
                                    className="w-full flex items-center justify-center gap-2 py-2 bg-[#E76315]/10 text-[#E76315] border border-[#E76315]/30 rounded-lg text-sm font-medium hover:bg-[#E76315]/20 transition-all disabled:opacity-50"
                                  >
                                    <Calendar className="w-4 h-4" />
                                    {scheduleMeeting.isPending
                                      ? "Saving…"
                                      : `Confirm ${selectedDay}, ${selectedTime}`}
                                  </button>
                                )}
                              </div>
                            )}
                          </div>
                        )}

                        {/* Meeting outcome + satisfaction */}
                        {match.status === "met" || match.meeting_outcome ? (
                          <div className="p-3 rounded-xl bg-blue-400/5 border border-blue-400/20">
                            <div className="text-xs text-blue-300 font-medium">
                              Meeting completed{match.meeting_outcome ? `: ${match.meeting_outcome}` : ""}
                            </div>
                            <div className="mt-2 flex items-center gap-2">
                              <span className="text-[11px] text-white/40">Rate this match</span>
                              {[1, 2, 3, 4, 5].map((v) => (
                                <button
                                  key={v}
                                  onClick={() =>
                                    feedback.mutate({ matchId: match.id, satisfaction_score: v })
                                  }
                                  className={`w-7 h-7 rounded-md border text-xs ${
                                    (match.satisfaction_score ?? 0) >= v
                                      ? "bg-[#E76315]/20 border-[#E76315]/40 text-[#E76315]"
                                      : "bg-white/5 border-white/10 text-white/50"
                                  }`}
                                >
                                  {v}
                                </button>
                              ))}
                            </div>
                          </div>
                        ) : (
                          match.meeting_time && (
                            <button
                              onClick={() => handleMarkMet(match.id)}
                              className="w-full flex items-center justify-center gap-2 py-2 bg-blue-400/10 text-blue-300 border border-blue-400/30 rounded-lg text-sm font-medium hover:bg-blue-400/20 transition-all"
                            >
                              <Check className="w-4 h-4" />
                              Mark meeting as done
                            </button>
                          )
                        )}

                        {/* AI-suggested icebreaker */}
                        {icebreaker && (
                          <div className="p-3 rounded-xl bg-white/[0.02] border border-white/10">
                            <div className="flex items-center justify-between mb-2">
                              <span className="text-[10px] text-white/30 uppercase font-medium flex items-center gap-1">
                                <Sparkles className="w-3 h-3" /> Suggested opener
                              </span>
                              <button
                                onClick={() => handleCopyIcebreaker(icebreaker, match.id)}
                                className="flex items-center gap-1 text-[10px] text-white/30 hover:text-[#E76315] transition-colors"
                              >
                                {copiedId === match.id ? (
                                  <><CheckCheck className="w-3 h-3 text-emerald-400" /> <span className="text-emerald-400">Copied</span></>
                                ) : (
                                  <><Copy className="w-3 h-3" /> Copy</>
                                )}
                              </button>
                            </div>
                            <p className="text-xs text-white/50 italic leading-relaxed">
                              "{icebreaker}"
                            </p>
                          </div>
                        )}
                      </div>
                    );
                  }

                  if (iAccepted && !isMutual) {
                    return (
                      <div className="space-y-2 pt-2">
                        <div className="flex items-center gap-2">
                          <div className="flex items-center gap-2 text-sm text-[#E76315]/70">
                            <Check className="w-4 h-4" />
                            You accepted — waiting for {person?.name.split(" ")[0] ?? "them"} to respond
                          </div>
                          {decliningMatchId !== match.id && (
                            <button
                              onClick={() => handleDecline(match.id)}
                              className="ml-auto flex items-center gap-1.5 px-3 py-1.5 bg-white/5 text-white/30 border border-white/10 rounded-lg text-xs hover:text-white/50 transition-all"
                            >
                              <X className="w-3 h-3" />
                              Cancel
                            </button>
                          )}
                        </div>
                        {decliningMatchId === match.id && (
                          <div className="p-3 rounded-xl bg-white/[0.03] border border-white/10 space-y-2">
                            <p className="text-xs text-white/40">Optional: why are you withdrawing?</p>
                            <textarea
                              value={declineReason}
                              onChange={(e) => setDeclineReason(e.target.value)}
                              rows={2}
                              placeholder="Changed my mind, not the right fit…"
                              className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-xs text-white placeholder-white/20 focus:outline-none focus:border-white/20 resize-none"
                            />
                            <div className="flex gap-2">
                              <button
                                onClick={() => confirmDecline(match.id)}
                                className="flex items-center gap-1.5 px-3 py-1.5 bg-red-500/10 text-red-400 border border-red-500/20 rounded-lg text-xs font-medium hover:bg-red-500/20 transition-all"
                              >
                                <X className="w-3 h-3" /> Confirm
                              </button>
                              <button
                                onClick={() => setDecliningMatchId(null)}
                                className="px-3 py-1.5 text-white/30 border border-white/10 rounded-lg text-xs hover:text-white/50 transition-all"
                              >
                                Keep
                              </button>
                            </div>
                          </div>
                        )}
                      </div>
                    );
                  }

                  // Pending — neither party has responded (or other accepted but I haven't)
                  const otherAccepted = otherStatus === "accepted";
                  return (
                    <div className="space-y-2 pt-2">
                      {otherAccepted && (
                        <div className="text-xs text-[#E76315] flex items-center gap-1.5 mb-1">
                          <Sparkles className="w-3 h-3" />
                          {person?.name.split(" ")[0] ?? "They"} already accepted — accept to confirm your meeting!
                        </div>
                      )}
                      {decliningMatchId === match.id ? (
                        <div className="p-3 rounded-xl bg-white/[0.03] border border-white/10 space-y-2">
                          <p className="text-xs text-white/40">Optional: why are you declining?</p>
                          <textarea
                            value={declineReason}
                            onChange={(e) => setDeclineReason(e.target.value)}
                            rows={2}
                            placeholder="Not the right fit, wrong timing…"
                            className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-xs text-white placeholder-white/20 focus:outline-none focus:border-white/20 resize-none"
                          />
                          <div className="flex gap-2">
                            <button
                              onClick={() => confirmDecline(match.id)}
                              className="flex items-center gap-1.5 px-3 py-1.5 bg-red-500/10 text-red-400 border border-red-500/20 rounded-lg text-xs font-medium hover:bg-red-500/20 transition-all"
                            >
                              <X className="w-3 h-3" /> Confirm decline
                            </button>
                            <button
                              onClick={() => setDecliningMatchId(null)}
                              className="px-3 py-1.5 text-white/30 border border-white/10 rounded-lg text-xs hover:text-white/50 transition-all"
                            >
                              Cancel
                            </button>
                          </div>
                        </div>
                      ) : (
                        <div className="space-y-2">
                          <button
                            onClick={() => handleStatus(match.id, "accepted")}
                            className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-emerald-500 text-white rounded-xl text-sm font-semibold hover:bg-emerald-400 transition-all shadow-lg shadow-emerald-500/20"
                          >
                            <Check className="w-4 h-4" />
                            {otherAccepted ? "I'd like to meet — confirm" : "I'd like to meet"}
                          </button>
                          <button
                            onClick={() => handleDecline(match.id)}
                            className="w-full text-center text-xs text-white/30 hover:text-white/50 transition-colors py-1"
                          >
                            Maybe later
                          </button>
                        </div>
                      )}
                    </div>
                  );
                })()}
              </div>
            </div>
          );
        })}
      </div>
      </>
      )}
    </div>
  );
}

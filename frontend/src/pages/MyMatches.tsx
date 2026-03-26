import { Navigate, Link, useNavigate } from "react-router-dom";
import {
  Check, X, Brain, Target, MessageSquare, Sparkles,
  Copy, CheckCheck, Calendar, Clock, Download, Heart, ChevronDown, ChevronUp, Send,
  Bookmark, BookmarkCheck, Linkedin, Twitter, Globe, ThumbsUp, ThumbsDown,
} from "lucide-react";
import AttendeeAvatar from "../components/AttendeeAvatar";
import { useAuth } from "../hooks/useAuth";
import { useMatches, useUpdateMatchStatus, useScheduleMeeting, useMeetingFeedback } from "../hooks/useMatches";
import { useSendMatchMessage } from "../hooks/useMessages";
import { useState } from "react";
import {
  CONFERENCE_SLOTS, slotToISO, formatMeetingTime, downloadICS,
  matchTypeConfig, ticketIcons, buildIcebreaker, twitterUrl,
} from "../utils/matchHelpers";

export default function MyMatches() {
  const navigate = useNavigate();
  const { user, isAuthenticated, isLoading: authLoading } = useAuth();
  const attendeeId = user?.attendee_id ?? undefined;

  const { data: matchData, isLoading: loadingMatches } = useMatches(attendeeId);
  const updateStatus = useUpdateMatchStatus(attendeeId);
  const scheduleMeeting = useScheduleMeeting(attendeeId);
  const feedback = useMeetingFeedback(attendeeId);
  const sendIntro = useSendMatchMessage();

  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [schedulingMatchId, setSchedulingMatchId] = useState<string | null>(null);
  const [selectedDay, setSelectedDay] = useState<string>("June 2");
  const [selectedTime, setSelectedTime] = useState<string | null>(null);
  const [expandedIds, setExpandedIds] = useState<Set<string>>(new Set());
  const [decliningMatchId, setDecliningMatchId] = useState<string | null>(null);
  const [declineReason, setDeclineReason] = useState("");
  const [sentIntroIds, setSentIntroIds] = useState<Set<string>>(new Set());
  const [savedMatchIds, setSavedMatchIds] = useState<Set<string>>(() => {
    try {
      const stored = localStorage.getItem("pot_saved_matches");
      return stored ? new Set(JSON.parse(stored)) : new Set();
    } catch {
      return new Set();
    }
  });
  const [activeTab, setActiveTab] = useState<"all" | "saved">("all");

  const matches = matchData?.matches ?? [];
  const isAdmin = user?.is_admin ?? false;

  // Wait for auth to resolve before redirecting
  if (authLoading) {
    return <div className="text-center py-20 text-white/30">Loading…</div>;
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  const handleStatus = (
    matchId: string,
    status: "accepted" | "declined" | "met",
    decline_reason?: string,
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
    feedback.mutate({ matchId, meeting_outcome: "met", met_at: new Date().toISOString() });
  };

  const handleCopyIcebreaker = (text: string, matchId: string) => {
    navigator.clipboard.writeText(text).then(() => {
      setCopiedId(matchId);
      setTimeout(() => setCopiedId(null), 2000);
    });
  };

  const toggleSaved = (matchId: string) => {
    setSavedMatchIds((prev) => {
      const next = new Set(prev);
      next.has(matchId) ? next.delete(matchId) : next.add(matchId);
      localStorage.setItem("pot_saved_matches", JSON.stringify([...next]));
      return next;
    });
  };

  const toggleExpanded = (matchId: string) => {
    setExpandedIds((prev) => {
      const next = new Set(prev);
      next.has(matchId) ? next.delete(matchId) : next.add(matchId);
      return next;
    });
  };

  const myStatusFor = (match: { attendee_a_id: string; attendee_b_id: string; status_a: string; status_b: string }) => {
    if (!attendeeId) return null;
    if (match.attendee_a_id === attendeeId) return match.status_a;
    if (match.attendee_b_id === attendeeId) return match.status_b;
    return null;
  };

  const otherStatusFor = (match: { attendee_a_id: string; attendee_b_id: string; status_a: string; status_b: string }) => {
    if (!attendeeId) return null;
    if (match.attendee_a_id === attendeeId) return match.status_b;
    if (match.attendee_b_id === attendeeId) return match.status_a;
    return null;
  };

  // No attendee profile linked yet
  if (!attendeeId) {
    return (
      <div className="flex flex-col items-center justify-center py-24 gap-5 text-center">
        <div className="w-16 h-16 rounded-2xl bg-white/5 flex items-center justify-center">
          <Heart className="w-8 h-8 text-white/20" />
        </div>
        <div>
          <h2 className="text-xl font-semibold text-white/60">No matches yet</h2>
          <p className="text-sm text-white/30 mt-1 max-w-sm">
            Complete your attendee profile so the AI can find your best connections at POT 2026.
          </p>
        </div>
      </div>
    );
  }

  if (loadingMatches) {
    return <div className="text-center py-20 text-white/30">Loading your matches…</div>;
  }

  return (
    <div className="space-y-8">
      {/* Page header */}
      <div>
        <div className="pot-badge-orange mb-4">Private Matchmaking Briefing</div>
        <h1 className="text-3xl font-normal text-white" style={{ fontFamily: "var(--font-heading)" }}>
          Your Top Introductions for Proof of Talk Paris
        </h1>
        <p className="text-white/40 mt-2">
          The conversations most likely to matter · Louvre Palace, June 2–3
        </p>
      </div>

      {matches.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-20 gap-4 text-center">
          <Sparkles className="w-10 h-10 text-white/10" />
          <p className="text-white/30 text-sm">No matches generated yet. Check back after the matching pipeline runs.</p>
        </div>
      ) : (
        <>
          <div className="flex items-center justify-between flex-wrap gap-3">
            <div className="flex items-center gap-2 text-sm text-white/40">
              <Sparkles className="w-4 h-4 text-[#E76315]" />
              We found {matches.length} people you should meet at the Louvre
            </div>
            {savedMatchIds.size > 0 && (
              <div className="flex items-center gap-1 p-1 bg-white/5 rounded-lg">
                <button
                  onClick={() => setActiveTab("all")}
                  className={`px-3 py-1 rounded-md text-xs font-medium transition-all ${
                    activeTab === "all" ? "bg-white/10 text-white" : "text-white/40 hover:text-white/60"
                  }`}
                >
                  All ({matches.length})
                </button>
                <button
                  onClick={() => setActiveTab("saved")}
                  className={`flex items-center gap-1 px-3 py-1 rounded-md text-xs font-medium transition-all ${
                    activeTab === "saved" ? "bg-white/10 text-white" : "text-white/40 hover:text-white/60"
                  }`}
                >
                  <BookmarkCheck className="w-3 h-3" />
                  Saved ({savedMatchIds.size})
                </button>
              </div>
            )}
          </div>

          {/* ── Your Schedule ──────────────────────────────────── */}
          {(() => {
            const scheduled = matches.filter((m) => m.meeting_time);
            if (!scheduled.length) return null;
            return (
              <div className="rounded-2xl border border-emerald-400/20 bg-emerald-400/[0.03] overflow-hidden">
                <div className="px-5 py-3 border-b border-emerald-400/10 flex items-center gap-2">
                  <Calendar className="w-4 h-4 text-emerald-400" />
                  <span className="text-sm font-semibold text-emerald-400">Your Schedule</span>
                  <span className="text-xs text-white/30 ml-auto">{scheduled.length} meeting{scheduled.length !== 1 ? "s" : ""} booked</span>
                </div>
                <div className="divide-y divide-white/5">
                  {scheduled
                    .sort((a, b) => new Date(a.meeting_time!).getTime() - new Date(b.meeting_time!).getTime())
                    .map((m) => {
                      const person = m.matched_attendee;
                      return (
                        <div key={m.id} className="px-5 py-3 flex items-center gap-4 flex-wrap">
                          <div className="flex items-center gap-2 min-w-0">
                            <div className="w-8 h-8 rounded-lg bg-white/5 flex items-center justify-center text-white/50 font-semibold text-sm shrink-0">
                              {person?.name[0]}
                            </div>
                            <div className="min-w-0">
                              <div className="text-sm font-medium truncate">{person?.name}</div>
                              <div className="text-xs text-white/30 truncate">{person?.title} · {person?.company}</div>
                            </div>
                          </div>
                          <div className="ml-auto flex items-center gap-3 shrink-0">
                            <div className="text-right">
                              <div className="text-sm text-emerald-400 font-medium">{formatMeetingTime(m.meeting_time!)}</div>
                              {m.meeting_location && (
                                <div className="text-xs text-white/30">{m.meeting_location}</div>
                              )}
                            </div>
                            <Link
                              to={`/messages?match=${m.id}`}
                              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-[#E76315]/10 text-[#E76315] border border-[#E76315]/20 text-xs font-medium hover:bg-[#E76315]/20 transition-all"
                            >
                              <MessageSquare className="w-3 h-3" />
                              Chat
                            </Link>
                          </div>
                        </div>
                      );
                    })}
                </div>
              </div>
            );
          })()}

          <div className="space-y-4">
            {(activeTab === "saved" ? matches.filter((m) => savedMatchIds.has(m.id)) : matches).map((match, idx) => {
              const config = matchTypeConfig[match.match_type] ?? matchTypeConfig.complementary;
              const Icon = config.icon;
              const person = match.matched_attendee;
              const isExpanded = expandedIds.has(match.id);
              const longExplanation = match.explanation.length > 200;

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
                  {/* Card header */}
                  <div className="px-5 py-3 bg-white/[0.02] border-b border-white/5 flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <span className="text-lg font-bold text-white/20">#{idx + 1}</span>
                      <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium border ${config.bg}`}>
                        <Icon className="w-3 h-3" />
                        {config.label}
                      </span>
                      <span className="text-xs text-white/30 hidden sm:block">{config.description}</span>
                    </div>
                    <div className="flex items-center gap-3">
                      <button
                        onClick={() => toggleSaved(match.id)}
                        className={`p-1.5 rounded-lg transition-all ${
                          savedMatchIds.has(match.id)
                            ? "text-[#E76315] bg-[#E76315]/10"
                            : "text-white/20 hover:text-white/50"
                        }`}
                        title={savedMatchIds.has(match.id) ? "Remove from saved" : "Save for later"}
                      >
                        {savedMatchIds.has(match.id)
                          ? <BookmarkCheck className="w-4 h-4" />
                          : <Bookmark className="w-4 h-4" />
                        }
                      </button>
                      <div className="text-right">
                        <div className="text-xs text-white/30">Compatibility</div>
                        <div className="text-lg font-bold text-[#E76315]">
                          {match.overall_score >= 0.85 ? "Strong match" : match.overall_score >= 0.7 ? "Good match" : "Potential match"}
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Card body */}
                  <div className="p-5 space-y-4">
                    {/* Matched person */}
                    {person && (
                      <div className="flex items-center gap-3">
                        <AttendeeAvatar attendee={person} size="md" />
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

                    {/* AI Explanation — collapsible if long */}
                    <div className="p-4 rounded-xl bg-[#E76315]/5 border border-[#E76315]/10">
                      <div className="flex items-center gap-2 text-xs text-[#E76315] font-medium mb-2">
                        <Brain className="w-3.5 h-3.5" />
                        Why this meeting matters
                      </div>
                      <p className="text-sm text-white/70 leading-relaxed">
                        {longExplanation && !isExpanded
                          ? `${match.explanation.slice(0, 200)}…`
                          : match.explanation}
                      </p>
                      {longExplanation && (
                        <button
                          onClick={() => toggleExpanded(match.id)}
                          className="mt-2 flex items-center gap-1 text-xs text-[#E76315]/60 hover:text-[#E76315] transition-colors"
                        >
                          {isExpanded ? (
                            <><ChevronUp className="w-3 h-3" /> Show less</>
                          ) : (
                            <><ChevronDown className="w-3 h-3" /> Show more</>
                          )}
                        </button>
                      )}
                    </div>

                    {/* Shared context */}
                    {match.shared_context && (
                      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
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

                    {/* Quick feedback */}
                    {match.status === "pending" && !isAdmin && (
                      <div className="flex items-center gap-2 pt-1">
                        <button
                          onClick={() => {
                            updateStatus.mutate({ matchId: match.id, status: "accepted", decline_reason: "FEEDBACK:more_like_this" });
                          }}
                          className="text-[10px] text-white/30 hover:text-emerald-400 transition-colors flex items-center gap-1"
                        >
                          <ThumbsUp className="w-3 h-3" /> More like this
                        </button>
                        <span className="text-white/10">|</span>
                        <button
                          onClick={() => {
                            updateStatus.mutate({ matchId: match.id, status: "declined", decline_reason: "FEEDBACK:not_relevant" });
                          }}
                          className="text-[10px] text-white/30 hover:text-red-400 transition-colors flex items-center gap-1"
                        >
                          <ThumbsDown className="w-3 h-3" /> Not relevant
                        </button>
                      </div>
                    )}

                    {/* Inline decline panel */}
                    {decliningMatchId === match.id && (
                      <div className="p-4 rounded-xl bg-red-500/5 border border-red-500/20 space-y-3">
                        <p className="text-sm text-white/60">Let us know why — it helps improve future matches (optional)</p>
                        <textarea
                          value={declineReason}
                          onChange={(e) => setDeclineReason(e.target.value)}
                          placeholder="Not the right fit right now…"
                          rows={2}
                          className="w-full px-3 py-2 bg-white/5 border border-white/10 rounded-lg text-sm text-white placeholder:text-white/20 focus:outline-none focus:border-red-400/40 resize-none"
                        />
                        <div className="flex gap-2">
                          <button
                            onClick={() => confirmDecline(match.id)}
                            className="flex items-center gap-1.5 px-4 py-2 bg-red-500/10 text-red-400 border border-red-500/20 rounded-lg text-sm font-medium hover:bg-red-500/20 transition-all"
                          >
                            <X className="w-3.5 h-3.5" /> Maybe later
                          </button>
                          <button
                            onClick={() => setDecliningMatchId(null)}
                            className="px-4 py-2 text-white/40 text-sm hover:text-white/60 transition-all"
                          >
                            Cancel
                          </button>
                        </div>
                      </div>
                    )}

                    {/* Actions — hidden for admin (read-only preview mode) */}
                    {isAdmin ? (
                      <div className="flex items-center gap-2 pt-2 text-xs text-white/30 border-t border-white/5 mt-2">
                        <Sparkles className="w-3 h-3 text-[#E76315]" />
                        Admin view — attendees manage their own appointments
                      </div>
                    ) : (() => {
                      const myStatus = myStatusFor(match);
                      const otherStatus = otherStatusFor(match);
                      const isMutual = match.status === "accepted";
                      const iDeclined = myStatus === "declined";
                      const iAccepted = myStatus === "accepted";

                      if (iDeclined || match.status === "declined") {
                        return (
                          <div className="flex items-center gap-2 text-sm text-white/30 pt-2">
                            <X className="w-4 h-4" /> Declined
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
                            <div className="flex items-center gap-3 flex-wrap">
                              <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-emerald-400/10 border border-emerald-400/20 text-sm text-emerald-400 font-medium">
                                <Check className="w-4 h-4" />
                                Mutual match — both accepted!
                              </div>
                              </div>

                            {match.meeting_time ? (
                              <div className="p-3 rounded-xl bg-emerald-400/5 border border-emerald-400/20 flex items-center justify-between gap-3 flex-wrap">
                                <div className="flex items-center gap-2 text-sm">
                                  <Calendar className="w-4 h-4 text-emerald-400 shrink-0" />
                                  <div>
                                    <div className="text-emerald-400 font-medium">
                                      {formatMeetingTime(match.meeting_time)}
                                    </div>
                                    <div className="text-xs text-white/40 mt-0.5">{match.meeting_location}</div>
                                  </div>
                                </div>
                                <button
                                  onClick={() =>
                                    person &&
                                    downloadICS(
                                      match.meeting_time!,
                                      user?.full_name ?? "",
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
                              <div className="rounded-xl border border-white/10 overflow-hidden">
                                <button
                                  onClick={() => {
                                    setSchedulingMatchId(isScheduling ? null : match.id);
                                    setSelectedTime(null);
                                  }}
                                  className="w-full flex items-center gap-2 px-4 py-2.5 bg-white/[0.02] text-sm text-white/50 hover:text-[#E76315] hover:bg-[#E76315]/5 transition-all text-left"
                                >
                                  <Clock className="w-4 h-4" />
                                  {isScheduling ? "Cancel" : "Save a preferred time for Paris"}
                                </button>

                                {isScheduling && (
                                  <div className="p-4 space-y-3 bg-white/[0.02]">
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
                                              className={`px-3 py-2 rounded-lg text-xs font-mono border transition-all min-h-[44px] flex items-center justify-center ${
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
                                        {scheduleMeeting.isPending ? "Saving…" : `Save ${selectedDay}, ${selectedTime}`}
                                      </button>
                                    )}
                                  </div>
                                )}
                              </div>
                            )}

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
                                      onClick={() => feedback.mutate({ matchId: match.id, satisfaction_score: v })}
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
                                <p className="text-xs text-white/50 italic leading-relaxed mb-3">"{icebreaker}"</p>
                                <button
                                  onClick={() => {
                                    sendIntro.mutate(
                                      { matchId: match.id, content: icebreaker },
                                      { onSuccess: () => navigate(`/messages?match=${match.id}`) },
                                    );
                                  }}
                                  disabled={sendIntro.isPending}
                                  className="flex items-center gap-1.5 px-3 py-1.5 bg-[#E76315]/10 text-[#E76315] border border-[#E76315]/20 rounded-lg text-xs font-medium hover:bg-[#E76315]/20 transition-all disabled:opacity-50"
                                >
                                  <Send className="w-3 h-3" />
                                  {sendIntro.isPending ? "Sending…" : "Send & open chat"}
                                </button>
                              </div>
                            )}
                          </div>
                        );
                      }

                      if (iAccepted && !isMutual) {
                        const icebreaker = person
                          ? buildIcebreaker(
                              person.name,
                              person.title,
                              person.company,
                              match.shared_context?.action_items,
                            )
                          : "";
                        const introSent = sentIntroIds.has(match.id);

                        return (
                          <div className="space-y-3 pt-2">
                            <div className="flex items-center gap-2">
                              <div className="flex items-center gap-2 text-sm text-[#E76315]/70">
                                <Check className="w-4 h-4" />
                                You accepted — waiting for {person?.name.split(" ")[0] ?? "them"} to respond
                              </div>
                              <button
                                onClick={() => handleDecline(match.id)}
                                className="ml-auto flex items-center gap-1.5 px-3 py-1.5 bg-white/5 text-white/30 border border-white/10 rounded-lg text-xs hover:text-white/50 transition-all"
                              >
                                <X className="w-3 h-3" /> Cancel
                              </button>
                            </div>

                            {icebreaker && (
                              <div className="p-3 rounded-xl bg-white/[0.02] border border-white/10">
                                <div className="flex items-center gap-1.5 mb-2">
                                  <Sparkles className="w-3 h-3 text-[#E76315]" />
                                  <span className="text-[10px] text-white/30 uppercase font-medium">Send an introduction</span>
                                </div>
                                <p className="text-xs text-white/50 italic leading-relaxed mb-3">"{icebreaker}"</p>
                                {introSent ? (
                                  <div className="flex items-center justify-between">
                                    <div className="flex items-center gap-1.5 text-xs text-emerald-400">
                                      <CheckCheck className="w-3.5 h-3.5" />
                                      Introduction sent — they'll see it when they accept
                                    </div>
                                    <Link
                                      to={`/messages?match=${match.id}`}
                                      className="flex items-center gap-1 text-[10px] text-[#E76315]/60 hover:text-[#E76315] transition-colors"
                                    >
                                      <MessageSquare className="w-3 h-3" /> View
                                    </Link>
                                  </div>
                                ) : (
                                  <button
                                    onClick={() => {
                                      sendIntro.mutate(
                                        { matchId: match.id, content: icebreaker },
                                        {
                                          onSuccess: () =>
                                            setSentIntroIds((prev) => new Set([...prev, match.id])),
                                        },
                                      );
                                    }}
                                    disabled={sendIntro.isPending}
                                    className="flex items-center gap-1.5 px-3 py-1.5 bg-[#E76315]/10 text-[#E76315] border border-[#E76315]/20 rounded-lg text-xs font-medium hover:bg-[#E76315]/20 transition-all disabled:opacity-50"
                                  >
                                    <Send className="w-3 h-3" />
                                    {sendIntro.isPending ? "Sending…" : "Send introduction"}
                                  </button>
                                )}
                              </div>
                            )}
                          </div>
                        );
                      }

                      // Pending
                      const otherAccepted = otherStatus === "accepted";
                      return (
                        <div className="space-y-2 pt-2">
                          {otherAccepted && (
                            <div className="text-xs text-[#E76315] flex items-center gap-1.5 mb-1">
                              <Sparkles className="w-3 h-3" />
                              {person?.name.split(" ")[0] ?? "They"} already accepted — accept to confirm your meeting!
                            </div>
                          )}
                          <div className="space-y-2">
                            <button
                              onClick={() => handleStatus(match.id, "accepted")}
                              disabled={updateStatus.isPending}
                              className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-emerald-500 text-white rounded-xl text-sm font-semibold hover:bg-emerald-400 transition-all shadow-lg shadow-emerald-500/20 disabled:opacity-50"
                            >
                              {updateStatus.isPending ? (
                                <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                              ) : (
                                <Check className="w-4 h-4" />
                              )}
                              {otherAccepted ? "I'd like to meet — confirm" : "I'd like to meet"}
                            </button>
                            <button
                              onClick={() => handleDecline(match.id)}
                              disabled={updateStatus.isPending}
                              className="w-full text-center text-xs text-white/30 hover:text-white/50 transition-colors py-1 disabled:opacity-50"
                            >
                              Maybe later
                            </button>
                          </div>
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

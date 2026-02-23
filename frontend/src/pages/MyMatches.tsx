import { Navigate, useNavigate } from "react-router-dom";
import {
  Check, X, Brain, Target, MessageSquare, Sparkles,
  Copy, CheckCheck, Calendar, Clock, Download, Heart, ChevronDown, ChevronUp,
} from "lucide-react";
import { useAuth } from "../hooks/useAuth";
import { useMatches, useUpdateMatchStatus, useScheduleMeeting, useMeetingFeedback } from "../hooks/useMatches";
import { useState } from "react";
import {
  CONFERENCE_SLOTS, slotToISO, formatMeetingTime, downloadICS,
  matchTypeConfig, ticketIcons, buildIcebreaker,
} from "../utils/matchHelpers";

export default function MyMatches() {
  const { user, isAuthenticated, isLoading: authLoading } = useAuth();
  const navigate = useNavigate();
  const attendeeId = user?.attendee_id ?? undefined;

  const { data: matchData, isLoading: loadingMatches } = useMatches(attendeeId);
  const updateStatus = useUpdateMatchStatus(attendeeId);
  const scheduleMeeting = useScheduleMeeting(attendeeId);
  const feedback = useMeetingFeedback(attendeeId);

  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [schedulingMatchId, setSchedulingMatchId] = useState<string | null>(null);
  const [selectedDay, setSelectedDay] = useState<string>("June 2");
  const [selectedTime, setSelectedTime] = useState<string | null>(null);
  const [expandedIds, setExpandedIds] = useState<Set<string>>(new Set());

  const matches = matchData?.matches ?? [];

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
    const reason = window.prompt("Optional: why are you declining this match?");
    handleStatus(matchId, "declined", reason?.trim() || undefined);
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
        <div className="flex items-center gap-3">
          <Heart className="w-6 h-6 text-amber-400" />
          <h1 className="text-3xl font-bold">My Matches</h1>
        </div>
        <p className="text-white/40 mt-1">
          AI-curated connections for you at Proof of Talk 2026 · Louvre Palace, Paris
        </p>
      </div>

      {matches.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-20 gap-4 text-center">
          <Sparkles className="w-10 h-10 text-white/10" />
          <p className="text-white/30 text-sm">No matches generated yet. Check back after the matching pipeline runs.</p>
        </div>
      ) : (
        <>
          <div className="flex items-center gap-2 text-sm text-white/40">
            <Sparkles className="w-4 h-4 text-amber-400" />
            {matches.length} AI-recommended connections
          </div>

          <div className="space-y-4">
            {matches.map((match, idx) => {
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
                    <div className="text-right">
                      <div className="text-xs text-white/30">Match Score</div>
                      <div className="text-lg font-bold text-amber-400">
                        {(match.overall_score * 100).toFixed(0)}%
                      </div>
                    </div>
                  </div>

                  {/* Card body */}
                  <div className="p-5 space-y-4">
                    {/* Matched person */}
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

                    {/* AI Explanation — collapsible if long */}
                    <div className="p-4 rounded-xl bg-amber-400/5 border border-amber-400/10">
                      <div className="flex items-center gap-2 text-xs text-amber-400 font-medium mb-2">
                        <Brain className="w-3.5 h-3.5" />
                        WHY YOU SHOULD MEET
                      </div>
                      <p className="text-sm text-white/70 leading-relaxed">
                        {longExplanation && !isExpanded
                          ? `${match.explanation.slice(0, 200)}…`
                          : match.explanation}
                      </p>
                      {longExplanation && (
                        <button
                          onClick={() => toggleExpanded(match.id)}
                          className="mt-2 flex items-center gap-1 text-xs text-amber-400/60 hover:text-amber-400 transition-colors"
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
                    {(() => {
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
                              <button
                                onClick={() => navigate(`/messages?match=${match.id}`)}
                                className="flex items-center gap-2 px-3 py-1.5 bg-amber-400/10 text-amber-400 border border-amber-400/20 rounded-lg text-sm font-medium hover:bg-amber-400/20 transition-all"
                              >
                                <MessageSquare className="w-3.5 h-3.5" />
                                Send Message
                              </button>
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
                                  className="flex items-center gap-1.5 px-3 py-1.5 bg-white/5 text-white/50 border border-white/10 rounded-lg text-xs hover:text-amber-400 hover:border-amber-400/30 transition-all"
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
                                  className="w-full flex items-center gap-2 px-4 py-2.5 bg-white/[0.02] text-sm text-white/50 hover:text-amber-400 hover:bg-amber-400/5 transition-all text-left"
                                >
                                  <Clock className="w-4 h-4" />
                                  {isScheduling ? "Cancel scheduling" : "Schedule a meeting at POT 2026"}
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
                                              ? "bg-amber-400/10 border-amber-400/30 text-amber-400"
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
                                              className={`px-3 py-1 rounded-lg text-xs font-mono border transition-all ${
                                                selectedTime === time
                                                  ? "bg-amber-400/20 border-amber-400/40 text-amber-400"
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
                                        className="w-full flex items-center justify-center gap-2 py-2 bg-amber-400/10 text-amber-400 border border-amber-400/30 rounded-lg text-sm font-medium hover:bg-amber-400/20 transition-all disabled:opacity-50"
                                      >
                                        <Calendar className="w-4 h-4" />
                                        {scheduleMeeting.isPending ? "Saving…" : `Confirm ${selectedDay}, ${selectedTime}`}
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
                                          ? "bg-amber-400/20 border-amber-400/40 text-amber-400"
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
                                    className="flex items-center gap-1 text-[10px] text-white/30 hover:text-amber-400 transition-colors"
                                  >
                                    {copiedId === match.id ? (
                                      <><CheckCheck className="w-3 h-3 text-emerald-400" /> <span className="text-emerald-400">Copied</span></>
                                    ) : (
                                      <><Copy className="w-3 h-3" /> Copy</>
                                    )}
                                  </button>
                                </div>
                                <p className="text-xs text-white/50 italic leading-relaxed">"{icebreaker}"</p>
                              </div>
                            )}
                          </div>
                        );
                      }

                      if (iAccepted && !isMutual) {
                        return (
                          <div className="flex items-center gap-2 pt-2">
                            <div className="flex items-center gap-2 text-sm text-amber-400/70">
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
                        );
                      }

                      // Pending
                      const otherAccepted = otherStatus === "accepted";
                      return (
                        <div className="space-y-2 pt-2">
                          {otherAccepted && (
                            <div className="text-xs text-amber-400 flex items-center gap-1.5 mb-1">
                              <Sparkles className="w-3 h-3" />
                              {person?.name.split(" ")[0] ?? "They"} already accepted — accept to confirm your meeting!
                            </div>
                          )}
                          <div className="flex items-center gap-2">
                            <button
                              onClick={() => handleStatus(match.id, "accepted")}
                              className="flex items-center gap-2 px-4 py-2 bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 rounded-lg text-sm font-medium hover:bg-emerald-500/20 transition-all"
                            >
                              <Check className="w-4 h-4" />
                              {otherAccepted ? "Accept & Confirm Meeting" : "Accept Meeting"}
                            </button>
                            <button
                              onClick={() => handleDecline(match.id)}
                              className="flex items-center gap-2 px-4 py-2 bg-white/5 text-white/40 border border-white/10 rounded-lg text-sm font-medium hover:text-white/60 transition-all"
                            >
                              <X className="w-4 h-4" /> Not Now
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

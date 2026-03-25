import { useState } from "react";
import { useParams, Link } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Sparkles, Brain, Target, MessageSquare,
  Linkedin, Twitter, Globe, UserPlus, Send, CheckCheck,
} from "lucide-react";
import { getMatchesByMagicLink, getAttendee, updateProfileViaMagicLink } from "../api/client";
import { matchTypeConfig } from "../utils/matchHelpers";
import AttendeeAvatar from "../components/AttendeeAvatar";

export default function MagicMatches() {
  const { token } = useParams<{ token: string }>();
  const queryClient = useQueryClient();
  const [enrichForm, setEnrichForm] = useState({ twitter_handle: "", target_companies: "" });
  const [enrichSaved, setEnrichSaved] = useState(false);

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

  const enrichMutation = useMutation({
    mutationFn: () => updateProfileViaMagicLink(token!, {
      twitter_handle: enrichForm.twitter_handle || undefined,
      target_companies: enrichForm.target_companies || undefined,
    }),
    onSuccess: () => {
      setEnrichSaved(true);
      queryClient.invalidateQueries({ queryKey: ["attendee", attendeeId] });
      setTimeout(() => setEnrichSaved(false), 3000);
    },
  });

  const showEnrichCard = attendee && (
    !attendee.twitter_handle && !attendee.target_companies
  );

  const matches = data?.matches ?? [];

  if (isLoading) {
    return (
      <div className="text-center py-20">
        <div className="inline-block w-8 h-8 border-2 border-[#E76315] border-t-transparent rounded-full animate-spin" />
        <p className="text-white/30 mt-4 text-sm">Loading your matches…</p>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="text-center py-20 space-y-4">
        <Sparkles className="w-8 h-8 text-white/20 mx-auto" />
        <p className="text-white/40">This link is invalid or has expired.</p>
        <Link to="/login" className="text-[#E76315] text-sm hover:underline">
          Log in instead →
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-8 max-w-3xl mx-auto">
      {/* Header */}
      <div className="text-center space-y-2">
        <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-[#E76315]/10 border border-[#E76315]/20">
          <Sparkles className="w-4 h-4 text-[#E76315]" />
          <span className="text-sm font-medium text-[#E76315]">Your AI Matches</span>
        </div>
        {attendee && (
          <div>
            <h1 className="text-2xl font-bold mt-3">Welcome, {attendee.name.split(" ")[0]}</h1>
            <p className="text-white/40 text-sm mt-1">
              {attendee.title} · {attendee.company}
            </p>
          </div>
        )}
        <p className="text-white/30 text-sm">
          Here are your personalised meeting recommendations for Proof of Talk 2026
        </p>
      </div>

      {/* Profile enrichment card */}
      {showEnrichCard && !enrichSaved && (
        <div className="p-5 rounded-2xl border border-[#E76315]/20 bg-[#E76315]/[0.04]">
          <div className="flex items-center gap-2 mb-3">
            <UserPlus className="w-5 h-5 text-[#E76315]" />
            <h3 className="font-semibold">Help us find better matches for you</h3>
          </div>
          <p className="text-xs text-white/40 mb-4">
            The more we know, the better your introductions. This takes 30 seconds.
          </p>
          <div className="space-y-3">
            <div>
              <label className="text-xs text-white/50 block mb-1">Your Twitter / X handle</label>
              <input
                type="text"
                placeholder="@yourhandle"
                value={enrichForm.twitter_handle}
                onChange={(e) => setEnrichForm(prev => ({ ...prev, twitter_handle: e.target.value }))}
                className="w-full px-3 py-2 rounded-lg bg-white/5 border border-white/10 text-sm text-white placeholder:text-white/20 outline-none focus:border-[#E76315]/30"
              />
            </div>
            <div>
              <label className="text-xs text-white/50 block mb-1">Who do you want to meet at Proof of Talk?</label>
              <textarea
                placeholder="e.g., Coinbase, a16z crypto, anyone building L2 infrastructure, Kucoin..."
                value={enrichForm.target_companies}
                onChange={(e) => setEnrichForm(prev => ({ ...prev, target_companies: e.target.value }))}
                rows={3}
                className="w-full px-3 py-2 rounded-lg bg-white/5 border border-white/10 text-sm text-white placeholder:text-white/20 outline-none focus:border-[#E76315]/30 resize-none"
              />
              <p className="text-[10px] text-white/30 mt-1">
                Name companies, people, or types of organisations. We'll prioritise these in your matches.
              </p>
            </div>
            <button
              onClick={() => enrichMutation.mutate()}
              disabled={enrichMutation.isPending || (!enrichForm.twitter_handle && !enrichForm.target_companies)}
              className="w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg bg-[#E76315] text-white font-medium text-sm disabled:opacity-30 hover:bg-[#D35400] transition-all"
            >
              <Send className="w-4 h-4" />
              Save & improve my matches
            </button>
          </div>
        </div>
      )}
      {enrichSaved && (
        <div className="p-4 rounded-xl border border-emerald-500/20 bg-emerald-500/[0.04] flex items-center gap-3">
          <CheckCheck className="w-5 h-5 text-emerald-400" />
          <p className="text-sm text-emerald-300">Saved! Your matches will improve on the next refresh.</p>
        </div>
      )}

      {/* Match count */}
      <div className="flex items-center gap-3">
        <Sparkles className="w-5 h-5 text-[#E76315]" />
        <h2 className="text-xl font-bold">Recommended Connections</h2>
        <span className="text-white/30 text-sm">({matches.length})</span>
      </div>

      {/* Match cards */}
      {matches.length === 0 ? (
        <div className="text-center py-12 text-white/30">
          <Brain className="w-8 h-8 mx-auto mb-3 text-white/10" />
          <p>Your matches are being generated. Check back soon.</p>
        </div>
      ) : (
        <div className="space-y-4">
          {matches.map((match, idx) => {
            const config = matchTypeConfig[match.match_type] ?? matchTypeConfig.complementary;
            const Icon = config.icon;
            const person = match.matched_attendee;

            return (
              <div
                key={match.id}
                className={`rounded-2xl border border-l-4 ${config.leftBorder} border-white/10 bg-white/[0.03] overflow-hidden`}
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

                {/* Person info */}
                <div className="p-5 space-y-4">
                  <div className="flex items-start gap-4">
                    {person ? (
                      <AttendeeAvatar attendee={person} size="lg" />
                    ) : (
                      <div className="w-14 h-14 rounded-xl bg-white/5 flex items-center justify-center text-white/20 text-lg font-bold shrink-0">
                        ?
                      </div>
                    )}
                    <div className="flex-1 min-w-0">
                      <h3 className="text-lg font-bold truncate">
                        {person?.name ?? "Matched Attendee"}
                      </h3>
                      <p className="text-white/50 text-sm">
                        {person?.title} · {person?.company}
                      </p>
                      {/* Social links */}
                      <div className="flex items-center gap-3 mt-2">
                        {person?.linkedin_url && (
                          <a href={person.linkedin_url} target="_blank" rel="noopener noreferrer"
                            className="text-white/30 hover:text-blue-400 transition-colors">
                            <Linkedin className="w-4 h-4" />
                          </a>
                        )}
                        {person?.twitter_handle && (
                          <a href={`https://twitter.com/${person.twitter_handle.replace("@", "")}`} target="_blank" rel="noopener noreferrer"
                            className="text-white/30 hover:text-sky-400 transition-colors">
                            <Twitter className="w-4 h-4" />
                          </a>
                        )}
                        {person?.company_website && (
                          <a href={person.company_website} target="_blank" rel="noopener noreferrer"
                            className="text-white/30 hover:text-[#E76315] transition-colors">
                            <Globe className="w-4 h-4" />
                          </a>
                        )}
                      </div>
                    </div>
                  </div>

                  {/* Why this meeting matters */}
                  <div className="p-4 rounded-xl bg-white/[0.02] border border-white/5">
                    <div className="flex items-center gap-2 mb-2">
                      <MessageSquare className="w-4 h-4 text-[#E76315]" />
                      <span className="text-xs font-medium text-[#E76315]">Why this meeting matters</span>
                    </div>
                    <p className="text-sm text-white/60 leading-relaxed">{match.explanation}</p>
                  </div>

                  {/* Shared context tags */}
                  {match.shared_context && Object.keys(match.shared_context).length > 0 && (
                    <div className="flex flex-wrap gap-1.5">
                      {Object.entries(match.shared_context).slice(0, 6).map(([key, val]) => (
                        <span key={key} className="px-2.5 py-1 rounded-full bg-white/5 text-white/30 text-xs">
                          {String(val)}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Footer CTA */}
      <div className="text-center py-8 space-y-3">
        <p className="text-white/30 text-sm">
          Want to accept matches and schedule meetings?
        </p>
        <Link
          to="/login"
          className="inline-flex items-center gap-2 px-6 py-3 rounded-xl bg-[#E76315] text-white font-medium hover:bg-[#D35400] transition-colors"
        >
          <Target className="w-4 h-4" />
          Log in to take action
        </Link>
      </div>
    </div>
  );
}

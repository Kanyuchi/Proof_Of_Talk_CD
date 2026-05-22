import { useState, useEffect, useRef } from "react";
import { useParams, useSearchParams, Link } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Sparkles, Brain, Target, MessageSquare,
  Linkedin, Twitter, Globe, UserPlus, Send, CheckCheck, FileText, KeyRound,
} from "lucide-react";
import { getMatchesByMagicLink, getAttendee, updateProfileViaMagicLink, claimAccount, deferMatchByMagicLink, uploadPhotoViaMagicLink } from "../api/client";
import PhotoUpload from "../components/PhotoUpload";
import { matchTypeConfig, twitterUrl } from "../utils/matchHelpers";
import GridOrgCard from "../components/GridOrgCard";
import AttendeeAvatar from "../components/AttendeeAvatar";

export default function MagicMatches() {
  const { token } = useParams<{ token: string }>();
  const queryClient = useQueryClient();
  const [enrichForm, setEnrichForm] = useState({
    twitter_handle: "",
    target_companies: "",
    linkedin_url: "",
    goals: "",
  });
  const [enrichSaved, setEnrichSaved] = useState(false);
  const [claimForm, setClaimForm] = useState({ email: "", password: "" });
  const [claimError, setClaimError] = useState("");
  // Arriving from the welcome email's "Unlock Full Access" CTA (?unlock=1)
  // pre-opens the claim panel and scrolls to it.
  const [searchParams] = useSearchParams();
  const [claimOpen, setClaimOpen] = useState(searchParams.get("unlock") === "1");
  const claimRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (searchParams.get("unlock") === "1") {
      claimRef.current?.scrollIntoView({ behavior: "smooth", block: "center" });
    }
  }, [searchParams]);

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
      linkedin_url: enrichForm.linkedin_url || undefined,
      goals: enrichForm.goals || undefined,
    }),
    onSuccess: () => {
      setEnrichSaved(true);
      queryClient.invalidateQueries({ queryKey: ["attendee", attendeeId] });
      setTimeout(() => setEnrichSaved(false), 3000);
    },
  });

  const deferMutation = useMutation({
    mutationFn: (matchId: string) => deferMatchByMagicLink(token!, matchId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["magic-matches", token] });
    },
  });

  // Claim a full account from this magic link. The token authenticates the
  // request server-side, so it bypasses the registration ticket gate — this
  // is how placeholder-email speakers get a real login. On success we store
  // the JWT and hard-navigate so AuthProvider picks up the session on mount.
  const claimMutation = useMutation({
    mutationFn: () => claimAccount({
      magic_token: token!,
      password: claimForm.password,
      email: claimForm.email.trim() || undefined,
    }),
    onSuccess: (tok) => {
      localStorage.setItem("token", tok.access_token);
      window.location.href = "/matches";
    },
    onError: (e: unknown) => {
      const detail = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setClaimError(detail || "Couldn't create your account. Please try again.");
    },
  });

  // Show the card whenever ANY of the high-leverage profile fields are
  // empty — LinkedIn URL and goals are now the most common gaps for
  // Extasy buyers who get a placeholder profile.
  const showEnrichCard = attendee && (
    !attendee.twitter_handle ||
    !attendee.target_companies ||
    !attendee.linkedin_url ||
    !attendee.goals
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
        <Link
          to={`/m/${token}/briefing`}
          className="inline-flex items-center gap-2 mt-3 px-4 py-2 bg-[#1a1a2e] border border-white/10 rounded-lg text-sm text-white/60 hover:text-white hover:border-[#E76315]/30 transition-colors"
        >
          <FileText className="w-4 h-4" /> View Meeting Prep Brief
        </Link>
      </div>

      {/* Claim full account — token-authenticated, bypasses the ticket gate */}
      {data?.attendee_id && (
        <div ref={claimRef} className="p-5 rounded-2xl border border-white/10 bg-white/[0.03]">
          <button
            onClick={() => setClaimOpen((v) => !v)}
            className="w-full flex items-center gap-2 text-left"
          >
            <KeyRound className="w-5 h-5 text-[#E76315]" />
            <div className="flex-1">
              <h3 className="font-semibold text-[#E76315]">Unlock full access</h3>
              <p className="text-xs text-white/40">
                Set a password to message your matches and use the AI Concierge.
              </p>
            </div>
            <span className="text-white/30 text-sm">{claimOpen ? "−" : "+"}</span>
          </button>
          {claimOpen && (
            <div className="space-y-3 mt-4">
              <div>
                <label className="text-xs text-white/50 block mb-1">
                  Email <span className="text-white/25">(only if it's not already on your ticket)</span>
                </label>
                <input
                  type="email"
                  placeholder="you@company.com"
                  value={claimForm.email}
                  onChange={(e) => setClaimForm((p) => ({ ...p, email: e.target.value }))}
                  className="w-full px-3 py-2 rounded-lg bg-white/5 border border-white/10 text-sm text-white placeholder:text-white/20 outline-none focus:border-[#E76315]/30"
                />
              </div>
              <div>
                <label className="text-xs text-white/50 block mb-1">Choose a password</label>
                <input
                  type="password"
                  placeholder="••••••••"
                  value={claimForm.password}
                  onChange={(e) => setClaimForm((p) => ({ ...p, password: e.target.value }))}
                  className="w-full px-3 py-2 rounded-lg bg-white/5 border border-white/10 text-sm text-white placeholder:text-white/20 outline-none focus:border-[#E76315]/30"
                />
                <p className="text-[10px] text-white/30 mt-1">
                  At least 8 characters, with an uppercase letter and a number.
                </p>
              </div>
              {claimError && <p className="text-xs text-red-400">{claimError}</p>}
              <button
                onClick={() => { setClaimError(""); claimMutation.mutate(); }}
                disabled={claimMutation.isPending || !claimForm.password}
                className="w-full py-2.5 rounded-lg bg-[#E76315] text-white text-sm font-semibold hover:bg-[#E76315]/90 disabled:opacity-70 disabled:cursor-not-allowed transition-colors"
              >
                {claimMutation.isPending ? "Creating your account…" : "Create my account"}
              </button>
              <p className="text-[10px] text-white/30 text-center">
                Already have a password? <Link to="/login" className="text-[#E76315] hover:underline">Sign in</Link>
              </p>
            </div>
          )}
        </div>
      )}

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
            {!attendee?.photo_url && (
              <div>
                <label className="text-xs text-white/50 block mb-1">Profile photo</label>
                <PhotoUpload
                  uploadFn={(blob) => uploadPhotoViaMagicLink(token!, blob)}
                  onUploaded={() =>
                    queryClient.invalidateQueries({ queryKey: ["attendee", attendeeId] })
                  }
                />
              </div>
            )}
            {!attendee?.linkedin_url && (
              <div>
                <label className="text-xs text-white/50 block mb-1">Your LinkedIn URL</label>
                <input
                  type="text"
                  placeholder="https://www.linkedin.com/in/your-handle"
                  value={enrichForm.linkedin_url}
                  onChange={(e) => setEnrichForm(prev => ({ ...prev, linkedin_url: e.target.value }))}
                  className="w-full px-3 py-2 rounded-lg bg-white/5 border border-white/10 text-sm text-white placeholder:text-white/20 outline-none focus:border-[#E76315]/30"
                />
                <p className="text-[10px] text-white/30 mt-1">
                  Must be a linkedin.com/in/ profile link. Used to enrich your matchmaking profile.
                </p>
              </div>
            )}
            {!attendee?.goals && (
              <div>
                <label className="text-xs text-white/50 block mb-1">What are your goals for Proof of Talk?</label>
                <textarea
                  placeholder="e.g., raising a Series A, finding a Layer-2 partner, exploring tokenisation deals..."
                  value={enrichForm.goals}
                  onChange={(e) => setEnrichForm(prev => ({ ...prev, goals: e.target.value }))}
                  rows={2}
                  className="w-full px-3 py-2 rounded-lg bg-white/5 border border-white/10 text-sm text-white placeholder:text-white/20 outline-none focus:border-[#E76315]/30 resize-none"
                />
              </div>
            )}
            {!attendee?.twitter_handle && (
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
            )}
            {!attendee?.target_companies && (
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
            )}
            <button
              onClick={() => enrichMutation.mutate()}
              disabled={
                enrichMutation.isPending ||
                (!enrichForm.twitter_handle && !enrichForm.target_companies &&
                 !enrichForm.linkedin_url && !enrichForm.goals)
              }
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
                      <div className="flex items-center gap-2">
                        <h3 className="text-lg font-bold truncate">
                          {person?.name ?? "Matched Attendee"}
                        </h3>
                        {person?.privacy_mode === "b2b_only" && (
                          <span className="px-1.5 py-0.5 rounded bg-white/5 text-white/30 text-[9px] uppercase tracking-wider shrink-0">B2B Profile</span>
                        )}
                        {person && (() => {
                          const ep = (person.enriched_profile as Record<string, any>) || {};
                          const hasGrid = !!ep?.grid?.grid_name;
                          const hasLinkedIn = !!ep?.linkedin?.headline;
                          const hasTitle = !!person.title;
                          const hasGoals = !!(person as any).goals;
                          const sparse = !hasGrid && !hasLinkedIn && (!hasTitle || !hasGoals);
                          return sparse ? (
                            <span
                              title="This profile has limited enrichment data — the AI reasoning may be less precise."
                              className="px-1.5 py-0.5 rounded bg-amber-500/10 text-amber-300/70 text-[9px] uppercase tracking-wider shrink-0"
                            >
                              Profile Incomplete
                            </span>
                          ) : null;
                        })()}
                      </div>
                      <p className="text-white/50 text-sm">
                        {person?.title ? `${person.title} · ${person.company}` : person?.company}
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
                          <a href={twitterUrl(person.twitter_handle)} target="_blank" rel="noopener noreferrer"
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

                  {/* Grid B2B data — full-width below the avatar row so it
                      doesn't get crammed into a ~280px column on mobile. */}
                  {person && (person.enriched_profile as Record<string, any>)?.grid?.grid_description && (
                    <GridOrgCard grid={(person.enriched_profile as Record<string, any>).grid} />
                  )}

                  {/* About this person — bio / AI summary */}
                  {person?.ai_summary && (
                    <div className="p-4 rounded-xl bg-white/[0.02] border border-white/5">
                      <div className="text-xs text-white/40 font-medium mb-2 uppercase tracking-wider">
                        About {person.name?.split(" ")[0] ?? "this attendee"}
                      </div>
                      <p className="text-sm text-white/60 leading-relaxed">{person.ai_summary}</p>
                    </div>
                  )}

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

                  <button
                    onClick={() => deferMutation.mutate(match.id)}
                    disabled={deferMutation.isPending}
                    className="mt-3 w-full text-center text-xs text-white/30 hover:text-white/50 transition-colors py-1 disabled:opacity-50"
                  >
                    Maybe later
                  </button>
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

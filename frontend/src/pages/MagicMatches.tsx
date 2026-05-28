import { useState, useEffect, useRef } from "react";
import { useParams, useSearchParams, Link, useNavigate } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Sparkles, Brain, Target, MessageSquare, Check,
  Linkedin, Twitter, Globe, UserPlus, Send, CheckCheck, FileText, KeyRound,
} from "lucide-react";
import { getMatchesByMagicLink, getIncomingSummaryByMagicLink, updateProfileViaMagicLink, claimAccount, deferMatchByMagicLink, uploadPhotoViaMagicLink, acceptMatchByMagicLink } from "../api/client";
import PhotoUpload from "../components/PhotoUpload";
import { matchTypeConfig, twitterUrl } from "../utils/matchHelpers";
import GridOrgCard from "../components/GridOrgCard";
import AttendeeAvatar from "../components/AttendeeAvatar";

export default function MagicMatches() {
  const { token } = useParams<{ token: string }>();
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const [enrichForm, setEnrichForm] = useState({
    twitter_handle: "",
    target_companies: "",
    linkedin_url: "",
    goals: "",
  });
  const [enrichSaved, setEnrichSaved] = useState(false);
  const [claimForm, setClaimForm] = useState({ email: "", password: "" });
  const [claimError, setClaimError] = useState("");
  // When set, the claim flow chains in an accept-this-match call before
  // redirecting — so a no-login user can confirm interest with one password.
  const [pendingAcceptMatchId, setPendingAcceptMatchId] = useState<string | null>(null);
  const [pendingAcceptPersonName, setPendingAcceptPersonName] = useState<string | null>(null);
  // Arriving from the welcome email's "Unlock Full Access" CTA (?unlock=1)
  // pre-opens the claim panel and scrolls to it.
  const [searchParams] = useSearchParams();
  // Track whether the user has manually collapsed the panel so the
  // has_account-driven default doesn't override their explicit choice.
  const [claimToggled, setClaimToggled] = useState(false);
  const [claimOpen, setClaimOpen] = useState(searchParams.get("unlock") === "1");
  const claimRef = useRef<HTMLDivElement>(null);
  // Phase 3 — Maybe-later microcopy (shown for 5s on the FIRST defer of the
  // visit only) + Concierge-gating reason flag for the claim-panel header.
  const [deferHintForMatchId, setDeferHintForMatchId] = useState<string | null>(null);
  const deferHintEverShown = useRef(false);
  const [claimReason, setClaimReason] = useState<"concierge" | null>(null);
  useEffect(() => {
    if (searchParams.get("unlock") === "1") {
      claimRef.current?.scrollIntoView({ behavior: "smooth", block: "center" });
    }
  }, [searchParams]);

  // Phase 3 — ChatWidget on /m/ routes dispatches this when a non-claimed
  // visitor taps the Concierge button. Open the claim panel with the
  // Concierge-flavoured copy instead of letting the panel 401.
  useEffect(() => {
    const handler = () => {
      setClaimError("");
      setClaimReason("concierge");
      setClaimToggled(true);
      setClaimOpen(true);
      setTimeout(() => {
        claimRef.current?.scrollIntoView({ behavior: "smooth", block: "center" });
      }, 50);
    };
    window.addEventListener("pot:open-magic-claim", handler);
    return () => window.removeEventListener("pot:open-magic-claim", handler);
  }, []);

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ["magic-matches", token],
    queryFn: () => getMatchesByMagicLink(token!, 10),
    enabled: !!token,
  });

  // Phase 2 reciprocity reveal — aggregate counts across the FULL match set
  // (not just the visible cap), so the top banner stays honest.
  const { data: incomingSummary } = useQuery({
    queryKey: ["magic-incoming-summary", token],
    queryFn: () => getIncomingSummaryByMagicLink(token!),
    enabled: !!token,
  });

  // Phase 1 of the conversion funnel: unclaimed visitors land with the claim
  // panel expanded; claimed visitors keep it collapsed (they don't need it).
  // Only fires once per visit and only before the user has touched the toggle.
  useEffect(() => {
    if (claimToggled) return;
    if (searchParams.get("unlock") === "1") return; // already opened above
    if (data && data.has_account === false) {
      setClaimOpen(true);
    }
  }, [data, claimToggled, searchParams]);

  // The viewer's own profile rides along on the magic-link match response, so
  // no-login users get it without the auth-gated GET /attendees/{id} (which
  // 401s for them and left the enrichment card permanently hidden).
  const attendee = data?.viewer;

  const enrichMutation = useMutation({
    mutationFn: () => updateProfileViaMagicLink(token!, {
      twitter_handle: enrichForm.twitter_handle || undefined,
      target_companies: enrichForm.target_companies || undefined,
      linkedin_url: enrichForm.linkedin_url || undefined,
      goals: enrichForm.goals || undefined,
    }),
    onSuccess: () => {
      setEnrichSaved(true);
      queryClient.invalidateQueries({ queryKey: ["magic-matches", token] });
      setTimeout(() => setEnrichSaved(false), 3000);
    },
  });

  const deferMutation = useMutation({
    mutationFn: (matchId: string) => deferMatchByMagicLink(token!, matchId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["magic-matches", token] });
    },
  });

  const acceptMutation = useMutation({
    mutationFn: ({ matchId, status }: { matchId: string; status: "accepted" | "declined" }) =>
      acceptMatchByMagicLink(token!, matchId, status),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["magic-matches", token] });
    },
  });

  // Incoming reciprocity requests: the other party accepted, this viewer has
  // not responded. Mirrors MyMatches.tsx. `attendee` is the viewer profile.
  const requestMatches = (data?.matches ?? []).filter((m) => {
    if (!attendee) return false;
    const iAmA = m.attendee_a_id === attendee.id;
    const myStatus = iAmA ? m.status_a : m.status_b;
    const otherStatus = iAmA ? m.status_b : m.status_a;
    return otherStatus === "accepted" && myStatus === "pending";
  });

  const requestsRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (searchParams.get("tab") === "requests") {
      requestsRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  }, [searchParams, data]);

  // Claim a full account from this magic link. The token authenticates the
  // request server-side, so it bypasses the registration ticket gate — this
  // is how placeholder-email speakers get a real login. On success we store
  // the JWT, optionally chain in an accept for the match the user clicked,
  // and hard-navigate so AuthProvider picks up the session on mount.
  const claimMutation = useMutation({
    mutationFn: () => claimAccount({
      magic_token: token!,
      password: claimForm.password,
      email: claimForm.email.trim() || undefined,
    }),
    onSuccess: async (tok) => {
      localStorage.setItem("token", tok.access_token);
      if (pendingAcceptMatchId) {
        try {
          await acceptMatchByMagicLink(token!, pendingAcceptMatchId, "accepted");
        } catch {
          // Best-effort — if the accept fails the user still lands logged in
          // on /matches and can re-tap the green button there.
        }
      }
      window.location.href = pendingAcceptMatchId ? "/matches?accepted=1" : "/matches";
    },
    onError: (e: unknown) => {
      const detail = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      // Already claimed → route them to sign in. They'll land on /attendees
      // (Login.tsx hard-codes that) then can navigate to matches to confirm.
      if (detail && /already/i.test(detail)) {
        navigate("/login");
        return;
      }
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
    !attendee.goals ||
    !attendee.photo_url
  );

  const matches = data?.matches ?? [];

  // Phase 4 — paywall the deep tier for unclaimed magic-link visitors. Top 8
  // render in full (rich explanations + accept/defer); the rest are replaced
  // by a single paywall card. Claimed visitors see everything (they're past
  // the funnel). The backend still returns the full list — truncation is
  // purely frontend so the same endpoint serves the logged-in app intact.
  const PAYWALL_VISIBLE = 8;
  const lockedFromBackend = data?.locked_count ?? 0;
  const paywallActive =
    data?.has_account === false && matches.length + lockedFromBackend > PAYWALL_VISIBLE;
  const displayedMatches = paywallActive ? matches.slice(0, PAYWALL_VISIBLE) : matches;
  const paywalledCount = paywallActive
    ? Math.max(0, matches.length - PAYWALL_VISIBLE) + lockedFromBackend
    : 0;
  // Show a few teaser avatars behind the paywall card.
  const paywallTeasers = paywallActive
    ? matches.slice(PAYWALL_VISIBLE, PAYWALL_VISIBLE + 5)
    : [];

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
        <p className="text-white/40">
          {error ? "We couldn't load this page." : "This link is invalid or has expired."}
        </p>
        {error && (
          <button
            onClick={() => refetch()}
            className="px-4 py-2 rounded-xl font-semibold text-white text-sm"
            style={{ background: "#E76315" }}
          >
            Try again
          </button>
        )}
        <div>
          <Link to="/login" className="text-[#E76315] text-sm hover:underline">
            {error ? "If you have an account, you can sign in instead →" : "Log in instead →"}
          </Link>
        </div>
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

      {/* Reciprocity reveal — surfaces FULL-pool incoming-accept counts above
          the claim panel. Pending-for-you (someone accepted, viewer hasn't)
          wins over accepted-back so we never manufacture double urgency.
          Hidden entirely when both counts are zero. Clicking expands the
          claim panel — the default "Set your password" header already reads
          as the right conversion CTA for the message-them ask. */}
      {data?.attendee_id && incomingSummary && (
        (incomingSummary.count_pending_for_you > 0 ||
         incomingSummary.count_accepted_back > 0) && (
          <button
            onClick={() => {
              setClaimError("");
              setClaimToggled(true);
              setClaimOpen(true);
              setTimeout(() => {
                claimRef.current?.scrollIntoView({ behavior: "smooth", block: "center" });
              }, 50);
            }}
            className="w-full text-left rounded-2xl border border-emerald-500/40 bg-emerald-500/10 p-5 hover:bg-emerald-500/15 transition-colors"
          >
            <div className="flex items-center gap-3">
              <span className="relative flex h-2 w-2 shrink-0">
                <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-60"></span>
                <span className="relative inline-flex h-2 w-2 rounded-full bg-emerald-400"></span>
              </span>
              <div className="flex-1 min-w-0">
                <h3 className="text-base font-semibold text-white">
                  {incomingSummary.count_pending_for_you > 0
                    ? `${incomingSummary.count_pending_for_you} ${incomingSummary.count_pending_for_you === 1 ? "person" : "people"} ${incomingSummary.count_pending_for_you === 1 ? "wants" : "want"} to meet you`
                    : `You have ${incomingSummary.count_accepted_back} mutual ${incomingSummary.count_accepted_back === 1 ? "match" : "matches"} waiting`}
                </h3>
                <p className="text-sm text-emerald-200/80 mt-0.5">
                  {incomingSummary.count_pending_for_you > 0
                    ? "Set a password to message them."
                    : "Set a password to start the conversation."}
                </p>
              </div>
              <span className="text-emerald-300 text-lg shrink-0">→</span>
            </div>
          </button>
        )
      )}

      {/* Claim full account — token-authenticated, bypasses the ticket gate */}
      {data?.attendee_id && (
        <div ref={claimRef} className="p-5 rounded-2xl border border-white/10 bg-white/[0.03]">
          <button
            onClick={() => { setClaimToggled(true); setClaimOpen((v) => !v); }}
            className="w-full flex items-center gap-2 text-left"
          >
            <KeyRound className="w-5 h-5 text-[#E76315]" />
            <div className="flex-1">
              <h3 className="font-semibold text-[#E76315]">
                {claimReason === "concierge"
                  ? "AI Concierge"
                  : pendingAcceptPersonName
                    ? `Confirm interest in ${pendingAcceptPersonName.split(" ")[0]}`
                    : "Set your password"}
              </h3>
              <p className="text-xs text-white/40">
                {claimReason === "concierge"
                  ? "Claim your account in 10 seconds to chat with the AI Concierge about your matches."
                  : pendingAcceptPersonName
                    ? `Set a quick password (10 seconds) — we'll save your interest and let ${pendingAcceptPersonName.split(" ")[0]} know.`
                    : "You already have a profile from your ticket — just choose a password to log in and unlock messaging and the AI Concierge."}
              </p>
            </div>
            <span className="text-white/30 text-sm">{claimOpen ? "−" : "+"}</span>
          </button>
          {claimOpen && (
            <div className="space-y-3 mt-4">
              <div>
                <label className="text-xs text-white/50 block mb-1">
                  Email <span className="text-white/25">(leave blank — we'll use the email from your ticket)</span>
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
                {claimMutation.isPending
                  ? (pendingAcceptMatchId ? "Confirming…" : "Creating your account…")
                  : (pendingAcceptMatchId ? "Confirm & create my account" : "Create my account")}
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
                    queryClient.invalidateQueries({ queryKey: ["magic-matches", token] })
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

      {/* Requests banner — "N people want to meet you" */}
      <div ref={requestsRef}>
        {requestMatches.length > 0 && (
          <div className="mb-6 rounded-xl border border-[#E76315]/40 bg-[#E76315]/10 p-5">
            <div className="flex items-center gap-2 mb-3">
              <span className="relative flex h-2 w-2">
                <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-[#E76315] opacity-60"></span>
                <span className="relative inline-flex h-2 w-2 rounded-full bg-[#E76315]"></span>
              </span>
              <h3 className="text-base font-semibold text-white">
                {requestMatches.length} {requestMatches.length === 1 ? "person wants" : "people want"} to meet you
              </h3>
            </div>
            <p className="text-sm text-white/60 mb-4">Accept to lock in the match, then book a time.</p>
            <div className="space-y-3">
              {requestMatches.map((m) => (
                <div key={m.id} className="flex items-center justify-between gap-3 rounded-lg bg-black/20 p-3">
                  <div className="flex items-center gap-3 min-w-0">
                    {m.matched_attendee && (
                      <AttendeeAvatar attendee={m.matched_attendee} size="sm" />
                    )}
                    <div className="min-w-0">
                      <div className="text-sm font-medium text-white truncate">
                        {m.matched_attendee?.name ?? "A fellow attendee"}
                      </div>
                      <div className="text-xs text-white/50 truncate">
                        {[m.matched_attendee?.title, m.matched_attendee?.company].filter(Boolean).join(" · ")}
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center gap-2 shrink-0">
                    <button
                      onClick={() => acceptMutation.mutate({ matchId: m.id, status: "accepted" })}
                      disabled={acceptMutation.isPending}
                      className="rounded-lg bg-[#E76315] px-3 py-2 text-xs font-semibold text-white disabled:opacity-50"
                    >
                      Accept
                    </button>
                    <button
                      onClick={() => acceptMutation.mutate({ matchId: m.id, status: "declined" })}
                      disabled={acceptMutation.isPending}
                      className="rounded-lg border border-white/15 px-3 py-2 text-xs font-medium text-white/70 disabled:opacity-50"
                    >
                      Not now
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Match cards */}
      {matches.length === 0 ? (
        <div className="text-center py-12 text-white/30">
          <Brain className="w-8 h-8 mx-auto mb-3 text-white/10" />
          <p>Your matches are being generated. Check back soon.</p>
        </div>
      ) : (
        <div className="space-y-4">
          {displayedMatches.map((match, idx) => {
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

                  <div className="mt-3 space-y-2">
                    <button
                      onClick={() => {
                        setPendingAcceptMatchId(match.id);
                        setPendingAcceptPersonName(person?.name ?? null);
                        setClaimError("");
                        setClaimOpen(true);
                        setTimeout(() => {
                          claimRef.current?.scrollIntoView({
                            behavior: "smooth",
                            block: "center",
                          });
                        }, 50);
                      }}
                      className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-emerald-500 text-white rounded-xl text-sm font-semibold hover:bg-emerald-400 transition-all shadow-lg shadow-emerald-500/20"
                    >
                      <Check className="w-4 h-4" />
                      I'd like to meet
                    </button>
                    <button
                      onClick={() => {
                        // Phase 3 — show the "skip them permanently" microcopy
                        // for 5s on the FIRST defer of the visit only. Gated to
                        // unclaimed visitors; claimed users already have the
                        // logged-in Decline tool and don't need the nudge.
                        if (
                          !deferHintEverShown.current &&
                          data?.has_account === false
                        ) {
                          deferHintEverShown.current = true;
                          setDeferHintForMatchId(match.id);
                          setTimeout(() => {
                            setDeferHintForMatchId((prev) =>
                              prev === match.id ? null : prev
                            );
                          }, 5000);
                        }
                        deferMutation.mutate(match.id);
                      }}
                      disabled={deferMutation.isPending}
                      className="w-full text-center text-xs text-white/30 hover:text-white/50 transition-colors py-1 disabled:opacity-50"
                    >
                      Maybe later
                    </button>
                    {deferHintForMatchId === match.id && (
                      <p className="text-[11px] text-white/40 text-center mt-1 animate-in fade-in">
                        They'll resurface next session. Want to skip them permanently?{" "}
                        <button
                          onClick={() => {
                            setDeferHintForMatchId(null);
                            setClaimError("");
                            setClaimToggled(true);
                            setClaimOpen(true);
                            setTimeout(() => {
                              claimRef.current?.scrollIntoView({
                                behavior: "smooth",
                                block: "center",
                              });
                            }, 50);
                          }}
                          className="underline text-emerald-300 hover:text-emerald-200"
                        >
                          Set a password to decline →
                        </button>
                      </p>
                    )}
                  </div>
                </div>
              </div>
            );
          })}

          {/* Phase 4 paywall — replaces the deep tier for unclaimed visitors.
              The backend still returns the full list; only this surface
              truncates so the logged-in app stays unchanged. */}
          {paywallActive && paywalledCount > 0 && (
            <div className="relative mt-2 rounded-2xl border border-[#E76315]/40 bg-gradient-to-b from-[#E76315]/10 to-[#E76315]/5 p-6 overflow-hidden">
              {paywallTeasers.length > 0 && (
                <div className="absolute inset-x-0 top-0 flex justify-center gap-2 pt-2 opacity-30 pointer-events-none">
                  {paywallTeasers.map((m) =>
                    m.matched_attendee ? (
                      <AttendeeAvatar
                        key={m.id}
                        attendee={m.matched_attendee}
                        size="sm"
                      />
                    ) : null
                  )}
                </div>
              )}
              <div className="relative z-10 text-center space-y-3 pt-10">
                <h3 className="text-lg font-bold text-white">
                  You have {paywalledCount} more {paywalledCount === 1 ? "match" : "matches"} in your pool
                </h3>
                <p className="text-sm text-white/60 max-w-sm mx-auto">
                  Set a password to unlock your full match list, message them, and book meetings at the Louvre.
                </p>
                <button
                  onClick={() => {
                    setClaimError("");
                    setClaimToggled(true);
                    setClaimOpen(true);
                    setTimeout(() => {
                      claimRef.current?.scrollIntoView({
                        behavior: "smooth",
                        block: "center",
                      });
                    }, 50);
                  }}
                  className="inline-flex items-center gap-2 px-6 py-3 rounded-xl bg-[#E76315] text-white font-semibold text-sm hover:bg-[#D35400] transition-colors shadow-lg shadow-[#E76315]/20"
                >
                  Unlock my full match list →
                </button>
              </div>
            </div>
          )}
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

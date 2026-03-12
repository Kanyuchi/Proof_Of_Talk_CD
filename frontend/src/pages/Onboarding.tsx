import { useState } from "react";
import { CheckCircle, Sparkles, ChevronRight, Loader2 } from "lucide-react";
import { api } from "../api/client";

// ── Interest taxonomy (matches GPT-4o intent classifier) ─────────────────────
const INTEREST_OPTIONS = [
  "RWA tokenisation",
  "DeFi infrastructure",
  "Digital assets custody",
  "Institutional crypto",
  "CBDC & regulation",
  "Web3 compliance / MiCA",
  "Layer 2 / enterprise blockchain",
  "TradFi–DeFi bridge",
  "Stablecoins",
  "Venture & growth investing",
  "Sovereign wealth / SWF",
  "Prime brokerage",
  "Payment rails",
  "AI × crypto",
  "Cross-border settlements",
];

const SEEKING_OPTIONS = [
  "Investors / VCs",
  "Startups to back",
  "Enterprise clients",
  "Technology partners",
  "Regulators / policy makers",
  "Co-investors",
  "Strategic advisors",
  "Talent / team members",
];

const DEAL_STAGE_OPTIONS = [
  { value: "pre_seed", label: "Pre-seed / ideation" },
  { value: "seed", label: "Seed stage" },
  { value: "series_a", label: "Series A" },
  { value: "series_b", label: "Series B+" },
  { value: "growth", label: "Growth / late stage" },
  { value: "deploying_capital", label: "Deploying capital (investor)" },
  { value: "policy", label: "Policy / regulatory (non-commercial)" },
  { value: "not_raising", label: "Not raising — here to partner / learn" },
];

interface FormState {
  ticket_code: string;
  title: string;
  company: string;
  goals: string;
  interests: string[];
  seeking: string[];
  deal_stage: string;
  linkedin_url: string;
}

const INITIAL: FormState = {
  ticket_code: "",
  title: "",
  company: "",
  goals: "",
  interests: [],
  seeking: [],
  deal_stage: "",
  linkedin_url: "",
};

function toggle(arr: string[], val: string): string[] {
  return arr.includes(val) ? arr.filter((x) => x !== val) : [...arr, val];
}

export default function Onboarding() {
  const [form, setForm] = useState<FormState>(INITIAL);
  const [step, setStep] = useState<1 | 2 | 3>(1);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<{ name: string; message: string } | null>(null);

  const setField = (key: keyof FormState, value: string | string[]) =>
    setForm((prev) => ({ ...prev, [key]: value }));

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.ticket_code.trim()) {
      setError("Please enter your ticket code.");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const { data } = await api.post("/attendees/onboarding", {
        ticket_code: form.ticket_code.trim(),
        title: form.title || null,
        company: form.company || null,
        goals: form.goals || null,
        interests: form.interests,
        seeking: form.seeking,
        deal_stage: form.deal_stage || null,
        linkedin_url: form.linkedin_url || null,
      });
      setSuccess({ name: data.name, message: data.message });
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
        "Something went wrong. Please check your ticket code and try again.";
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  if (success) {
    return (
      <div className="min-h-[80vh] flex items-center justify-center px-4">
        <div className="max-w-md w-full text-center space-y-6">
          <div className="flex justify-center">
            <CheckCircle className="w-16 h-16 text-emerald-400" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-white mb-2">You're all set, {success.name.split(" ")[0]}.</h1>
            <p className="text-gray-400 leading-relaxed">{success.message}</p>
          </div>
          <div className="bg-white/5 border border-white/10 rounded-xl p-5 text-left space-y-2">
            <p className="text-xs text-gray-500 uppercase tracking-widest font-medium">What happens next</p>
            <ul className="text-sm text-gray-300 space-y-1.5">
              <li className="flex gap-2"><span className="text-amber-400">→</span> Our AI enriches your profile from public sources</li>
              <li className="flex gap-2"><span className="text-amber-400">→</span> Match recommendations generated 2 weeks before the event</li>
              <li className="flex gap-2"><span className="text-amber-400">→</span> You'll receive an email with your top matches to review</li>
            </ul>
          </div>
          <p className="text-xs text-gray-600">Proof of Talk 2026 · Louvre Palace, Paris · June 2–3</p>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-2xl mx-auto px-4 py-12">
      {/* Header */}
      <div className="text-center mb-10">
        <div className="flex items-center justify-center gap-2 mb-4">
          <Sparkles className="w-6 h-6 text-amber-400" />
          <span className="text-xs font-semibold tracking-[0.2em] uppercase text-amber-400">
            POT 2026 Matchmaker
          </span>
        </div>
        <h1 className="text-3xl font-bold text-white mb-3">Tell us what you're here for</h1>
        <p className="text-gray-400 text-base max-w-md mx-auto">
          3 minutes of intent signals → personalised match recommendations before the event.
          We'll send your top connections directly to your inbox.
        </p>
      </div>

      {/* Step indicator */}
      <div className="flex items-center gap-2 justify-center mb-8">
        {[1, 2, 3].map((s) => (
          <div key={s} className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => s < step && setStep(s as 1 | 2 | 3)}
              className={`w-8 h-8 rounded-full text-sm font-semibold transition-all
                ${step === s
                  ? "bg-amber-400 text-black"
                  : s < step
                  ? "bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 cursor-pointer"
                  : "bg-white/5 text-gray-600 border border-white/10 cursor-default"
                }`}
            >
              {s < step ? "✓" : s}
            </button>
            {s < 3 && <div className={`w-12 h-px ${s < step ? "bg-emerald-500/40" : "bg-white/10"}`} />}
          </div>
        ))}
      </div>

      <form onSubmit={handleSubmit}>
        {/* ── Step 1: Identity ─────────────────────────────────────────────── */}
        {step === 1 && (
          <div className="space-y-6">
            <div className="bg-white/3 border border-white/8 rounded-2xl p-6 space-y-5">
              <p className="text-xs font-semibold tracking-widest text-gray-500 uppercase">
                Step 1 of 3 — Identify yourself
              </p>

              <div>
                <label className="block text-sm font-medium text-gray-300 mb-1.5">
                  Ticket code <span className="text-amber-400">*</span>
                </label>
                <input
                  type="text"
                  required
                  placeholder="e.g. POT-ABCD1234"
                  value={form.ticket_code}
                  onChange={(e) => setField("ticket_code", e.target.value)}
                  className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-white placeholder-gray-600 focus:outline-none focus:border-amber-400/50 focus:ring-1 focus:ring-amber-400/20 transition font-mono text-sm"
                />
                <p className="mt-1 text-xs text-gray-600">
                  Found in your Extasy confirmation email under "Ticket Details"
                </p>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-1.5">Job title</label>
                  <input
                    type="text"
                    placeholder="e.g. Partner, CTO, Head of DeFi"
                    value={form.title}
                    onChange={(e) => setField("title", e.target.value)}
                    className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-white placeholder-gray-600 focus:outline-none focus:border-amber-400/50 focus:ring-1 focus:ring-amber-400/20 transition text-sm"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-1.5">Company</label>
                  <input
                    type="text"
                    placeholder="e.g. Andreessen Horowitz"
                    value={form.company}
                    onChange={(e) => setField("company", e.target.value)}
                    className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-white placeholder-gray-600 focus:outline-none focus:border-amber-400/50 focus:ring-1 focus:ring-amber-400/20 transition text-sm"
                  />
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-300 mb-1.5">LinkedIn URL (optional)</label>
                <input
                  type="text"
                  placeholder="linkedin.com/in/yourname"
                  value={form.linkedin_url}
                  onChange={(e) => setField("linkedin_url", e.target.value)}
                  className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-white placeholder-gray-600 focus:outline-none focus:border-amber-400/50 focus:ring-1 focus:ring-amber-400/20 transition text-sm"
                />
                <p className="mt-1 text-xs text-gray-600">Enables deeper career-history enrichment for better matches</p>
              </div>
            </div>

            <button
              type="button"
              onClick={() => setStep(2)}
              disabled={!form.ticket_code.trim()}
              className="w-full flex items-center justify-center gap-2 bg-amber-400 hover:bg-amber-300 disabled:opacity-40 disabled:cursor-not-allowed text-black font-semibold py-3.5 rounded-xl transition-all text-sm"
            >
              Continue <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        )}

        {/* ── Step 2: Interests & goals ────────────────────────────────────── */}
        {step === 2 && (
          <div className="space-y-6">
            <div className="bg-white/3 border border-white/8 rounded-2xl p-6 space-y-6">
              <p className="text-xs font-semibold tracking-widest text-gray-500 uppercase">
                Step 2 of 3 — Interests & goals
              </p>

              <div>
                <label className="block text-sm font-medium text-gray-300 mb-3">
                  What are you here for? <span className="text-gray-600">(pick all that apply)</span>
                </label>
                <div className="flex flex-wrap gap-2">
                  {INTEREST_OPTIONS.map((opt) => (
                    <button
                      key={opt}
                      type="button"
                      onClick={() => setField("interests", toggle(form.interests, opt))}
                      className={`px-3 py-1.5 rounded-lg text-xs font-medium border transition-all
                        ${form.interests.includes(opt)
                          ? "bg-amber-400/15 border-amber-400/50 text-amber-300"
                          : "bg-white/3 border-white/10 text-gray-400 hover:border-white/20 hover:text-gray-300"
                        }`}
                    >
                      {opt}
                    </button>
                  ))}
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-300 mb-1.5">
                  In one or two sentences, what's your goal at POT 2026?
                </label>
                <textarea
                  rows={3}
                  placeholder="e.g. Deploying €50M into Series B tokenisation infrastructure. Looking for teams with institutional-grade custody and a live product."
                  value={form.goals}
                  onChange={(e) => setField("goals", e.target.value)}
                  className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-white placeholder-gray-600 focus:outline-none focus:border-amber-400/50 focus:ring-1 focus:ring-amber-400/20 transition text-sm resize-none"
                />
                <p className="mt-1 text-xs text-gray-600">The more specific, the better your matches.</p>
              </div>
            </div>

            <div className="flex gap-3">
              <button
                type="button"
                onClick={() => setStep(1)}
                className="flex-1 py-3.5 rounded-xl border border-white/10 text-gray-400 hover:border-white/20 hover:text-white transition text-sm font-medium"
              >
                Back
              </button>
              <button
                type="button"
                onClick={() => setStep(3)}
                className="flex-[2] flex items-center justify-center gap-2 bg-amber-400 hover:bg-amber-300 text-black font-semibold py-3.5 rounded-xl transition-all text-sm"
              >
                Continue <ChevronRight className="w-4 h-4" />
              </button>
            </div>
          </div>
        )}

        {/* ── Step 3: Deal signals ──────────────────────────────────────────── */}
        {step === 3 && (
          <div className="space-y-6">
            <div className="bg-white/3 border border-white/8 rounded-2xl p-6 space-y-6">
              <p className="text-xs font-semibold tracking-widest text-gray-500 uppercase">
                Step 3 of 3 — Deal signals
              </p>

              <div>
                <label className="block text-sm font-medium text-gray-300 mb-1.5">
                  Where are you in your journey?
                </label>
                <div className="grid grid-cols-2 gap-2">
                  {DEAL_STAGE_OPTIONS.map(({ value, label }) => (
                    <button
                      key={value}
                      type="button"
                      onClick={() => setField("deal_stage", form.deal_stage === value ? "" : value)}
                      className={`px-3 py-2.5 rounded-xl text-xs font-medium border text-left transition-all
                        ${form.deal_stage === value
                          ? "bg-amber-400/15 border-amber-400/50 text-amber-300"
                          : "bg-white/3 border-white/10 text-gray-400 hover:border-white/20 hover:text-gray-300"
                        }`}
                    >
                      {label}
                    </button>
                  ))}
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-300 mb-3">
                  Who do you want to meet? <span className="text-gray-600">(pick all that apply)</span>
                </label>
                <div className="flex flex-wrap gap-2">
                  {SEEKING_OPTIONS.map((opt) => (
                    <button
                      key={opt}
                      type="button"
                      onClick={() => setField("seeking", toggle(form.seeking, opt))}
                      className={`px-3 py-1.5 rounded-lg text-xs font-medium border transition-all
                        ${form.seeking.includes(opt)
                          ? "bg-violet-500/15 border-violet-500/50 text-violet-300"
                          : "bg-white/3 border-white/10 text-gray-400 hover:border-white/20 hover:text-gray-300"
                        }`}
                    >
                      {opt}
                    </button>
                  ))}
                </div>
              </div>
            </div>

            {error && (
              <div className="bg-red-500/10 border border-red-500/30 rounded-xl px-4 py-3 text-red-400 text-sm">
                {error}
              </div>
            )}

            <div className="flex gap-3">
              <button
                type="button"
                onClick={() => setStep(2)}
                className="flex-1 py-3.5 rounded-xl border border-white/10 text-gray-400 hover:border-white/20 hover:text-white transition text-sm font-medium"
              >
                Back
              </button>
              <button
                type="submit"
                disabled={loading}
                className="flex-[2] flex items-center justify-center gap-2 bg-amber-400 hover:bg-amber-300 disabled:opacity-60 text-black font-semibold py-3.5 rounded-xl transition-all text-sm"
              >
                {loading ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" /> Saving…
                  </>
                ) : (
                  <>
                    <Sparkles className="w-4 h-4" /> Submit & get matched
                  </>
                )}
              </button>
            </div>

            <p className="text-center text-xs text-gray-600">
              Your data is used only for match recommendations within Proof of Talk 2026.
            </p>
          </div>
        )}
      </form>
    </div>
  );
}

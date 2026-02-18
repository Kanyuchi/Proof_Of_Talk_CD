import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Sparkles, ChevronRight, ChevronLeft, Check, X, Eye, EyeOff } from "lucide-react";
import { useAuth } from "../hooks/useAuth";

const TICKET_TYPES = [
  { value: "delegate", label: "Delegate", desc: "Conference attendee" },
  { value: "vip", label: "VIP", desc: "Sovereign fund, family office" },
  { value: "speaker", label: "Speaker", desc: "Keynote or panel speaker" },
  { value: "sponsor", label: "Sponsor", desc: "Corporate sponsor" },
] as const;

const SUGGESTED_INTERESTS = [
  "DeFi", "CBDC", "tokenisation", "institutional custody", "blockchain infrastructure",
  "regulatory compliance", "TradFi-DeFi", "Layer-2", "KYC/AML", "cross-chain",
  "NFTs", "DAOs", "Web3", "zero-knowledge proofs", "tokenised RWA",
];

export default function Register() {
  const { register } = useAuth();
  const navigate = useNavigate();
  const [step, setStep] = useState(1);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showPw, setShowPw] = useState(false);

  // Form state
  const [form, setForm] = useState({
    email: "",
    password: "",
    confirmPassword: "",
    name: "",
    company: "",
    title: "",
    ticket_type: "delegate",
    interests: [] as string[],
    interestInput: "",
    goals: "",
    linkedin_url: "",
    twitter_handle: "",
    company_website: "",
  });

  const set = (key: string, value: unknown) =>
    setForm((f) => ({ ...f, [key]: value }));

  const addInterest = (val: string) => {
    const trimmed = val.trim().toLowerCase();
    if (trimmed && !form.interests.includes(trimmed)) {
      set("interests", [...form.interests, trimmed]);
    }
    set("interestInput", "");
  };

  const removeInterest = (tag: string) =>
    set("interests", form.interests.filter((i) => i !== tag));

  const validateStep = () => {
    setError(null);
    if (step === 1) {
      if (!form.email || !form.password) return false;
      if (form.password !== form.confirmPassword) {
        setError("Passwords don't match");
        return false;
      }
      if (form.password.length < 8) {
        setError("Password must be at least 8 characters");
        return false;
      }
    }
    if (step === 2) {
      if (!form.name || !form.company || !form.title) {
        setError("Please fill in all required fields");
        return false;
      }
    }
    return true;
  };

  const handleNext = () => {
    if (validateStep()) setStep((s) => s + 1);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      await register({
        email: form.email,
        password: form.password,
        name: form.name,
        company: form.company,
        title: form.title,
        ticket_type: form.ticket_type,
        interests: form.interests,
        goals: form.goals,
        linkedin_url: form.linkedin_url || undefined,
        twitter_handle: form.twitter_handle || undefined,
        company_website: form.company_website || undefined,
      });
      navigate("/attendees");
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setError(msg || "Registration failed. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  const inputCls =
    "w-full px-4 py-2.5 bg-white/5 border border-white/10 rounded-xl text-sm text-white placeholder:text-white/20 focus:outline-none focus:border-amber-400/50";

  return (
    <div className="min-h-[80vh] flex items-center justify-center py-8">
      <div className="w-full max-w-lg">
        {/* Header */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-gradient-to-br from-amber-400 to-amber-600 mb-4">
            <Sparkles className="w-7 h-7 text-black" />
          </div>
          <h1 className="text-2xl font-bold">Join Proof of Talk 2026</h1>
          <p className="text-white/40 text-sm mt-1">
            Register your profile and let AI find your perfect connections
          </p>
        </div>

        {/* Step indicators */}
        <div className="flex items-center justify-center gap-2 mb-6">
          {[1, 2, 3].map((s) => (
            <div key={s} className="flex items-center gap-2">
              <div
                className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold transition-all ${
                  s < step
                    ? "bg-amber-400 text-black"
                    : s === step
                    ? "bg-amber-400/20 text-amber-400 border border-amber-400/40"
                    : "bg-white/5 text-white/30 border border-white/10"
                }`}
              >
                {s < step ? <Check className="w-3.5 h-3.5" /> : s}
              </div>
              {s < 3 && <div className="w-8 h-px bg-white/10" />}
            </div>
          ))}
        </div>

        <div className="p-6 rounded-2xl bg-white/[0.03] border border-white/10">
          {error && (
            <div className="mb-4 p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-sm">
              {error}
            </div>
          )}

          {/* Step 1: Account */}
          {step === 1 && (
            <div className="space-y-4">
              <h2 className="text-lg font-semibold">Create your account</h2>
              <div>
                <label className="block text-xs text-white/40 uppercase font-medium mb-1.5">Email *</label>
                <input type="email" required value={form.email} onChange={(e) => set("email", e.target.value)} placeholder="you@company.com" className={inputCls} />
              </div>
              <div>
                <label className="block text-xs text-white/40 uppercase font-medium mb-1.5">Password *</label>
                <div className="relative">
                  <input type={showPw ? "text" : "password"} required value={form.password} onChange={(e) => set("password", e.target.value)} placeholder="Min. 8 characters" className={`${inputCls} pr-10`} />
                  <button type="button" onClick={() => setShowPw((v) => !v)} className="absolute right-3 top-1/2 -translate-y-1/2 text-white/30 hover:text-white/60">
                    {showPw ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
              </div>
              <div>
                <label className="block text-xs text-white/40 uppercase font-medium mb-1.5">Confirm Password *</label>
                <input type="password" required value={form.confirmPassword} onChange={(e) => set("confirmPassword", e.target.value)} placeholder="••••••••" className={inputCls} />
              </div>
              <button onClick={handleNext} className="w-full flex items-center justify-center gap-2 py-3 bg-amber-400 text-black font-semibold rounded-xl hover:bg-amber-300 transition-all">
                Continue <ChevronRight className="w-4 h-4" />
              </button>
            </div>
          )}

          {/* Step 2: Profile */}
          {step === 2 && (
            <div className="space-y-4">
              <h2 className="text-lg font-semibold">Your profile</h2>
              <div className="grid grid-cols-2 gap-3">
                <div className="col-span-2">
                  <label className="block text-xs text-white/40 uppercase font-medium mb-1.5">Full Name *</label>
                  <input type="text" required value={form.name} onChange={(e) => set("name", e.target.value)} placeholder="Jane Smith" className={inputCls} />
                </div>
                <div>
                  <label className="block text-xs text-white/40 uppercase font-medium mb-1.5">Company *</label>
                  <input type="text" required value={form.company} onChange={(e) => set("company", e.target.value)} placeholder="Acme Capital" className={inputCls} />
                </div>
                <div>
                  <label className="block text-xs text-white/40 uppercase font-medium mb-1.5">Title *</label>
                  <input type="text" required value={form.title} onChange={(e) => set("title", e.target.value)} placeholder="Managing Partner" className={inputCls} />
                </div>
              </div>
              <div>
                <label className="block text-xs text-white/40 uppercase font-medium mb-1.5">Ticket Type *</label>
                <div className="grid grid-cols-2 gap-2">
                  {TICKET_TYPES.map(({ value, label, desc }) => (
                    <button
                      key={value}
                      type="button"
                      onClick={() => set("ticket_type", value)}
                      className={`p-3 rounded-xl border text-left transition-all ${
                        form.ticket_type === value
                          ? "bg-amber-400/10 border-amber-400/40 text-amber-400"
                          : "bg-white/[0.02] border-white/10 text-white/60 hover:border-white/20"
                      }`}
                    >
                      <div className="text-sm font-medium">{label}</div>
                      <div className="text-xs opacity-60">{desc}</div>
                    </button>
                  ))}
                </div>
              </div>
              <div className="flex gap-2">
                <button onClick={() => setStep(1)} className="flex items-center gap-1 px-4 py-3 rounded-xl border border-white/10 text-white/60 hover:text-white transition-all text-sm">
                  <ChevronLeft className="w-4 h-4" /> Back
                </button>
                <button onClick={handleNext} className="flex-1 flex items-center justify-center gap-2 py-3 bg-amber-400 text-black font-semibold rounded-xl hover:bg-amber-300 transition-all">
                  Continue <ChevronRight className="w-4 h-4" />
                </button>
              </div>
            </div>
          )}

          {/* Step 3: Interests + Goals */}
          {step === 3 && (
            <form onSubmit={handleSubmit} className="space-y-4">
              <h2 className="text-lg font-semibold">Your interests & goals</h2>
              <div>
                <label className="block text-xs text-white/40 uppercase font-medium mb-1.5">Interests</label>
                <div className="flex flex-wrap gap-1.5 mb-2">
                  {form.interests.map((tag) => (
                    <span key={tag} className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full bg-amber-400/10 text-amber-400 text-xs border border-amber-400/20">
                      {tag}
                      <button type="button" onClick={() => removeInterest(tag)}>
                        <X className="w-3 h-3" />
                      </button>
                    </span>
                  ))}
                </div>
                <input
                  type="text"
                  value={form.interestInput}
                  onChange={(e) => set("interestInput", e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" || e.key === ",") {
                      e.preventDefault();
                      addInterest(form.interestInput);
                    }
                  }}
                  placeholder="Type interest and press Enter…"
                  className={inputCls}
                />
                <div className="flex flex-wrap gap-1 mt-2">
                  {SUGGESTED_INTERESTS.filter((s) => !form.interests.includes(s.toLowerCase())).slice(0, 8).map((s) => (
                    <button key={s} type="button" onClick={() => addInterest(s)} className="px-2 py-0.5 rounded-full bg-white/5 text-white/40 text-xs hover:text-white/70 hover:bg-white/10 transition-all">
                      + {s}
                    </button>
                  ))}
                </div>
              </div>
              <div>
                <label className="block text-xs text-white/40 uppercase font-medium mb-1.5">Goals at the Conference</label>
                <textarea value={form.goals} onChange={(e) => set("goals", e.target.value)} placeholder="What do you want to achieve? (investors, partners, pilots…)" rows={3} className={`${inputCls} resize-none`} />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs text-white/40 uppercase font-medium mb-1.5">LinkedIn URL</label>
                  <input type="url" value={form.linkedin_url} onChange={(e) => set("linkedin_url", e.target.value)} placeholder="linkedin.com/in/you" className={inputCls} />
                </div>
                <div>
                  <label className="block text-xs text-white/40 uppercase font-medium mb-1.5">Twitter / X</label>
                  <input type="text" value={form.twitter_handle} onChange={(e) => set("twitter_handle", e.target.value)} placeholder="@handle" className={inputCls} />
                </div>
                <div className="col-span-2">
                  <label className="block text-xs text-white/40 uppercase font-medium mb-1.5">Company Website</label>
                  <input type="url" value={form.company_website} onChange={(e) => set("company_website", e.target.value)} placeholder="https://company.com" className={inputCls} />
                </div>
              </div>
              <div className="flex gap-2">
                <button type="button" onClick={() => setStep(2)} className="flex items-center gap-1 px-4 py-3 rounded-xl border border-white/10 text-white/60 hover:text-white transition-all text-sm">
                  <ChevronLeft className="w-4 h-4" /> Back
                </button>
                <button type="submit" disabled={loading} className="flex-1 flex items-center justify-center gap-2 py-3 bg-amber-400 text-black font-semibold rounded-xl hover:bg-amber-300 transition-all disabled:opacity-50">
                  {loading ? (
                    <div className="w-4 h-4 border-2 border-black/30 border-t-black rounded-full animate-spin" />
                  ) : (
                    <Sparkles className="w-4 h-4" />
                  )}
                  {loading ? "Creating your profile…" : "Complete Registration"}
                </button>
              </div>
            </form>
          )}
        </div>

        <p className="text-center text-sm text-white/40 mt-4">
          Already have an account?{" "}
          <Link to="/login" className="text-amber-400 hover:text-amber-300">
            Sign in
          </Link>
        </p>
      </div>
    </div>
  );
}

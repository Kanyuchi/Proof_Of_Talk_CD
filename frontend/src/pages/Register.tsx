import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { ChevronRight, ChevronLeft, Check, Eye, EyeOff } from "lucide-react";
import { useAuth } from "../hooks/useAuth";

export default function Register() {
  const { register } = useAuth();
  const navigate = useNavigate();
  const [step, setStep] = useState(1);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showPw, setShowPw] = useState(false);

  const [form, setForm] = useState({
    email: "",
    password: "",
    confirmPassword: "",
    name: "",
    company: "",
    title: "",
    company_website: "",
    goals: "",
    seeking: "",
  });

  const set = (key: string, value: string) =>
    setForm((f) => ({ ...f, [key]: value }));

  const normalizeUrl = (val: string): string => {
    if (!val.trim()) return val;
    if (/^https?:\/\//i.test(val)) return val;
    return `https://${val}`;
  };

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

  const handleSubmit = async (e: React.SyntheticEvent) => {
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
        ticket_type: "delegate",
        interests: [],
        goals: form.goals,
        seeking: form.seeking ? [form.seeking] : [],
        company_website: normalizeUrl(form.company_website) || undefined,
      });
      navigate("/matches");
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setError(msg || "Registration failed. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  const inputCls =
    "w-full px-4 py-3 bg-white/5 border border-white/10 rounded-xl text-sm text-white placeholder:text-white/20 focus:outline-none focus:border-[#E76315]/50 transition-colors";

  const stepLabels = ["Account", "Profile", "Intent"];

  return (
    <div className="min-h-[80vh] flex items-center justify-center py-8">
      <div className="w-full max-w-md">
        {/* Header */}
        <div className="text-center mb-8">
          {/* POT logo mark */}
          <div className="flex items-center justify-center gap-3 mb-4">
            <div
              className="w-7 h-9 bg-[#E76315]"
              style={{ clipPath: "polygon(0 0, 100% 8%, 100% 92%, 0 100%)" }}
            />
            <span className="text-lg font-semibold" style={{ fontFamily: "var(--font-heading)" }}>
              Proof of Talk 2026
            </span>
          </div>
          <p className="text-white/40 text-sm">
            Tell us what you need. We'll tell you who to meet.
          </p>
        </div>

        {/* Step indicators */}
        <div className="flex items-center justify-center gap-2 mb-6">
          {[1, 2, 3].map((s) => (
            <div key={s} className="flex items-center gap-2">
              <div className="flex flex-col items-center gap-1">
                <div
                  className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold transition-all ${
                    s < step
                      ? "bg-[#E76315] text-white"
                      : s === step
                      ? "bg-[#E76315]/20 text-[#E76315] border border-[#E76315]/40"
                      : "bg-white/5 text-white/30 border border-white/10"
                  }`}
                >
                  {s < step ? <Check className="w-3.5 h-3.5" /> : s}
                </div>
                <span className={`text-[10px] ${s === step ? "text-[#E76315]" : "text-white/30"}`}>
                  {stepLabels[s - 1]}
                </span>
              </div>
              {s < 3 && <div className="w-8 h-px bg-white/10 mb-4" />}
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
              <h2 className="text-lg font-semibold" style={{ fontFamily: "var(--font-heading)" }}>
                Create your account
              </h2>
              <div>
                <label className="block text-xs text-white/40 uppercase font-medium mb-1.5">Email *</label>
                <input
                  type="email"
                  required
                  value={form.email}
                  onChange={(e) => set("email", e.target.value)}
                  placeholder="you@company.com"
                  className={inputCls}
                />
              </div>
              <div>
                <label className="block text-xs text-white/40 uppercase font-medium mb-1.5">Password *</label>
                <div className="relative">
                  <input
                    type={showPw ? "text" : "password"}
                    required
                    value={form.password}
                    onChange={(e) => set("password", e.target.value)}
                    placeholder="Min. 8 characters"
                    className={`${inputCls} pr-10`}
                  />
                  <button
                    type="button"
                    onClick={() => setShowPw((v) => !v)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-white/30 hover:text-white/60"
                  >
                    {showPw ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
              </div>
              <div>
                <label className="block text-xs text-white/40 uppercase font-medium mb-1.5">Confirm Password *</label>
                <input
                  type="password"
                  required
                  value={form.confirmPassword}
                  onChange={(e) => set("confirmPassword", e.target.value)}
                  placeholder="••••••••"
                  className={inputCls}
                />
              </div>
              <button
                onClick={handleNext}
                className="w-full flex items-center justify-center gap-2 py-3 min-h-[44px] text-white font-semibold rounded-xl transition-all"
                style={{ background: "var(--pot-orange)" }}
              >
                Continue <ChevronRight className="w-4 h-4" />
              </button>
            </div>
          )}

          {/* Step 2: Profile */}
          {step === 2 && (
            <div className="space-y-4">
              <h2 className="text-lg font-semibold" style={{ fontFamily: "var(--font-heading)" }}>
                Your profile
              </h2>
              <div>
                <label className="block text-xs text-white/40 uppercase font-medium mb-1.5">Full Name *</label>
                <input
                  type="text"
                  required
                  value={form.name}
                  onChange={(e) => set("name", e.target.value)}
                  placeholder="Jane Smith"
                  className={inputCls}
                />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs text-white/40 uppercase font-medium mb-1.5">Company *</label>
                  <input
                    type="text"
                    required
                    value={form.company}
                    onChange={(e) => set("company", e.target.value)}
                    placeholder="Acme Capital"
                    className={inputCls}
                  />
                </div>
                <div>
                  <label className="block text-xs text-white/40 uppercase font-medium mb-1.5">Title *</label>
                  <input
                    type="text"
                    required
                    value={form.title}
                    onChange={(e) => set("title", e.target.value)}
                    placeholder="Managing Partner"
                    className={inputCls}
                  />
                </div>
              </div>
              <div>
                <label className="block text-xs text-white/40 uppercase font-medium mb-1.5">Company Website</label>
                <input
                  type="text"
                  value={form.company_website}
                  onChange={(e) => set("company_website", e.target.value)}
                  onBlur={(e) => set("company_website", normalizeUrl(e.target.value))}
                  placeholder="company.com"
                  className={inputCls}
                />
              </div>
              <div className="flex gap-2">
                <button
                  onClick={() => setStep(1)}
                  className="flex items-center gap-1 px-4 py-3 min-h-[44px] rounded-xl border border-white/10 text-white/60 hover:text-white transition-all text-sm"
                >
                  <ChevronLeft className="w-4 h-4" /> Back
                </button>
                <button
                  onClick={handleNext}
                  className="flex-1 flex items-center justify-center gap-2 py-3 min-h-[44px] text-white font-semibold rounded-xl transition-all"
                  style={{ background: "var(--pot-orange)" }}
                >
                  Continue <ChevronRight className="w-4 h-4" />
                </button>
              </div>
            </div>
          )}

          {/* Step 3: Intent */}
          {step === 3 && (
            <form onSubmit={handleSubmit} className="space-y-4">
              <h2 className="text-lg font-semibold" style={{ fontFamily: "var(--font-heading)" }}>
                Two quick questions
              </h2>
              <div>
                <label className="block text-xs text-white/40 uppercase font-medium mb-1.5">
                  What are you looking to achieve at POT 2026?
                </label>
                <textarea
                  value={form.goals}
                  onChange={(e) => set("goals", e.target.value)}
                  placeholder="e.g. Deploy €50M into Series B tokenisation infrastructure over 12 months…"
                  rows={3}
                  className={`${inputCls} resize-none`}
                />
              </div>
              <div>
                <label className="block text-xs text-white/40 uppercase font-medium mb-1.5">
                  Who is your ideal connection at this event?
                </label>
                <textarea
                  value={form.seeking}
                  onChange={(e) => set("seeking", e.target.value)}
                  placeholder="e.g. Founders with institutional-grade custody infrastructure and a live product…"
                  rows={3}
                  className={`${inputCls} resize-none`}
                />
              </div>
              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={() => setStep(2)}
                  className="flex items-center gap-1 px-4 py-3 min-h-[44px] rounded-xl border border-white/10 text-white/60 hover:text-white transition-all text-sm"
                >
                  <ChevronLeft className="w-4 h-4" /> Back
                </button>
                <button
                  type="submit"
                  disabled={loading}
                  className="flex-1 flex items-center justify-center gap-2 py-3 min-h-[44px] text-white font-semibold rounded-xl transition-all disabled:opacity-50"
                  style={{ background: "var(--pot-orange)" }}
                >
                  {loading ? (
                    <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  ) : null}
                  {loading ? "Creating your profile…" : "Get my introductions"}
                </button>
              </div>
            </form>
          )}
        </div>

        <p className="text-center text-sm text-white/40 mt-4">
          Already have an account?{" "}
          <Link to="/login" className="text-[#E76315] hover:text-[#FF833A]">
            Sign in
          </Link>
        </p>
      </div>
    </div>
  );
}

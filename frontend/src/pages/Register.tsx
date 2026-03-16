import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Eye, EyeOff, Linkedin } from "lucide-react";
import { useAuth } from "../hooks/useAuth";

export default function Register() {
  const { register } = useAuth();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showPw, setShowPw] = useState(false);

  const [form, setForm] = useState({
    email: "",
    password: "",
    name: "",
    linkedin_url: "",
    goals: "",
  });

  const set = (key: string, value: string) =>
    setForm((f) => ({ ...f, [key]: value }));

  const normalizeUrl = (val: string): string => {
    if (!val.trim()) return val;
    if (/^https?:\/\//i.test(val)) return val;
    return `https://${val}`;
  };

  const handleSubmit = async (e: React.SyntheticEvent) => {
    e.preventDefault();
    setError(null);

    if (!form.email || !form.password || !form.name) {
      setError("Email, password and name are required");
      return;
    }
    if (form.password.length < 8) {
      setError("Password must be at least 8 characters");
      return;
    }
    if (!/[A-Z]/.test(form.password) || !/[a-z]/.test(form.password) || !/\d/.test(form.password)) {
      setError("Password must contain uppercase, lowercase, and a number (e.g. Paris2026)");
      return;
    }

    setLoading(true);
    try {
      await register({
        email: form.email,
        password: form.password,
        name: form.name,
        company: "",
        title: "",
        ticket_type: "delegate",
        interests: [],
        goals: form.goals || undefined,
        seeking: [],
        linkedin_url: normalizeUrl(form.linkedin_url) || undefined,
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

  return (
    <div className="min-h-[80vh] flex items-center justify-center py-8">
      <div className="w-full max-w-md">
        {/* Header */}
        <div className="text-center mb-8">
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
            Tell us who you are. We'll tell you who to meet.
          </p>
        </div>

        <div className="p-6 rounded-2xl bg-white/[0.03] border border-white/10">
          {error && (
            <div className="mb-4 p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-sm">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="grid grid-cols-2 gap-3">
              <div className="col-span-2">
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
              <div className="col-span-2">
                <label className="block text-xs text-white/40 uppercase font-medium mb-1.5">Password *</label>
                <div className="relative">
                  <input
                    type={showPw ? "text" : "password"}
                    required
                    value={form.password}
                    onChange={(e) => set("password", e.target.value)}
                    placeholder="Min. 8 chars · uppercase + number"
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
              <div className="col-span-2">
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
            </div>

            <div>
              <label className="block text-xs text-white/40 uppercase font-medium mb-1.5 flex items-center gap-1.5">
                <Linkedin className="w-3.5 h-3.5 text-blue-400" />
                LinkedIn URL
                <span className="text-white/20 normal-case font-normal ml-1">— we build your profile from this</span>
              </label>
              <input
                type="text"
                value={form.linkedin_url}
                onChange={(e) => set("linkedin_url", e.target.value)}
                onBlur={(e) => set("linkedin_url", normalizeUrl(e.target.value))}
                placeholder="linkedin.com/in/yourname"
                className={inputCls}
              />
            </div>

            <div>
              <label className="block text-xs text-white/40 uppercase font-medium mb-1.5">
                What are you looking to achieve at POT 2026?
              </label>
              <textarea
                value={form.goals}
                onChange={(e) => set("goals", e.target.value)}
                placeholder="e.g. Deploy €50M into Series B tokenisation infrastructure, find co-investors for a CBDC pilot…"
                rows={3}
                className={`${inputCls} resize-none`}
              />
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full flex items-center justify-center gap-2 py-3 min-h-[44px] text-white font-semibold rounded-xl transition-all disabled:opacity-50"
              style={{ background: "var(--pot-orange)" }}
            >
              {loading ? (
                <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              ) : null}
              {loading ? "Creating your profile…" : "Get my introductions →"}
            </button>
          </form>
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

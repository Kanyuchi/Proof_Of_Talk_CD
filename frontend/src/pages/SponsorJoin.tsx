import { useState } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";

const inputCls =
  "w-full px-4 py-3 bg-white/5 border border-white/10 rounded-xl text-sm text-white placeholder:text-white/20 focus:outline-none focus:border-[#E76315]/50 transition-colors";

export default function SponsorJoin() {
  const { code = "" } = useParams();
  const navigate = useNavigate();
  const { joinViaInvite } = useAuth();
  const [form, setForm] = useState({
    name: "", email: "", password: "", company: "", title: "",
    linkedin_url: "", goals: "", target_companies: "",
  });
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const set =
    (k: string) =>
    (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) =>
      setForm({ ...form, [k]: e.target.value });

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    const p = form.password;
    if (p.length < 8 || !/[A-Z]/.test(p) || !/[a-z]/.test(p) || !/\d/.test(p)) {
      setError("Password needs 8+ characters with an uppercase, lowercase, and a number.");
      return;
    }
    let linkedin = form.linkedin_url.trim();
    if (linkedin && !linkedin.startsWith("http")) linkedin = `https://${linkedin}`;
    setSubmitting(true);
    try {
      await joinViaInvite({
        invite_code: code,
        email: form.email.trim().toLowerCase(),
        password: form.password,
        name: form.name.trim(),
        company: form.company.trim(),
        title: form.title.trim(),
        linkedin_url: linkedin || undefined,
        goals: form.goals.trim() || undefined,
        target_companies: form.target_companies.trim() || undefined,
      });
      navigate("/matches");
    } catch (err: any) {
      const detail = err?.response?.data?.detail;
      setError(typeof detail === "string" ? detail : "Something went wrong. Please try again.");
      setSubmitting(false);
    }
  };

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
            Create your profile. Once you save, we'll enrich it and surface your matches.
          </p>
        </div>

        <div className="p-6 rounded-2xl bg-white/[0.03] border border-white/10">
          {error && (
            <div className="mb-4 p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-sm">
              {error}
              {error.toLowerCase().includes("already registered") && (
                <>
                  {" "}
                  <Link to="/login" className="underline">Log in</Link>.
                </>
              )}
            </div>
          )}

          <form onSubmit={onSubmit} className="space-y-4">
            <div>
              <label className="block text-xs text-white/40 uppercase font-medium mb-1.5">Full Name *</label>
              <input
                required
                placeholder="Jane Smith"
                value={form.name}
                onChange={set("name")}
                className={inputCls}
              />
            </div>
            <div>
              <label className="block text-xs text-white/40 uppercase font-medium mb-1.5">Work Email *</label>
              <input
                required
                type="email"
                placeholder="you@company.com"
                value={form.email}
                onChange={set("email")}
                className={inputCls}
              />
            </div>
            <div>
              <label className="block text-xs text-white/40 uppercase font-medium mb-1.5">Password *</label>
              <input
                required
                type="password"
                placeholder="Min. 8 chars · uppercase + number"
                value={form.password}
                onChange={set("password")}
                className={inputCls}
              />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs text-white/40 uppercase font-medium mb-1.5">Company</label>
                <input
                  placeholder="Acme Corp"
                  value={form.company}
                  onChange={set("company")}
                  className={inputCls}
                />
              </div>
              <div>
                <label className="block text-xs text-white/40 uppercase font-medium mb-1.5">Title</label>
                <input
                  placeholder="Head of BD"
                  value={form.title}
                  onChange={set("title")}
                  className={inputCls}
                />
              </div>
            </div>
            <div>
              <label className="block text-xs text-white/40 uppercase font-medium mb-1.5">LinkedIn URL</label>
              <input
                placeholder="linkedin.com/in/yourname"
                value={form.linkedin_url}
                onChange={set("linkedin_url")}
                className={inputCls}
              />
            </div>
            <div>
              <label className="block text-xs text-white/40 uppercase font-medium mb-1.5">
                What do you want to get out of Proof of Talk?
              </label>
              <textarea
                placeholder="e.g. Find DeFi infrastructure partners, close pilot contracts…"
                value={form.goals}
                onChange={set("goals")}
                rows={3}
                className={`${inputCls} resize-none`}
              />
            </div>
            <div>
              <label className="block text-xs text-white/40 uppercase font-medium mb-1.5">Who do you want to meet?</label>
              <textarea
                placeholder="e.g. L2 founders, compliance leads at tier-1 banks…"
                value={form.target_companies}
                onChange={set("target_companies")}
                rows={2}
                className={`${inputCls} resize-none`}
              />
            </div>
            <button
              type="submit"
              disabled={submitting}
              className="w-full flex items-center justify-center gap-2 py-3 min-h-[44px] text-white font-semibold rounded-xl transition-all disabled:opacity-50"
              style={{ background: "var(--pot-orange)" }}
            >
              {submitting ? (
                <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              ) : null}
              {submitting ? "Setting up your matches…" : "Create my profile →"}
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

import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { Save, Plus, X, Linkedin, Twitter, Globe, User } from "lucide-react";
import { useAuth } from "../hooks/useAuth";
import { updateProfile, getAttendee } from "../api/client";
import type { Attendee } from "../types";

const INTEREST_SUGGESTIONS = [
  "DeFi", "RWA", "CBDC", "Layer 2", "Compliance", "Custody",
  "Tokenisation", "Stablecoins", "Web3 Infrastructure", "Regulation",
  "Institutional Crypto", "TradFi-DeFi Bridge", "Settlement",
];

export default function Profile() {
  const { user, refreshUser } = useAuth();
  const navigate = useNavigate();

  const [attendee, setAttendee] = useState<Attendee | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [form, setForm] = useState({
    name: "",
    company: "",
    title: "",
    goals: "",
    linkedin_url: "",
    twitter_handle: "",
    company_website: "",
    interests: [] as string[],
  });

  const [interestInput, setInterestInput] = useState("");

  useEffect(() => {
    if (!user?.attendee_id) {
      setLoading(false);
      return;
    }
    getAttendee(user.attendee_id)
      .then((a) => {
        setAttendee(a);
        setForm({
          name: a.name ?? "",
          company: a.company ?? "",
          title: a.title ?? "",
          goals: a.goals ?? "",
          linkedin_url: a.linkedin_url ?? "",
          twitter_handle: a.twitter_handle ?? "",
          company_website: a.company_website ?? "",
          interests: a.interests ?? [],
        });
      })
      .catch(() => setError("Could not load your profile."))
      .finally(() => setLoading(false));
  }, [user?.attendee_id]);

  const set = (field: keyof typeof form) => (
    e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>
  ) => setForm((f) => ({ ...f, [field]: e.target.value }));

  const addInterest = (tag: string) => {
    const clean = tag.trim();
    if (!clean || form.interests.includes(clean)) return;
    setForm((f) => ({ ...f, interests: [...f.interests, clean] }));
    setInterestInput("");
  };

  const removeInterest = (tag: string) =>
    setForm((f) => ({ ...f, interests: f.interests.filter((i) => i !== tag) }));

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setError(null);
    try {
      await updateProfile(form);
      await refreshUser();
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    } catch (err: unknown) {
      const msg =
        err && typeof err === "object" && "response" in err
          ? (err as { response?: { data?: { detail?: string } } }).response?.data?.detail
          : null;
      setError(msg ?? "Failed to save profile.");
    } finally {
      setSaving(false);
    }
  };

  const initials = (user?.full_name ?? "?")
    .split(" ")
    .map((w) => w[0])
    .join("")
    .toUpperCase()
    .slice(0, 2);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="w-6 h-6 border-2 border-amber-400 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <div className="max-w-2xl mx-auto">
      {/* Header */}
      <div className="flex items-center gap-5 mb-8">
        <div className="w-16 h-16 rounded-full bg-gradient-to-br from-amber-400 to-amber-600 flex items-center justify-center text-black font-bold text-xl shrink-0">
          {initials}
        </div>
        <div>
          <h1 className="text-2xl font-bold">{user?.full_name}</h1>
          <p className="text-white/40 text-sm">{user?.email}</p>
          {user?.is_admin && (
            <span className="mt-1 inline-block text-[10px] font-semibold uppercase tracking-wider px-2 py-0.5 rounded-full bg-amber-400/20 text-amber-400">
              Admin
            </span>
          )}
        </div>
      </div>

      {!user?.attendee_id && (
        <div className="mb-6 p-4 rounded-xl border border-white/10 bg-white/5 text-white/50 text-sm flex items-center gap-3">
          <User className="w-4 h-4 shrink-0" />
          No attendee profile linked to this account.
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Basic info */}
        <section className="rounded-xl border border-white/10 bg-white/[0.03] p-6 space-y-4">
          <h2 className="text-sm font-semibold text-white/60 uppercase tracking-wider">Basic Info</h2>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="space-y-1">
              <label className="text-xs text-white/50">Full name</label>
              <input
                value={form.name}
                onChange={set("name")}
                placeholder="Your name"
                className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm text-white placeholder-white/20 focus:outline-none focus:border-amber-400/50"
              />
            </div>
            <div className="space-y-1">
              <label className="text-xs text-white/50">Company</label>
              <input
                value={form.company}
                onChange={set("company")}
                placeholder="Your company"
                className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm text-white placeholder-white/20 focus:outline-none focus:border-amber-400/50"
              />
            </div>
            <div className="sm:col-span-2 space-y-1">
              <label className="text-xs text-white/50">Title</label>
              <input
                value={form.title}
                onChange={set("title")}
                placeholder="Your role / title"
                className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm text-white placeholder-white/20 focus:outline-none focus:border-amber-400/50"
              />
            </div>
          </div>

          <div className="space-y-1">
            <label className="text-xs text-white/50">Goals at POT 2026</label>
            <textarea
              value={form.goals}
              onChange={set("goals")}
              rows={3}
              placeholder="What are you hoping to achieve at Proof of Talk?"
              className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm text-white placeholder-white/20 focus:outline-none focus:border-amber-400/50 resize-none"
            />
          </div>
        </section>

        {/* Interests */}
        <section className="rounded-xl border border-white/10 bg-white/[0.03] p-6 space-y-4">
          <h2 className="text-sm font-semibold text-white/60 uppercase tracking-wider">Interests</h2>

          <div className="flex flex-wrap gap-2">
            {form.interests.map((tag) => (
              <span
                key={tag}
                className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-amber-400/15 text-amber-400 text-xs font-medium"
              >
                {tag}
                <button type="button" onClick={() => removeInterest(tag)} className="hover:text-white">
                  <X className="w-3 h-3" />
                </button>
              </span>
            ))}
            {form.interests.length === 0 && (
              <span className="text-white/20 text-xs">No interests added yet</span>
            )}
          </div>

          {/* Suggestions */}
          <div className="flex flex-wrap gap-1.5">
            {INTEREST_SUGGESTIONS.filter((s) => !form.interests.includes(s)).map((s) => (
              <button
                key={s}
                type="button"
                onClick={() => addInterest(s)}
                className="px-2 py-0.5 rounded-full border border-white/10 text-white/40 text-xs hover:border-amber-400/40 hover:text-amber-400 transition-all"
              >
                + {s}
              </button>
            ))}
          </div>

          {/* Custom input */}
          <div className="flex gap-2">
            <input
              value={interestInput}
              onChange={(e) => setInterestInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") { e.preventDefault(); addInterest(interestInput); }
              }}
              placeholder="Add custom interest…"
              className="flex-1 bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm text-white placeholder-white/20 focus:outline-none focus:border-amber-400/50"
            />
            <button
              type="button"
              onClick={() => addInterest(interestInput)}
              className="px-3 py-2 rounded-lg bg-white/5 border border-white/10 text-white/50 hover:text-white hover:border-white/20 transition-all"
            >
              <Plus className="w-4 h-4" />
            </button>
          </div>
        </section>

        {/* Social / web */}
        <section className="rounded-xl border border-white/10 bg-white/[0.03] p-6 space-y-4">
          <h2 className="text-sm font-semibold text-white/60 uppercase tracking-wider">Online Presence</h2>

          <div className="space-y-3">
            <div className="flex items-center gap-3">
              <Linkedin className="w-4 h-4 text-white/30 shrink-0" />
              <input
                value={form.linkedin_url}
                onChange={set("linkedin_url")}
                placeholder="https://linkedin.com/in/yourhandle"
                className="flex-1 bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm text-white placeholder-white/20 focus:outline-none focus:border-amber-400/50"
              />
            </div>
            <div className="flex items-center gap-3">
              <Twitter className="w-4 h-4 text-white/30 shrink-0" />
              <input
                value={form.twitter_handle}
                onChange={set("twitter_handle")}
                placeholder="@handle"
                className="flex-1 bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm text-white placeholder-white/20 focus:outline-none focus:border-amber-400/50"
              />
            </div>
            <div className="flex items-center gap-3">
              <Globe className="w-4 h-4 text-white/30 shrink-0" />
              <input
                value={form.company_website}
                onChange={set("company_website")}
                placeholder="https://yourcompany.com"
                className="flex-1 bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm text-white placeholder-white/20 focus:outline-none focus:border-amber-400/50"
              />
            </div>
          </div>
        </section>

        {/* AI context */}
        {attendee?.ai_summary && (
          <section className="rounded-xl border border-white/10 bg-white/[0.03] p-6 space-y-2">
            <h2 className="text-sm font-semibold text-white/60 uppercase tracking-wider">AI Summary</h2>
            <p className="text-sm text-white/50 leading-relaxed">{attendee.ai_summary}</p>
            <p className="text-[11px] text-white/20">Auto-generated · updates after each enrichment run</p>
          </section>
        )}

        {/* Actions */}
        {error && (
          <p className="text-sm text-red-400 bg-red-400/10 border border-red-400/20 rounded-lg px-4 py-3">{error}</p>
        )}
        {saved && (
          <p className="text-sm text-emerald-400 bg-emerald-400/10 border border-emerald-400/20 rounded-lg px-4 py-3">
            Profile saved successfully.
          </p>
        )}

        <div className="flex items-center gap-3">
          <button
            type="submit"
            disabled={saving || !user?.attendee_id}
            className="flex items-center gap-2 px-5 py-2.5 rounded-lg bg-amber-400 text-black text-sm font-semibold hover:bg-amber-300 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
          >
            <Save className="w-4 h-4" />
            {saving ? "Saving…" : "Save changes"}
          </button>
          <button
            type="button"
            onClick={() => navigate(-1)}
            className="px-5 py-2.5 rounded-lg border border-white/10 text-white/50 text-sm hover:text-white hover:border-white/20 transition-all"
          >
            Cancel
          </button>
        </div>
      </form>
    </div>
  );
}

import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Sparkles, Eye, EyeOff, LogIn, Mail } from "lucide-react";
import { useAuth } from "../hooks/useAuth";
import { forgotPassword } from "../api/client";

export default function Login() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPw, setShowPw] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [setupLoading, setSetupLoading] = useState(false);
  const [setupSent, setSetupSent] = useState(false);

  const sendSetupLink = async () => {
    if (!email.trim()) {
      setError("Enter your email above first, then tap to get a setup link.");
      return;
    }
    setSetupLoading(true);
    try {
      await forgotPassword(email);
    } catch {
      // fall through — always show the generic confirmation (no enumeration)
    } finally {
      setSetupLoading(false);
      setError(null); // clear the login error so we don't show red + green at once
      setSetupSent(true);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      await login(email, password);
      navigate("/attendees");
    } catch {
      setError("Invalid email or password. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-[70vh] flex items-center justify-center">
      <div className="w-full max-w-md">
        {/* Logo */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-gradient-to-br from-[#E76315] to-[#D35400] mb-4">
            <Sparkles className="w-7 h-7 text-black" />
          </div>
          <h1 className="text-2xl font-bold">Welcome back</h1>
          <p className="text-white/40 text-sm mt-1">Sign in to your POT Matchmaker account</p>
        </div>

        <form
          onSubmit={handleSubmit}
          className="p-6 rounded-2xl bg-white/[0.03] border border-white/10 space-y-4"
        >
          {error && (
            <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-sm">
              {error}
            </div>
          )}

          {error && !setupSent && (
            <div className="space-y-2">
              <p className="text-xs text-white/50 text-center">
                First time here, or haven't set a password yet?
              </p>
              <button
                type="button"
                onClick={sendSetupLink}
                disabled={setupLoading}
                className="w-full flex items-center justify-center gap-2 py-2.5 bg-white/5 border border-white/10 text-white/80 text-sm font-medium rounded-xl hover:bg-white/10 hover:border-[#E76315]/40 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {setupLoading ? (
                  <div className="w-4 h-4 border-2 border-white/30 border-t-white/80 rounded-full animate-spin" />
                ) : (
                  <Mail className="w-4 h-4 text-[#E76315]" />
                )}
                {setupLoading ? "Sending…" : "Email me a setup link"}
              </button>
            </div>
          )}

          {setupSent && (
            <div className="p-3 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-sm">
              If your email is in our system, we've sent a link to set your password. Check your inbox (and spam).
            </div>
          )}

          <div>
            <label className="block text-xs text-white/40 uppercase font-medium mb-1.5">
              Email
            </label>
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@company.com"
              className="w-full px-4 py-2.5 bg-white/5 border border-white/10 rounded-xl text-sm text-white placeholder:text-white/20 focus:outline-none focus:border-[#E76315]/50"
            />
          </div>

          <div>
            <label className="block text-xs text-white/40 uppercase font-medium mb-1.5">
              Password
            </label>
            <div className="relative">
              <input
                type={showPw ? "text" : "password"}
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                className="w-full px-4 py-2.5 pr-10 bg-white/5 border border-white/10 rounded-xl text-sm text-white placeholder:text-white/20 focus:outline-none focus:border-[#E76315]/50"
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

          <div className="text-right">
            <Link to="/forgot-password" className="text-xs text-[#E76315] hover:text-[#FF833A]">
              Forgot password?
            </Link>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full flex items-center justify-center gap-2 py-3 bg-[#E76315] text-black font-semibold rounded-xl hover:bg-[#FF833A] transition-all disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? (
              <div className="w-4 h-4 border-2 border-black/30 border-t-black rounded-full animate-spin" />
            ) : (
              <LogIn className="w-4 h-4" />
            )}
            {loading ? "Signing in…" : "Sign In"}
          </button>
        </form>

        <p className="text-center text-sm text-white/40 mt-4">
          Don't have an account?{" "}
          <Link to="/register" className="text-[#E76315] hover:text-[#FF833A]">
            Register here
          </Link>
        </p>
      </div>
    </div>
  );
}

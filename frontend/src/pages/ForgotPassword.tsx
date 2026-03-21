import { useState } from "react";
import { Link } from "react-router-dom";
import { Sparkles, Mail } from "lucide-react";
import { forgotPassword } from "../api/client";

export default function ForgotPassword() {
  const [email, setEmail] = useState("");
  const [loading, setLoading] = useState(false);
  const [sent, setSent] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      await forgotPassword(email);
      setSent(true);
    } catch {
      setError("Something went wrong. Please try again.");
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
          <h1 className="text-2xl font-bold">Reset your password</h1>
          <p className="text-white/40 text-sm mt-1">
            Enter your email and we'll send you a reset link
          </p>
        </div>

        {sent ? (
          <div className="p-6 rounded-2xl bg-white/[0.03] border border-white/10 text-center">
            <div className="inline-flex items-center justify-center w-12 h-12 rounded-full bg-[#E76315]/10 mb-4">
              <Mail className="w-6 h-6 text-[#E76315]" />
            </div>
            <h2 className="text-lg font-semibold mb-2">Check your email</h2>
            <p className="text-white/50 text-sm mb-6">
              If an account exists for <span className="text-white">{email}</span>,
              you'll receive a password reset link shortly.
            </p>
            <Link
              to="/login"
              className="text-[#E76315] hover:text-[#FF833A] text-sm font-medium"
            >
              Back to login
            </Link>
          </div>
        ) : (
          <form
            onSubmit={handleSubmit}
            className="p-6 rounded-2xl bg-white/[0.03] border border-white/10 space-y-4"
          >
            {error && (
              <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-sm">
                {error}
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

            <button
              type="submit"
              disabled={loading}
              className="w-full flex items-center justify-center gap-2 py-3 bg-[#E76315] text-black font-semibold rounded-xl hover:bg-[#FF833A] transition-all disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? (
                <div className="w-4 h-4 border-2 border-black/30 border-t-black rounded-full animate-spin" />
              ) : (
                <Mail className="w-4 h-4" />
              )}
              {loading ? "Sending..." : "Send Reset Link"}
            </button>
          </form>
        )}

        <p className="text-center text-sm text-white/40 mt-4">
          Remember your password?{" "}
          <Link to="/login" className="text-[#E76315] hover:text-[#FF833A]">
            Sign in
          </Link>
        </p>
      </div>
    </div>
  );
}

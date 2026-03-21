import { useState, useEffect } from "react";
import { Link, useSearchParams, useNavigate } from "react-router-dom";
import { Sparkles, Eye, EyeOff, Lock, CheckCircle, AlertTriangle } from "lucide-react";
import { resetPassword } from "../api/client";

export default function ResetPassword() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const token = searchParams.get("token") || "";

  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [showPw, setShowPw] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Password validation
  const hasLength = password.length >= 8;
  const hasUpper = /[A-Z]/.test(password);
  const hasLower = /[a-z]/.test(password);
  const hasDigit = /\d/.test(password);
  const passwordsMatch = password === confirm && confirm.length > 0;
  const isValid = hasLength && hasUpper && hasLower && hasDigit && passwordsMatch;

  // Auto-redirect after success
  useEffect(() => {
    if (success) {
      const timer = setTimeout(() => navigate("/login"), 3000);
      return () => clearTimeout(timer);
    }
  }, [success, navigate]);

  if (!token) {
    return (
      <div className="min-h-[70vh] flex items-center justify-center">
        <div className="w-full max-w-md text-center">
          <div className="inline-flex items-center justify-center w-12 h-12 rounded-full bg-red-500/10 mb-4">
            <AlertTriangle className="w-6 h-6 text-red-400" />
          </div>
          <h1 className="text-xl font-bold mb-2">Invalid reset link</h1>
          <p className="text-white/50 text-sm mb-6">
            This link is missing a reset token. Please request a new one.
          </p>
          <Link
            to="/forgot-password"
            className="text-[#E76315] hover:text-[#FF833A] text-sm font-medium"
          >
            Request a new reset link
          </Link>
        </div>
      </div>
    );
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!isValid) return;
    setLoading(true);
    setError(null);
    try {
      await resetPassword(token, password);
      setSuccess(true);
    } catch (err: unknown) {
      const msg =
        err && typeof err === "object" && "response" in err
          ? (err as { response?: { data?: { detail?: string } } }).response?.data?.detail
          : undefined;
      setError(msg || "Reset link is invalid or has expired. Please request a new one.");
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
          <h1 className="text-2xl font-bold">Set new password</h1>
          <p className="text-white/40 text-sm mt-1">Choose a strong password for your account</p>
        </div>

        {success ? (
          <div className="p-6 rounded-2xl bg-white/[0.03] border border-white/10 text-center">
            <div className="inline-flex items-center justify-center w-12 h-12 rounded-full bg-green-500/10 mb-4">
              <CheckCircle className="w-6 h-6 text-green-400" />
            </div>
            <h2 className="text-lg font-semibold mb-2">Password updated</h2>
            <p className="text-white/50 text-sm">
              Redirecting you to login...
            </p>
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
                New Password
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

            <div>
              <label className="block text-xs text-white/40 uppercase font-medium mb-1.5">
                Confirm Password
              </label>
              <div className="relative">
                <input
                  type={showConfirm ? "text" : "password"}
                  required
                  value={confirm}
                  onChange={(e) => setConfirm(e.target.value)}
                  placeholder="••••••••"
                  className="w-full px-4 py-2.5 pr-10 bg-white/5 border border-white/10 rounded-xl text-sm text-white placeholder:text-white/20 focus:outline-none focus:border-[#E76315]/50"
                />
                <button
                  type="button"
                  onClick={() => setShowConfirm((v) => !v)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-white/30 hover:text-white/60"
                >
                  {showConfirm ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
            </div>

            {/* Password requirements */}
            {password.length > 0 && (
              <div className="space-y-1 text-xs">
                <div className={hasLength ? "text-green-400" : "text-white/30"}>
                  {hasLength ? "✓" : "○"} At least 8 characters
                </div>
                <div className={hasUpper ? "text-green-400" : "text-white/30"}>
                  {hasUpper ? "✓" : "○"} One uppercase letter
                </div>
                <div className={hasLower ? "text-green-400" : "text-white/30"}>
                  {hasLower ? "✓" : "○"} One lowercase letter
                </div>
                <div className={hasDigit ? "text-green-400" : "text-white/30"}>
                  {hasDigit ? "✓" : "○"} One digit
                </div>
                {confirm.length > 0 && (
                  <div className={passwordsMatch ? "text-green-400" : "text-red-400"}>
                    {passwordsMatch ? "✓" : "✗"} Passwords match
                  </div>
                )}
              </div>
            )}

            <button
              type="submit"
              disabled={loading || !isValid}
              className="w-full flex items-center justify-center gap-2 py-3 bg-[#E76315] text-black font-semibold rounded-xl hover:bg-[#FF833A] transition-all disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? (
                <div className="w-4 h-4 border-2 border-black/30 border-t-black rounded-full animate-spin" />
              ) : (
                <Lock className="w-4 h-4" />
              )}
              {loading ? "Updating..." : "Update Password"}
            </button>
          </form>
        )}

        <p className="text-center text-sm text-white/40 mt-4">
          <Link to="/login" className="text-[#E76315] hover:text-[#FF833A]">
            Back to login
          </Link>
        </p>
      </div>
    </div>
  );
}

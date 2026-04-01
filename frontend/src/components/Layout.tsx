import { Link, useLocation } from "react-router-dom";
import { Users, Sparkles, BarChart3, LogIn, LogOut, UserPlus, UserCog, Heart, MessageSquare, MessageCircle } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { getPendingMatchCount } from "../api/client";
import { useAuth } from "../hooks/useAuth";
import ChatWidget from "./chat/ChatWidget";

export default function Layout({ children }: { children: React.ReactNode }) {
  const location = useLocation();
  const { user, isAuthenticated, logout } = useAuth();
  const { data: pendingData } = useQuery({
    queryKey: ["pending-match-count"],
    queryFn: getPendingMatchCount,
    enabled: isAuthenticated && !user?.is_admin,
    staleTime: 15_000,
    refetchInterval: 30_000,
  });
  const pendingCount = pendingData?.pending_count ?? 0;

  const isActive = (to: string) =>
    to === "/" ? location.pathname === to : location.pathname.startsWith(to);

  const linkCls = (to: string) =>
    `px-3 py-2 rounded-lg text-sm font-medium transition-all flex items-center gap-2 min-h-[44px] ${
      isActive(to)
        ? "bg-white/10 text-[#E76315]"
        : "text-white/60 hover:text-white hover:bg-white/5 active:bg-white/10"
    }`;

  return (
    <div className="min-h-screen bg-[#121212] text-white pb-16 sm:pb-0">
      {/* Top nav */}
      <header className="border-b border-white/10 bg-[#121212]/80 backdrop-blur-xl sticky top-0 z-40">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 h-16 flex items-center justify-between gap-4">
          <Link to={isAuthenticated ? "/matches" : "/"} className="flex items-center gap-3 shrink-0">
            {/* POT logo mark */}
            <div
              className="w-7 h-9 bg-[#E76315] shrink-0"
              style={{ clipPath: "polygon(0 0, 100% 8%, 100% 92%, 0 100%)" }}
            />
            <span className="font-semibold text-lg tracking-tight hidden sm:block">
              Proof of Talk
            </span>
          </Link>

          {/* Desktop nav */}
          <nav className="hidden sm:flex items-center gap-1">
            {!isAuthenticated && (
              <Link to="/" className={linkCls("/")}>
                <Sparkles className="w-4 h-4" />
                <span>Home</span>
              </Link>
            )}
            {user?.is_admin && (
              <Link to="/attendees" className={linkCls("/attendees")}>
                <Users className="w-4 h-4" />
                <span>Attendees</span>
              </Link>
            )}
            {user?.is_admin && (
              <Link to="/dashboard" className={linkCls("/dashboard")}>
                <BarChart3 className="w-4 h-4" />
                <span>Dashboard</span>
              </Link>
            )}
            {isAuthenticated && (
              <Link to="/matches" className={`${linkCls("/matches")} relative`}>
                <Heart className="w-4 h-4" />
                <span>My Matches</span>
                {pendingCount > 0 && (
                  <span className="absolute -top-1.5 -right-2.5 min-w-[18px] h-[18px] flex items-center justify-center rounded-full bg-[#E76315] text-white text-[10px] font-bold px-1">
                    {pendingCount}
                  </span>
                )}
              </Link>
            )}
            {isAuthenticated && !user?.is_admin && (
              <Link to="/messages" className={linkCls("/messages")}>
                <MessageSquare className="w-4 h-4" />
                <span>Messages</span>
              </Link>
            )}
            {isAuthenticated && (
              <Link to="/threads" className={linkCls("/threads")}>
                <MessageCircle className="w-4 h-4" />
                <span>Threads</span>
              </Link>
            )}
          </nav>

          {/* Auth section */}
          <div className="flex items-center gap-2 shrink-0">
            {isAuthenticated ? (
              <>
                <Link to="/profile" className="hidden sm:flex flex-col text-right hover:opacity-80 transition-opacity">
                  <span className="text-xs font-medium text-white/80">{user?.full_name}</span>
                  <span className="text-[10px] text-white/30">{user?.is_admin ? "Admin" : "Attendee"}</span>
                </Link>
                <Link
                  to="/profile"
                  className={`p-2 rounded-lg border border-white/10 text-white/50 hover:text-[#E76315] hover:border-amber-400/30 transition-all min-h-[44px] min-w-[44px] flex items-center justify-center ${
                    location.pathname === "/profile" ? "text-[#E76315] border-amber-400/30 bg-[#E76315]/10" : ""
                  }`}
                  title="Edit profile"
                >
                  <UserCog className="w-4 h-4" />
                </Link>
                <button
                  onClick={logout}
                  className="hidden sm:flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-white/10 text-white/50 text-xs hover:text-white/80 hover:border-white/20 transition-all min-h-[44px]"
                >
                  <LogOut className="w-3.5 h-3.5" />
                  <span>Sign out</span>
                </button>
              </>
            ) : (
              <>
                <Link
                  to="/login"
                  className="flex items-center gap-1.5 px-3 py-2 rounded-lg text-white/50 text-xs hover:text-white/80 hover:bg-white/5 transition-all min-h-[44px]"
                >
                  <LogIn className="w-3.5 h-3.5" />
                  <span className="hidden sm:inline">Sign in</span>
                </Link>
                <Link
                  to="/register"
                  className="flex items-center gap-1.5 px-3 py-2 rounded-lg bg-[#E76315] text-black text-xs font-semibold hover:bg-amber-300 transition-all min-h-[44px]"
                >
                  <UserPlus className="w-3.5 h-3.5" />
                  <span className="hidden sm:inline">Register</span>
                </Link>
              </>
            )}
          </div>
        </div>
      </header>

      {/* Main content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 py-6 sm:py-8">{children}</main>

      {/* Footer — desktop only */}
      <footer className="hidden sm:block border-t border-white/10 mt-auto">
        <div className="max-w-7xl mx-auto px-6 py-6 flex items-center justify-between text-sm text-white/40">
          <span>Proof of Talk 2026 &middot; Louvre Palace, Paris</span>
          <span>XVentures Labs</span>
        </div>
      </footer>

      {/* Mobile bottom tab bar */}
      <nav className="sm:hidden fixed bottom-0 left-0 right-0 z-40 bg-[#121212]/95 backdrop-blur-xl border-t border-white/10 flex items-stretch">
        {isAuthenticated ? (
          <>
            <Link
              to="/matches"
              className={`flex-1 flex flex-col items-center justify-center gap-1 py-3 text-[10px] font-medium transition-all relative ${
                isActive("/matches") ? "text-[#E76315]" : "text-white/40 active:text-white/70"
              }`}
            >
              <Heart className="w-5 h-5" />
              My Matches
              {pendingCount > 0 && (
                <span className="absolute top-1 right-1/4 min-w-[16px] h-[16px] flex items-center justify-center rounded-full bg-[#E76315] text-white text-[9px] font-bold px-0.5">
                  {pendingCount}
                </span>
              )}
            </Link>
            <Link
              to="/threads"
              className={`flex-1 flex flex-col items-center justify-center gap-1 py-3 text-[10px] font-medium transition-all ${
                isActive("/threads") ? "text-[#E76315]" : "text-white/40 active:text-white/70"
              }`}
            >
              <MessageCircle className="w-5 h-5" />
              Threads
            </Link>
            {user?.is_admin ? (
              <Link
                to="/dashboard"
                className={`flex-1 flex flex-col items-center justify-center gap-1 py-3 text-[10px] font-medium transition-all ${
                  isActive("/dashboard") ? "text-[#E76315]" : "text-white/40 active:text-white/70"
                }`}
              >
                <BarChart3 className="w-5 h-5" />
                Dashboard
              </Link>
            ) : (
              <Link
                to="/messages"
                className={`flex-1 flex flex-col items-center justify-center gap-1 py-3 text-[10px] font-medium transition-all ${
                  isActive("/messages") ? "text-[#E76315]" : "text-white/40 active:text-white/70"
                }`}
              >
                <MessageSquare className="w-5 h-5" />
                Messages
              </Link>
            )}
            <button
              onClick={logout}
              className="flex-1 flex flex-col items-center justify-center gap-1 py-3 text-[10px] font-medium text-white/40 active:text-white/70 transition-all"
            >
              <LogOut className="w-5 h-5" />
              Sign out
            </button>
          </>
        ) : (
          <>
            <Link
              to="/"
              className={`flex-1 flex flex-col items-center justify-center gap-1 py-3 text-[10px] font-medium transition-all ${
                isActive("/") ? "text-[#E76315]" : "text-white/40 active:text-white/70"
              }`}
            >
              <Sparkles className="w-5 h-5" />
              Home
            </Link>
            <Link
              to="/login"
              className={`flex-1 flex flex-col items-center justify-center gap-1 py-3 text-[10px] font-medium transition-all ${
                isActive("/login") ? "text-[#E76315]" : "text-white/40 active:text-white/70"
              }`}
            >
              <LogIn className="w-5 h-5" />
              Sign in
            </Link>
            <Link
              to="/register"
              className="flex-1 flex flex-col items-center justify-center gap-1 py-3 text-[10px] font-medium text-[#E76315] active:text-amber-300 transition-all"
            >
              <UserPlus className="w-5 h-5" />
              Register
            </Link>
          </>
        )}
      </nav>

      {/* Floating AI Concierge */}
      <ChatWidget />
    </div>
  );
}

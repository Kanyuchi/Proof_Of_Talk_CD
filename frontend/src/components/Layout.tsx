import { Link, useLocation } from "react-router-dom";
import { Users, Sparkles, BarChart3, MessageSquare, LogIn, LogOut, UserPlus, UserCog } from "lucide-react";
import { useAuth } from "../hooks/useAuth";
import { useUnreadCount } from "../hooks/useMessages";
import ChatWidget from "./chat/ChatWidget";

const navItems = [
  { to: "/", label: "Home", icon: Sparkles },
  { to: "/attendees", label: "Attendees", icon: Users },
  { to: "/dashboard", label: "Dashboard", icon: BarChart3 },
];

function UnreadBadge() {
  const { data } = useUnreadCount();
  const count = data?.unread_count ?? 0;
  if (count === 0) return null;
  return (
    <span className="absolute -top-1 -right-1 w-4 h-4 rounded-full bg-amber-400 text-black text-[9px] font-bold flex items-center justify-center">
      {count > 9 ? "9+" : count}
    </span>
  );
}

export default function Layout({ children }: { children: React.ReactNode }) {
  const location = useLocation();
  const { user, isAuthenticated, logout } = useAuth();

  return (
    <div className="min-h-screen bg-[#0a0a0f] text-white">
      {/* Top nav */}
      <header className="border-b border-white/10 bg-[#0a0a0f]/80 backdrop-blur-xl sticky top-0 z-40">
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between gap-4">
          <Link to="/" className="flex items-center gap-3 shrink-0">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-amber-400 to-amber-600 flex items-center justify-center">
              <Sparkles className="w-4 h-4 text-black" />
            </div>
            <span className="font-semibold text-lg tracking-tight">
              POT <span className="text-amber-400">Matchmaker</span>
            </span>
          </Link>

          <nav className="flex items-center gap-1">
            {navItems.map(({ to, label, icon: Icon }) => {
              const active = location.pathname === to || (to !== "/" && location.pathname.startsWith(to));
              return (
                <Link
                  key={to}
                  to={to}
                  className={`px-3 py-2 rounded-lg text-sm font-medium transition-all flex items-center gap-2 ${
                    active
                      ? "bg-white/10 text-amber-400"
                      : "text-white/60 hover:text-white hover:bg-white/5"
                  }`}
                >
                  <Icon className="w-4 h-4" />
                  <span className="hidden sm:inline">{label}</span>
                </Link>
              );
            })}

            {/* Messages (only when logged in) */}
            {isAuthenticated && (
              <Link
                to="/messages"
                className={`relative px-3 py-2 rounded-lg text-sm font-medium transition-all flex items-center gap-2 ${
                  location.pathname.startsWith("/messages")
                    ? "bg-white/10 text-amber-400"
                    : "text-white/60 hover:text-white hover:bg-white/5"
                }`}
              >
                <MessageSquare className="w-4 h-4" />
                <UnreadBadge />
                <span className="hidden sm:inline">Messages</span>
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
                  className={`p-1.5 rounded-lg border border-white/10 text-white/50 hover:text-amber-400 hover:border-amber-400/30 transition-all ${
                    location.pathname === "/profile" ? "text-amber-400 border-amber-400/30 bg-amber-400/10" : ""
                  }`}
                  title="Edit profile"
                >
                  <UserCog className="w-3.5 h-3.5" />
                </Link>
                <button
                  onClick={logout}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-white/10 text-white/50 text-xs hover:text-white/80 hover:border-white/20 transition-all"
                >
                  <LogOut className="w-3.5 h-3.5" />
                  <span className="hidden sm:inline">Sign out</span>
                </button>
              </>
            ) : (
              <>
                <Link
                  to="/login"
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-white/50 text-xs hover:text-white/80 hover:bg-white/5 transition-all"
                >
                  <LogIn className="w-3.5 h-3.5" />
                  <span className="hidden sm:inline">Sign in</span>
                </Link>
                <Link
                  to="/register"
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-amber-400 text-black text-xs font-semibold hover:bg-amber-300 transition-all"
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
      <main className="max-w-7xl mx-auto px-6 py-8">{children}</main>

      {/* Footer */}
      <footer className="border-t border-white/10 mt-auto">
        <div className="max-w-7xl mx-auto px-6 py-6 flex items-center justify-between text-sm text-white/40">
          <span>Proof of Talk 2026 &middot; Louvre Palace, Paris</span>
          <span>XVentures Labs</span>
        </div>
      </footer>

      {/* Floating AI Concierge */}
      <ChatWidget />
    </div>
  );
}

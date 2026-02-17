import { Link, useLocation } from "react-router-dom";
import { Users, Sparkles, BarChart3 } from "lucide-react";

const navItems = [
  { to: "/", label: "Home", icon: Sparkles },
  { to: "/attendees", label: "Attendees", icon: Users },
  { to: "/dashboard", label: "Dashboard", icon: BarChart3 },
];

export default function Layout({ children }: { children: React.ReactNode }) {
  const location = useLocation();

  return (
    <div className="min-h-screen bg-[#0a0a0f] text-white">
      {/* Top nav */}
      <header className="border-b border-white/10 bg-[#0a0a0f]/80 backdrop-blur-xl sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          <Link to="/" className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-amber-400 to-amber-600 flex items-center justify-center">
              <Sparkles className="w-4 h-4 text-black" />
            </div>
            <span className="font-semibold text-lg tracking-tight">
              POT <span className="text-amber-400">Matchmaker</span>
            </span>
          </Link>

          <nav className="flex items-center gap-1">
            {navItems.map(({ to, label, icon: Icon }) => {
              const active = location.pathname === to;
              return (
                <Link
                  key={to}
                  to={to}
                  className={`px-4 py-2 rounded-lg text-sm font-medium transition-all flex items-center gap-2 ${
                    active
                      ? "bg-white/10 text-amber-400"
                      : "text-white/60 hover:text-white hover:bg-white/5"
                  }`}
                >
                  <Icon className="w-4 h-4" />
                  {label}
                </Link>
              );
            })}
          </nav>
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
    </div>
  );
}

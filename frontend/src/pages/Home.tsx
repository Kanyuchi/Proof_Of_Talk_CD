import { Link } from "react-router-dom";
import { ArrowRight, Brain, Zap, Users } from "lucide-react";
import { useAuth } from "../hooks/useAuth";

export default function Home() {
  const { isAuthenticated } = useAuth();

  return (
    <div className="space-y-20">
      {/* Hero */}
      <section className="text-center pt-16 pb-8">
        <div className="pot-badge-orange mb-8">
          Private Matchmaking · Proof of Talk 2026
        </div>

        <h1
          className="text-5xl md:text-7xl tracking-tight leading-[1.1] mb-6 text-white font-normal"
          style={{ fontFamily: "var(--font-heading)" }}
        >
          Tell us what you need.
          <br />
          <span style={{ color: "var(--pot-orange)" }}>
            We'll tell you who to meet.
          </span>
        </h1>

        <p className="text-lg text-white/50 max-w-2xl mx-auto mb-10 leading-relaxed" style={{ fontFamily: "var(--font-body)" }}>
          2,500 decision-makers. $18 trillion in assets. Two days at the Louvre Palace.
          Our AI finds the five conversations most likely to matter — before you walk through the door.
        </p>

        <div className="flex items-center justify-center gap-4 flex-wrap">
          {isAuthenticated ? (
            <>
              <Link
                to="/matches"
                className="inline-flex items-center gap-2 px-6 py-3 rounded-xl font-semibold text-white transition-all min-h-[44px]"
                style={{ background: "var(--pot-orange)" }}
              >
                View your matches
                <ArrowRight className="w-4 h-4" />
              </Link>
              <Link
                to="/profile"
                className="inline-flex items-center gap-2 px-6 py-3 bg-white/5 text-white font-semibold rounded-xl border border-white/10 hover:bg-white/10 transition-all min-h-[44px]"
              >
                Edit your profile
              </Link>
            </>
          ) : (
            <>
              <Link
                to="/register"
                className="inline-flex items-center gap-2 px-6 py-3 rounded-xl font-semibold text-white transition-all min-h-[44px]"
                style={{ background: "var(--pot-orange)" }}
              >
                Get your introductions
                <ArrowRight className="w-4 h-4" />
              </Link>
              <Link
                to="/login"
                className="inline-flex items-center gap-2 px-6 py-3 bg-white/5 text-white font-semibold rounded-xl border border-white/10 hover:bg-white/10 transition-all min-h-[44px]"
              >
                Sign in to view matches
              </Link>
            </>
          )}
        </div>
      </section>

      {/* How it works */}
      <section>
        <h2
          className="text-center text-2xl mb-12 text-white/80 font-normal"
          style={{ fontFamily: "var(--font-heading)" }}
        >
          How the Engine Works
        </h2>
        <div className="grid md:grid-cols-3 gap-6">
          {[
            {
              icon: Users,
              title: "Multi-Source Intelligence",
              description:
                "We go beyond your registration form — pulling from LinkedIn, company pages, and public data to understand what you're really building and what you actually need.",
              color: "from-blue-500 to-blue-600",
            },
            {
              icon: Brain,
              title: "AI Matching Pipeline",
              description:
                "Our AI doesn't just match keywords. It finds the people whose goals complement yours — the investor who fits your thesis, the builder who solves your problem, the partner you didn't know you needed.",
              color: "from-[#E76315] to-[#D35400]",
            },
            {
              icon: Zap,
              title: "Private Briefing Dossier",
              description:
                "Each recommendation comes with a personalised brief: why this person matters to you, what you have in common, and how to start the conversation.",
              color: "from-emerald-400 to-emerald-600",
            },
          ].map(({ icon: Icon, title, description, color }) => (
            <div
              key={title}
              className="p-6 rounded-2xl bg-white/[0.03] border border-white/10 hover:border-white/20 transition-all"
            >
              <div
                className={`w-10 h-10 rounded-xl bg-gradient-to-br ${color} flex items-center justify-center mb-4`}
              >
                <Icon className="w-5 h-5 text-white" />
              </div>
              <h3 className="text-lg font-semibold mb-2" style={{ fontFamily: "var(--font-heading)" }}>{title}</h3>
              <p className="text-white/50 text-sm leading-relaxed">{description}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Stats bar */}
      <section className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[
          { label: "Decision Makers", value: "2,500" },
          { label: "Assets Under Mgmt", value: "$18T" },
          { label: "C-Suite Attendees", value: "85%" },
          { label: "Event", value: "June 2–3, 2026" },
        ].map(({ label, value }) => (
          <div
            key={label}
            className="text-center p-5 rounded-xl bg-white/[0.03] border border-white/10"
          >
            <div className="text-2xl font-bold" style={{ color: "var(--pot-orange)", fontFamily: "var(--font-heading)" }}>{value}</div>
            <div className="text-sm text-white/40 mt-1">{label}</div>
          </div>
        ))}
      </section>
    </div>
  );
}

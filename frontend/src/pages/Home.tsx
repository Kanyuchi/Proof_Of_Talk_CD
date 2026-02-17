import { Link } from "react-router-dom";
import { ArrowRight, Sparkles, Users, Brain, Zap } from "lucide-react";

export default function Home() {
  return (
    <div className="space-y-20">
      {/* Hero */}
      <section className="text-center pt-16 pb-8">
        <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-amber-400/10 text-amber-400 text-sm font-medium mb-8 border border-amber-400/20">
          <Sparkles className="w-3.5 h-3.5" />
          AI-Powered Matchmaking Engine
        </div>

        <h1 className="text-5xl md:text-7xl font-bold tracking-tight leading-[1.1] mb-6">
          <span className="text-white">The Right Meeting</span>
          <br />
          <span className="bg-gradient-to-r from-amber-400 to-amber-200 bg-clip-text text-transparent">
            Changes Everything
          </span>
        </h1>

        <p className="text-lg text-white/50 max-w-2xl mx-auto mb-10 leading-relaxed">
          2,500 decision-makers. $18 trillion in assets. Two days at the Louvre.
          Our AI ensures the most valuable connections happen — before you walk
          through the door.
        </p>

        <div className="flex items-center justify-center gap-4">
          <Link
            to="/attendees"
            className="inline-flex items-center gap-2 px-6 py-3 bg-amber-400 text-black font-semibold rounded-xl hover:bg-amber-300 transition-all"
          >
            View Matches
            <ArrowRight className="w-4 h-4" />
          </Link>
          <Link
            to="/dashboard"
            className="inline-flex items-center gap-2 px-6 py-3 bg-white/5 text-white font-semibold rounded-xl border border-white/10 hover:bg-white/10 transition-all"
          >
            Organiser Dashboard
          </Link>
        </div>
      </section>

      {/* How it works */}
      <section>
        <h2 className="text-center text-2xl font-bold mb-12 text-white/80">
          How the Engine Works
        </h2>
        <div className="grid md:grid-cols-3 gap-6">
          {[
            {
              icon: Users,
              title: "Multi-Source Intelligence",
              description:
                "We synthesise registration data, LinkedIn profiles, Twitter activity, company websites, and funding data to build a 360° view of each attendee.",
              color: "from-blue-500 to-blue-600",
            },
            {
              icon: Brain,
              title: "AI Matching Pipeline",
              description:
                "Semantic embeddings find complementary profiles. GPT-4o re-ranks for non-obvious connections and deal-readiness — not keyword matching.",
              color: "from-amber-400 to-amber-600",
            },
            {
              icon: Zap,
              title: "Contextual Explanations",
              description:
                "Every match comes with a clear reason: why you should meet, what you have in common, and what to discuss. No generic 'Let's connect!' messages.",
              color: "from-emerald-400 to-emerald-600",
            },
          ].map(({ icon: Icon, title, description, color }) => (
            <div
              key={title}
              className="p-6 rounded-2xl bg-white/[0.03] border border-white/10 hover:border-white/20 transition-all group"
            >
              <div
                className={`w-10 h-10 rounded-xl bg-gradient-to-br ${color} flex items-center justify-center mb-4`}
              >
                <Icon className="w-5 h-5 text-white" />
              </div>
              <h3 className="text-lg font-semibold mb-2">{title}</h3>
              <p className="text-white/50 text-sm leading-relaxed">
                {description}
              </p>
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
            <div className="text-2xl font-bold text-amber-400">{value}</div>
            <div className="text-sm text-white/40 mt-1">{label}</div>
          </div>
        ))}
      </section>
    </div>
  );
}

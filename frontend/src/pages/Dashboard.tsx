import { useState, useEffect } from "react";
import {
  Users,
  Handshake,
  Check,
  TrendingUp,
  BarChart3,
  Brain,
  Lightbulb,
  DollarSign,
  Activity,
} from "lucide-react";
import type { DashboardStats, MatchQuality } from "../types";
import { getDashboardStats, getMatchQuality } from "../api/client";

// Demo data
const demoStats: DashboardStats = {
  total_attendees: 5,
  matches_generated: 20,
  matches_accepted: 8,
  matches_declined: 3,
  enrichment_coverage: 1.0,
  avg_match_score: 0.67,
  top_sectors: [
    { sector: "tokenised real-world assets", count: 2 },
    { sector: "blockchain infrastructure", count: 2 },
    { sector: "institutional custody", count: 2 },
    { sector: "compliance modules", count: 2 },
    { sector: "regulatory frameworks", count: 2 },
    { sector: "institutional DeFi", count: 1 },
    { sector: "CBDC", count: 1 },
    { sector: "Layer-2 scaling", count: 1 },
    { sector: "TradFi-DeFi convergence", count: 1 },
    { sector: "KYC/AML", count: 1 },
  ],
  match_type_distribution: {
    complementary: 10,
    non_obvious: 6,
    deal_ready: 4,
  },
};

const demoQuality: MatchQuality = {
  total_matches: 20,
  score_distribution: {
    "0.0-0.2": 0,
    "0.2-0.4": 1,
    "0.4-0.6": 6,
    "0.6-0.8": 8,
    "0.8-1.0": 5,
  },
  acceptance_rate: 0.4,
};

function StatCard({
  icon: Icon,
  label,
  value,
  color,
}: {
  icon: React.ElementType;
  label: string;
  value: string | number;
  color: string;
}) {
  return (
    <div className="p-5 rounded-xl bg-white/[0.03] border border-white/10">
      <div className="flex items-center gap-3 mb-3">
        <div className={`w-8 h-8 rounded-lg ${color} flex items-center justify-center`}>
          <Icon className="w-4 h-4 text-white" />
        </div>
        <span className="text-sm text-white/40">{label}</span>
      </div>
      <div className="text-3xl font-bold">{value}</div>
    </div>
  );
}

export default function Dashboard() {
  const [stats, setStats] = useState<DashboardStats>(demoStats);
  const [quality, setQuality] = useState<MatchQuality>(demoQuality);
  useEffect(() => {
    async function load() {
      try {
        const [s, q] = await Promise.all([
          getDashboardStats(),
          getMatchQuality(),
        ]);
        if (s.total_attendees > 0) setStats(s);
        if (q.total_matches > 0) setQuality(q);
      } catch {
        // Use demo data
      }
    }
    load();
  }, []);

  const totalMatchTypes = Object.values(stats.match_type_distribution).reduce(
    (a, b) => a + b,
    0
  );

  const maxBarValue = Math.max(...Object.values(quality.score_distribution));

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-bold">Organiser Dashboard</h1>
        <p className="text-white/50 mt-1">
          Proof of Talk 2026 — Event Intelligence Overview
        </p>
      </div>

      {/* Top stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard
          icon={Users}
          label="Total Attendees"
          value={stats.total_attendees.toLocaleString()}
          color="bg-blue-500"
        />
        <StatCard
          icon={Handshake}
          label="Matches Generated"
          value={stats.matches_generated.toLocaleString()}
          color="bg-amber-500"
        />
        <StatCard
          icon={Check}
          label="Matches Accepted"
          value={stats.matches_accepted.toLocaleString()}
          color="bg-emerald-500"
        />
        <StatCard
          icon={TrendingUp}
          label="Avg Match Score"
          value={`${(stats.avg_match_score * 100).toFixed(0)}%`}
          color="bg-purple-500"
        />
      </div>

      <div className="grid md:grid-cols-2 gap-6">
        {/* Match quality distribution */}
        <div className="p-6 rounded-2xl bg-white/[0.03] border border-white/10">
          <div className="flex items-center gap-2 mb-6">
            <BarChart3 className="w-5 h-5 text-amber-400" />
            <h2 className="text-lg font-semibold">Match Quality Distribution</h2>
          </div>
          <div className="space-y-3">
            {Object.entries(quality.score_distribution).map(([range, count]) => (
              <div key={range} className="flex items-center gap-3">
                <span className="text-xs text-white/40 w-14 font-mono">{range}</span>
                <div className="flex-1 h-6 bg-white/5 rounded-lg overflow-hidden">
                  <div
                    className="h-full rounded-lg bg-gradient-to-r from-amber-400/60 to-amber-400 transition-all duration-500"
                    style={{
                      width: maxBarValue > 0 ? `${(count / maxBarValue) * 100}%` : "0%",
                    }}
                  />
                </div>
                <span className="text-sm font-mono text-white/60 w-8 text-right">{count}</span>
              </div>
            ))}
          </div>
          <div className="mt-4 pt-4 border-t border-white/5 flex items-center justify-between text-sm">
            <span className="text-white/30">Acceptance Rate</span>
            <span className="text-emerald-400 font-semibold">
              {(quality.acceptance_rate * 100).toFixed(0)}%
            </span>
          </div>
        </div>

        {/* Match type breakdown */}
        <div className="p-6 rounded-2xl bg-white/[0.03] border border-white/10">
          <div className="flex items-center gap-2 mb-6">
            <Brain className="w-5 h-5 text-amber-400" />
            <h2 className="text-lg font-semibold">Match Type Breakdown</h2>
          </div>
          <div className="space-y-4">
            {[
              {
                type: "complementary",
                label: "Complementary",
                icon: Handshake,
                color: "bg-blue-400",
                desc: "Investor meets startup, regulator meets builder",
              },
              {
                type: "non_obvious",
                label: "Non-Obvious",
                icon: Lightbulb,
                color: "bg-purple-400",
                desc: "Different sectors solving the same problem",
              },
              {
                type: "deal_ready",
                label: "Deal Ready",
                icon: DollarSign,
                color: "bg-emerald-400",
                desc: "Both parties positioned to transact",
              },
            ].map(({ type, label, icon: Icon, color, desc }) => {
              const count = stats.match_type_distribution[type] || 0;
              const pct = totalMatchTypes > 0 ? (count / totalMatchTypes) * 100 : 0;
              return (
                <div key={type} className="space-y-2">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <Icon className="w-4 h-4 text-white/50" />
                      <span className="text-sm font-medium">{label}</span>
                      <span className="text-xs text-white/30">{desc}</span>
                    </div>
                    <span className="text-sm font-mono text-white/60">{count}</span>
                  </div>
                  <div className="h-2 bg-white/5 rounded-full overflow-hidden">
                    <div
                      className={`h-full rounded-full ${color} transition-all duration-500`}
                      style={{ width: `${pct}%` }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* Top sectors */}
      <div className="p-6 rounded-2xl bg-white/[0.03] border border-white/10">
        <div className="flex items-center gap-2 mb-6">
          <Activity className="w-5 h-5 text-amber-400" />
          <h2 className="text-lg font-semibold">Top Interest Sectors</h2>
        </div>
        <div className="flex flex-wrap gap-2">
          {stats.top_sectors.map(({ sector, count }, i) => (
            <span
              key={sector}
              className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full border text-sm ${
                i < 3
                  ? "bg-amber-400/10 text-amber-400 border-amber-400/20"
                  : "bg-white/5 text-white/50 border-white/10"
              }`}
            >
              {sector}
              <span className="text-xs opacity-60">{count}</span>
            </span>
          ))}
        </div>
      </div>

      {/* Enrichment coverage */}
      <div className="p-6 rounded-2xl bg-white/[0.03] border border-white/10">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <Brain className="w-5 h-5 text-amber-400" />
            <h2 className="text-lg font-semibold">AI Processing Coverage</h2>
          </div>
          <span className="text-2xl font-bold text-amber-400">
            {(stats.enrichment_coverage * 100).toFixed(0)}%
          </span>
        </div>
        <div className="h-3 bg-white/5 rounded-full overflow-hidden">
          <div
            className="h-full rounded-full bg-gradient-to-r from-amber-600 to-amber-400 transition-all duration-500"
            style={{ width: `${stats.enrichment_coverage * 100}%` }}
          />
        </div>
        <p className="text-xs text-white/30 mt-2">
          Percentage of attendees with AI summaries, intent classification, and embeddings generated
        </p>
      </div>
    </div>
  );
}

import { useState } from "react";
import {
  Users, Handshake, Check, TrendingUp, BarChart3, Brain,
  Lightbulb, DollarSign, Activity, Zap, RefreshCw, X,
} from "lucide-react";
import type { Attendee, Match } from "../types";
import {
  useDashboardStats, useMatchQuality, useMatchesByType,
  useAttendeesBySector, useTriggerProcessing, useTriggerMatching,
} from "../hooks/useDashboard";
import { useAuth } from "../hooks/useAuth";
import { enrichAll } from "../api/client";

function StatCard({
  icon: Icon,
  label,
  value,
  color,
  onClick,
}: {
  icon: React.ElementType;
  label: string;
  value: string | number;
  color: string;
  onClick?: () => void;
}) {
  return (
    <div
      className={`p-5 rounded-xl bg-white/[0.03] border border-white/10 ${onClick ? "cursor-pointer hover:border-amber-400/30 hover:bg-white/[0.05] transition-all" : ""}`}
      onClick={onClick}
    >
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

function DrillDownModal({
  title,
  onClose,
  children,
}: {
  title: string;
  onClose: () => void;
  children: React.ReactNode;
}) {
  return (
    <div className="fixed inset-0 z-50 flex items-end sm:items-center justify-center p-4 bg-black/60 backdrop-blur-sm">
      <div className="w-full max-w-2xl max-h-[80vh] rounded-2xl bg-[#0d0d15] border border-white/10 overflow-hidden flex flex-col">
        <div className="flex items-center justify-between px-5 py-4 border-b border-white/10">
          <h3 className="font-semibold">{title}</h3>
          <button onClick={onClose} className="text-white/40 hover:text-white transition-colors">
            <X className="w-5 h-5" />
          </button>
        </div>
        <div className="overflow-y-auto p-5 space-y-3">{children}</div>
      </div>
    </div>
  );
}

export default function Dashboard() {
  const { isAdmin } = useAuth();
  const { data: stats } = useDashboardStats();
  const { data: quality } = useMatchQuality();
  const [drillType, setDrillType] = useState<string | null>(null);
  const [drillSector, setDrillSector] = useState<string | null>(null);
  const [enrichingAll, setEnrichingAll] = useState(false);
  const [actionResult, setActionResult] = useState<string | null>(null);

  const { data: typeMatches, isLoading: loadingTypeMatches } = useMatchesByType(drillType);
  const { data: sectorAttendees, isLoading: loadingSector } = useAttendeesBySector(drillSector);
  const processMutation = useTriggerProcessing();
  const matchMutation = useTriggerMatching();

  const handleTriggerProcessing = async () => {
    const result = await processMutation.mutateAsync();
    setActionResult(`Processed ${result.attendees_processed} attendees`);
  };

  const handleTriggerMatching = async () => {
    const result = await matchMutation.mutateAsync();
    setActionResult(`Generated ${result.total_matches} matches`);
  };

  const handleEnrichAll = async () => {
    setEnrichingAll(true);
    try {
      await enrichAll();
      setActionResult("Enrichment triggered for all attendees");
    } finally {
      setEnrichingAll(false);
    }
  };

  if (!stats || !quality) return null;

  const totalMatchTypes = Object.values(stats.match_type_distribution).reduce((a, b) => a + b, 0);
  const maxBarValue = Math.max(...Object.values(quality.score_distribution));

  const matchTypeList = [
    { type: "complementary", label: "Complementary", icon: Handshake, color: "bg-blue-400", desc: "Investor meets startup, regulator meets builder" },
    { type: "non_obvious", label: "Non-Obvious", icon: Lightbulb, color: "bg-purple-400", desc: "Different sectors solving the same problem" },
    { type: "deal_ready", label: "Deal Ready", icon: DollarSign, color: "bg-emerald-400", desc: "Both parties positioned to transact" },
  ];

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-bold">Organiser Dashboard</h1>
        <p className="text-white/50 mt-1">Proof of Talk 2026 — Event Intelligence Overview</p>
      </div>

      {/* Admin actions */}
      {isAdmin && (
        <div className="p-5 rounded-2xl bg-amber-400/5 border border-amber-400/20">
          <div className="flex items-center gap-2 mb-4">
            <Zap className="w-5 h-5 text-amber-400" />
            <h2 className="font-semibold text-amber-400">Admin Actions</h2>
          </div>
          <div className="flex flex-wrap gap-3">
            <button
              onClick={handleTriggerProcessing}
              disabled={processMutation.isPending}
              className="flex items-center gap-2 px-4 py-2 rounded-lg bg-white/5 border border-white/10 text-sm text-white/70 hover:text-white hover:border-white/20 transition-all disabled:opacity-50"
            >
              <Brain className={`w-4 h-4 ${processMutation.isPending ? "animate-spin" : ""}`} />
              {processMutation.isPending ? "Processing…" : "Process All Attendees"}
            </button>
            <button
              onClick={handleTriggerMatching}
              disabled={matchMutation.isPending}
              className="flex items-center gap-2 px-4 py-2 rounded-lg bg-white/5 border border-white/10 text-sm text-white/70 hover:text-white hover:border-white/20 transition-all disabled:opacity-50"
            >
              <Handshake className={`w-4 h-4 ${matchMutation.isPending ? "animate-spin" : ""}`} />
              {matchMutation.isPending ? "Generating…" : "Generate All Matches"}
            </button>
            <button
              onClick={handleEnrichAll}
              disabled={enrichingAll}
              className="flex items-center gap-2 px-4 py-2 rounded-lg bg-white/5 border border-white/10 text-sm text-white/70 hover:text-white hover:border-white/20 transition-all disabled:opacity-50"
            >
              <RefreshCw className={`w-4 h-4 ${enrichingAll ? "animate-spin" : ""}`} />
              {enrichingAll ? "Enriching…" : "Enrich All Profiles"}
            </button>
          </div>
          {actionResult && (
            <div className="mt-3 text-sm text-emerald-400 flex items-center gap-1.5">
              <Check className="w-3.5 h-3.5" /> {actionResult}
            </div>
          )}
        </div>
      )}

      {/* Top stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard icon={Users} label="Total Attendees" value={stats.total_attendees.toLocaleString()} color="bg-blue-500" />
        <StatCard icon={Handshake} label="Matches Generated" value={stats.matches_generated.toLocaleString()} color="bg-amber-500" />
        <StatCard icon={Check} label="Matches Accepted" value={stats.matches_accepted.toLocaleString()} color="bg-emerald-500" />
        <StatCard icon={TrendingUp} label="Avg Match Score" value={`${(stats.avg_match_score * 100).toFixed(0)}%`} color="bg-purple-500" />
      </div>

      <div className="grid md:grid-cols-2 gap-6">
        {/* Match quality */}
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
                    style={{ width: maxBarValue > 0 ? `${(count / maxBarValue) * 100}%` : "0%" }}
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

        {/* Match type breakdown — clickable */}
        <div className="p-6 rounded-2xl bg-white/[0.03] border border-white/10">
          <div className="flex items-center gap-2 mb-6">
            <Brain className="w-5 h-5 text-amber-400" />
            <h2 className="text-lg font-semibold">Match Type Breakdown</h2>
            <span className="text-xs text-white/30 ml-auto">Click to explore</span>
          </div>
          <div className="space-y-4">
            {matchTypeList.map(({ type, label, icon: Icon, color, desc }) => {
              const count = stats.match_type_distribution[type] ?? 0;
              const pct = totalMatchTypes > 0 ? (count / totalMatchTypes) * 100 : 0;
              return (
                <div
                  key={type}
                  className="space-y-2 cursor-pointer group"
                  onClick={() => setDrillType(type)}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <Icon className="w-4 h-4 text-white/50 group-hover:text-white/70 transition-colors" />
                      <span className="text-sm font-medium group-hover:text-white transition-colors">{label}</span>
                      <span className="text-xs text-white/30">{desc}</span>
                    </div>
                    <span className="text-sm font-mono text-white/60">{count}</span>
                  </div>
                  <div className="h-2 bg-white/5 rounded-full overflow-hidden">
                    <div
                      className={`h-full rounded-full ${color} transition-all duration-500 group-hover:opacity-80`}
                      style={{ width: `${pct}%` }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* Top sectors — clickable */}
      <div className="p-6 rounded-2xl bg-white/[0.03] border border-white/10">
        <div className="flex items-center gap-2 mb-6">
          <Activity className="w-5 h-5 text-amber-400" />
          <h2 className="text-lg font-semibold">Top Interest Sectors</h2>
          <span className="text-xs text-white/30 ml-auto">Click to see attendees</span>
        </div>
        <div className="flex flex-wrap gap-2">
          {stats.top_sectors.map(({ sector, count }, i) => (
            <button
              key={sector}
              onClick={() => setDrillSector(sector)}
              className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full border text-sm transition-all hover:scale-105 ${
                i < 3
                  ? "bg-amber-400/10 text-amber-400 border-amber-400/20 hover:bg-amber-400/20"
                  : "bg-white/5 text-white/50 border-white/10 hover:border-white/20 hover:text-white/70"
              }`}
            >
              {sector}
              <span className="text-xs opacity-60">{count}</span>
            </button>
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

      {/* Drill-down: match type modal */}
      {drillType && (
        <DrillDownModal
          title={`${drillType.replace("_", " ")} matches`}
          onClose={() => setDrillType(null)}
        >
          {loadingTypeMatches ? (
            <div className="text-center py-8 text-white/30">Loading…</div>
          ) : (typeMatches?.matches ?? []).length === 0 ? (
            <div className="text-center py-8 text-white/30">No matches of this type yet.</div>
          ) : (
            (typeMatches?.matches ?? []).map((match: Match) => (
              <div key={match.id} className="p-4 rounded-xl bg-white/[0.03] border border-white/10">
                <div className="flex items-center justify-between mb-2">
                  <div className="text-sm font-semibold">
                    {match.matched_attendee?.name ?? `Match ${match.id.slice(0, 8)}`}
                  </div>
                  <span className="text-sm font-bold text-amber-400">{(match.overall_score * 100).toFixed(0)}%</span>
                </div>
                <p className="text-xs text-white/40 line-clamp-2">{match.explanation}</p>
              </div>
            ))
          )}
        </DrillDownModal>
      )}

      {/* Drill-down: sector attendees modal */}
      {drillSector && (
        <DrillDownModal
          title={`Attendees interested in "${drillSector}"`}
          onClose={() => setDrillSector(null)}
        >
          {loadingSector ? (
            <div className="text-center py-8 text-white/30">Loading…</div>
          ) : (sectorAttendees?.attendees ?? []).length === 0 ? (
            <div className="text-center py-8 text-white/30">No attendees found for this sector.</div>
          ) : (
            (sectorAttendees?.attendees ?? []).map((a: Attendee) => (
              <div key={a.id} className="flex items-center gap-3 p-3 rounded-xl bg-white/[0.03] border border-white/10">
                <div className="w-9 h-9 rounded-full bg-gradient-to-br from-amber-400/20 to-amber-600/20 flex items-center justify-center text-amber-400 font-bold shrink-0">
                  {a.name[0]}
                </div>
                <div>
                  <div className="text-sm font-semibold">{a.name}</div>
                  <div className="text-xs text-white/40">{a.title} · {a.company}</div>
                </div>
              </div>
            ))
          )}
        </DrillDownModal>
      )}
    </div>
  );
}

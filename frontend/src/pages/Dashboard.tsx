import { useState } from "react";
import {
  Users, Handshake, Check, TrendingUp, BarChart3, Brain,
  Lightbulb, DollarSign, Activity, Zap, RefreshCw, X, Sparkles,
} from "lucide-react";
import type { Attendee, Match } from "../types";
import {
  useDashboardStats, useMatchQuality, useMatchesByType,
  useAttendeesBySector, useTriggerProcessing, useTriggerMatching,
} from "../hooks/useDashboard";
import { useAuth } from "../hooks/useAuth";
import { enrichAll, syncExtasy, syncSpeakers, getInvestorHeatmap, getRevenueStats } from "../api/client";
import { useQuery } from "@tanstack/react-query";

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
      className={`p-5 rounded-xl bg-white/[0.03] border border-white/10 ${onClick ? "cursor-pointer hover:border-[#E76315]/30 hover:bg-white/[0.05] transition-all" : ""}`}
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
  const [syncingExtasy, setSyncingExtasy] = useState(false);
  const [syncingSpeakers, setSyncingSpeakers] = useState(false);
  const [actionResult, setActionResult] = useState<string | null>(null);

  const { data: typeMatches, isLoading: loadingTypeMatches } = useMatchesByType(drillType);
  const { data: sectorAttendees, isLoading: loadingSector } = useAttendeesBySector(drillSector);
  const { data: heatmapData } = useQuery({
    queryKey: ["investor-heatmap"],
    queryFn: getInvestorHeatmap,
    staleTime: 60_000,
  });
  const { data: revenueData } = useQuery({
    queryKey: ["revenue-stats"],
    queryFn: getRevenueStats,
    staleTime: 60_000,
  });
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

  const handleSyncExtasy = async () => {
    setSyncingExtasy(true);
    setActionResult(null);
    try {
      const result = await syncExtasy();
      setActionResult(
        `Extasy sync complete — ${result.inserted} inserted, ${result.upgraded} upgraded, ${result.skipped} skipped (${result.paid_count} paid orders from ${result.total_fetched} total)`
      );
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Sync failed";
      setActionResult(`Extasy sync error: ${msg}`);
    } finally {
      setSyncingExtasy(false);
    }
  };

  const handleSyncSpeakers = async () => {
    setSyncingSpeakers(true);
    setActionResult(null);
    try {
      const result = await syncSpeakers();
      setActionResult(`Speakers sync — ${result.inserted} inserted, ${result.updated} updated, ${result.skipped} skipped`);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Sync failed";
      setActionResult(`Speakers sync error: ${msg}`);
    } finally {
      setSyncingSpeakers(false);
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
        <div className="p-5 rounded-2xl bg-[#E76315]/5 border border-[#E76315]/20">
          <div className="flex items-center gap-2 mb-4">
            <Zap className="w-5 h-5 text-[#E76315]" />
            <h2 className="font-semibold text-[#E76315]">Admin Actions</h2>
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
            <button
              onClick={handleSyncExtasy}
              disabled={syncingExtasy}
              className="flex items-center gap-2 px-4 py-2 rounded-lg bg-[#E76315]/10 border border-[#E76315]/30 text-sm text-[#E76315] hover:bg-[#E76315]/20 hover:border-[#E76315]/50 transition-all disabled:opacity-50"
            >
              <RefreshCw className={`w-4 h-4 ${syncingExtasy ? "animate-spin" : ""}`} />
              {syncingExtasy ? "Syncing…" : "Sync from Extasy"}
            </button>
            <button
              onClick={handleSyncSpeakers}
              disabled={syncingSpeakers}
              className="flex items-center gap-2 px-4 py-2 rounded-lg bg-purple-500/10 border border-purple-500/30 text-sm text-purple-400 hover:bg-purple-500/20 hover:border-purple-500/50 transition-all disabled:opacity-50"
            >
              <RefreshCw className={`w-4 h-4 ${syncingSpeakers ? "animate-spin" : ""}`} />
              {syncingSpeakers ? "Syncing…" : "Sync Speakers"}
            </button>
          </div>
          {actionResult && (
            <div className="mt-3 text-sm text-emerald-400 flex items-center gap-1.5">
              <Check className="w-3.5 h-3.5" /> {actionResult}
            </div>
          )}
        </div>
      )}

      {/* Revenue & Registration */}
      {revenueData && (
        <>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <StatCard icon={DollarSign} label="Total Revenue" value={`€${revenueData.revenue.total.toLocaleString()}`} color="bg-emerald-500" />
            <StatCard icon={Users} label="Valid Tickets" value={revenueData.funnel.valid} color="bg-blue-500" />
            <StatCard icon={TrendingUp} label="Conversion Rate" value={`${(revenueData.funnel.conversion_rate * 100).toFixed(1)}%`} color="bg-purple-500" />
            <StatCard icon={DollarSign} label="Avg Ticket Price" value={`€${revenueData.revenue.avg_ticket_price.toFixed(0)}`} color="bg-[#D35400]" />
          </div>

          {/* Registration funnel */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="p-6 rounded-2xl bg-white/[0.03] border border-white/10">
              <div className="flex items-center gap-2 mb-4">
                <Activity className="w-5 h-5 text-[#E76315]" />
                <h2 className="text-lg font-semibold">Registration Funnel</h2>
              </div>
              <div className="space-y-3">
                {[
                  { label: "Total Orders", value: revenueData.funnel.total_orders, color: "bg-white/20" },
                  { label: "Paid", value: revenueData.funnel.paid, color: "bg-emerald-500" },
                  { label: "Redeemed (comp)", value: revenueData.funnel.redeemed, color: "bg-blue-500" },
                  { label: "Failed", value: revenueData.funnel.failed, color: "bg-red-500" },
                  { label: "Pending", value: revenueData.funnel.pending, color: "bg-yellow-500" },
                  { label: "Refunded", value: revenueData.funnel.refunded, color: "bg-white/30" },
                ].map(({ label, value, color }) => {
                  const pct = revenueData.funnel.total_orders ? (value / revenueData.funnel.total_orders) * 100 : 0;
                  return (
                    <div key={label} className="flex items-center gap-3">
                      <span className="w-32 text-xs text-white/50 text-right shrink-0">{label}</span>
                      <div className="flex-1 h-6 bg-white/5 rounded-full overflow-hidden relative">
                        <div className={`h-full ${color} rounded-full transition-all`} style={{ width: `${Math.max(pct, 2)}%` }} />
                        <span className="absolute inset-0 flex items-center justify-center text-[10px] font-bold text-white/80">{value}</span>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Revenue by ticket type */}
            <div className="p-6 rounded-2xl bg-white/[0.03] border border-white/10">
              <div className="flex items-center gap-2 mb-4">
                <DollarSign className="w-5 h-5 text-emerald-400" />
                <h2 className="text-lg font-semibold">Revenue by Ticket Type</h2>
              </div>
              <div className="space-y-3">
                {revenueData.revenue.by_type.map(({ type, count, revenue }) => (
                  <div key={type} className="flex items-center justify-between gap-2">
                    <div className="min-w-0">
                      <div className="text-xs font-medium truncate">{type}</div>
                      <div className="text-[10px] text-white/30">{count} ticket{count !== 1 ? "s" : ""}</div>
                    </div>
                    <span className="text-xs font-mono text-emerald-400 shrink-0 whitespace-nowrap">€{revenue.toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 0 })}</span>
                  </div>
                ))}
                <div className="pt-2 border-t border-white/10 flex items-center justify-between">
                  <span className="text-xs text-white/40">Paid: {revenueData.revenue.paid_tickets} · Comp: {revenueData.revenue.comp_tickets}</span>
                </div>
              </div>
            </div>
          </div>

          {/* Attendee growth + source breakdown + profile completeness */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {/* Weekly growth */}
            <div className="p-6 rounded-2xl bg-white/[0.03] border border-white/10">
              <div className="flex items-center gap-2 mb-4">
                <TrendingUp className="w-5 h-5 text-[#E76315]" />
                <h2 className="text-lg font-semibold">Weekly Growth</h2>
              </div>
              <div className="space-y-2">
                {revenueData.growth.map(({ week, registrations }) => {
                  const maxReg = Math.max(...revenueData.growth.map(g => g.registrations), 1);
                  // Convert "2026-W11" to "Mar 10" style
                  const weekLabel = (() => {
                    try {
                      const [y, w] = week.split("-W");
                      const jan1 = new Date(parseInt(y), 0, 1);
                      const d = new Date(jan1.getTime() + ((parseInt(w) - 1) * 7 - jan1.getDay() + 1) * 86400000);
                      return d.toLocaleDateString("en-GB", { month: "short", day: "numeric" });
                    } catch { return week; }
                  })();
                  return (
                    <div key={week} className="flex items-center gap-2">
                      <span className="w-16 text-[10px] text-white/40 text-right shrink-0">{weekLabel}</span>
                      <div className="flex-1 h-5 bg-white/5 rounded overflow-hidden relative">
                        <div className="h-full bg-[#E76315] rounded transition-all" style={{ width: `${(registrations / maxReg) * 100}%` }} />
                        <span className="absolute inset-0 flex items-center justify-center text-[10px] font-bold text-white/70">{registrations}</span>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Source breakdown */}
            <div className="p-6 rounded-2xl bg-white/[0.03] border border-white/10">
              <div className="flex items-center gap-2 mb-4">
                <Users className="w-5 h-5 text-blue-400" />
                <h2 className="text-lg font-semibold">Attendee Sources</h2>
              </div>
              <div className="space-y-3">
                {[
                  { label: "Rhuna / Extasy", value: revenueData.source_breakdown.extasy, color: "text-[#E76315]" },
                  { label: "1000 Minds Speakers", value: revenueData.source_breakdown.speakers_1000minds, color: "text-purple-400" },
                  { label: "Seed / Test", value: revenueData.source_breakdown.seed, color: "text-white/30" },
                  { label: "Self-registered", value: revenueData.source_breakdown.other, color: "text-blue-400" },
                ].map(({ label, value, color }) => (
                  <div key={label} className="flex items-center justify-between">
                    <span className="text-sm text-white/60">{label}</span>
                    <span className={`text-lg font-bold ${color}`}>{value}</span>
                  </div>
                ))}
                <div className="pt-2 border-t border-white/10 flex items-center justify-between">
                  <span className="text-xs text-white/40">Total in DB</span>
                  <span className="text-lg font-bold">{revenueData.source_breakdown.total}</span>
                </div>
              </div>
            </div>

            {/* Profile completeness */}
            <div className="p-6 rounded-2xl bg-white/[0.03] border border-white/10">
              <div className="flex items-center gap-2 mb-4">
                <Lightbulb className="w-5 h-5 text-emerald-400" />
                <h2 className="text-lg font-semibold">Profile Quality</h2>
              </div>
              <div className="space-y-2">
                {[
                  { label: "Goals", value: revenueData.profile_completeness.with_goals, color: "bg-emerald-500" },
                  { label: "LinkedIn", value: revenueData.profile_completeness.with_linkedin, color: "bg-blue-500" },
                  { label: "Twitter", value: revenueData.profile_completeness.with_twitter, color: "bg-sky-500" },
                  { label: "Website", value: revenueData.profile_completeness.with_website, color: "bg-[#E76315]" },
                  { label: "Grid", value: revenueData.profile_completeness.with_grid, color: "bg-purple-500" },
                  { label: "Photo", value: revenueData.profile_completeness.with_photo, color: "bg-pink-500" },
                  { label: "Targets", value: revenueData.profile_completeness.with_targets, color: "bg-yellow-500" },
                ].map(({ label, value, color }) => {
                  const pct = revenueData.profile_completeness.total ? (value / revenueData.profile_completeness.total) * 100 : 0;
                  return (
                    <div key={label} className="flex items-center gap-2">
                      <span className="w-16 text-xs text-white/50 text-right shrink-0">{label}</span>
                      <div className="flex-1 h-5 bg-white/5 rounded-full overflow-hidden relative">
                        <div className={`h-full ${color} rounded-full`} style={{ width: `${Math.max(pct, 3)}%` }} />
                        {value > 0 && (
                          <span className="absolute inset-0 flex items-center justify-center text-[10px] font-bold text-white/70">{Math.round(pct)}%</span>
                        )}
                      </div>
                      <span className="text-xs text-white/40 w-10 text-right">{value}</span>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        </>
      )}

      {/* Matchmaking stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard icon={Users} label="Total Attendees" value={stats.total_attendees.toLocaleString()} color="bg-blue-500" />
        <StatCard icon={Handshake} label="Matches Generated" value={stats.matches_generated.toLocaleString()} color="bg-[#D35400]" />
        <StatCard icon={Check} label="Matches Accepted" value={stats.matches_accepted.toLocaleString()} color="bg-emerald-500" />
        <StatCard icon={TrendingUp} label="Avg Match Score" value={`${(stats.avg_match_score * 100).toFixed(0)}%`} color="bg-purple-500" />
      </div>

      {/* Outcome funnel KPIs */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard
          icon={Handshake}
          label="Mutual Accept Rate"
          value={`${(stats.mutual_accept_rate * 100).toFixed(1)}%`}
          color="bg-emerald-600"
        />
        <StatCard
          icon={Activity}
          label="Scheduled Rate"
          value={`${(stats.scheduled_rate * 100).toFixed(1)}%`}
          color="bg-blue-600"
        />
        <StatCard
          icon={Check}
          label="Show Rate"
          value={`${(stats.show_rate * 100).toFixed(1)}%`}
          color="bg-indigo-600"
        />
        <StatCard
          icon={Sparkles}
          label="Post-Meeting CSAT"
          value={stats.post_meeting_satisfaction > 0 ? `${stats.post_meeting_satisfaction.toFixed(2)} / 5` : "N/A"}
          color="bg-amber-600"
        />
      </div>

      <div className="grid md:grid-cols-2 gap-6">
        {/* Match quality */}
        <div className="p-6 rounded-2xl bg-white/[0.03] border border-white/10">
          <div className="flex items-center gap-2 mb-6">
            <BarChart3 className="w-5 h-5 text-[#E76315]" />
            <h2 className="text-lg font-semibold">Match Quality Distribution</h2>
          </div>
          <div className="space-y-3">
            {Object.entries(quality.score_distribution).map(([range, count]) => (
              <div key={range} className="flex items-center gap-3">
                <span className="text-xs text-white/40 w-14 font-mono">{range}</span>
                <div className="flex-1 h-6 bg-white/5 rounded-lg overflow-hidden">
                  <div
                    className="h-full rounded-lg bg-gradient-to-r from-[#E76315]/60 to-[#FF833A] transition-all duration-500"
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
            <Brain className="w-5 h-5 text-[#E76315]" />
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
          <Activity className="w-5 h-5 text-[#E76315]" />
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
                  ? "bg-[#E76315]/10 text-[#E76315] border-[#E76315]/20 hover:bg-[#E76315]/20"
                  : "bg-white/5 text-white/50 border-white/10 hover:border-white/20 hover:text-white/70"
              }`}
            >
              {sector}
              <span className="text-xs opacity-60">{count}</span>
            </button>
          ))}
        </div>
      </div>

      {/* Investor Heatmap */}
      {heatmapData && (
        <div className="p-6 rounded-2xl bg-white/[0.03] border border-white/10">
          <div className="flex items-center gap-2 mb-2">
            <DollarSign className="w-5 h-5 text-[#E76315]" />
            <h2 className="text-lg font-semibold">Investor Heatmap</h2>
          </div>
          <p className="text-xs text-white/30 mb-6">Capital activity by sector — darker = more deal-ready attendees</p>

          {/* Deal readiness summary */}
          <div className="grid grid-cols-3 gap-3 mb-6">
            {[
              { label: "High readiness", count: heatmapData.deal_readiness_distribution.high, color: "text-emerald-400" },
              { label: "Medium readiness", count: heatmapData.deal_readiness_distribution.medium, color: "text-[#E76315]" },
              { label: "Low readiness", count: heatmapData.deal_readiness_distribution.low, color: "text-white/40" },
            ].map(({ label, count, color }) => (
              <div key={label} className="text-center p-3 rounded-lg bg-white/[0.02] border border-white/5">
                <div className={`text-xl font-bold ${color}`}>{count}</div>
                <div className="text-[10px] text-white/30 uppercase mt-0.5">{label}</div>
              </div>
            ))}
          </div>

          {/* Heatmap grid */}
          <div className="space-y-2">
            {heatmapData.heatmap.map((row) => {
              const maxActive = Math.max(...heatmapData.heatmap.map((r) => r.capital_active), 1);
              const intensity = row.capital_active / maxActive;
              return (
                <div key={row.vertical} className="flex items-center gap-3">
                  <div className="w-44 text-xs text-white/50 truncate text-right shrink-0">{row.label}</div>
                  <div className="flex-1 flex items-center gap-2">
                    <div
                      className="h-8 rounded-lg transition-all relative overflow-hidden"
                      style={{
                        width: `${Math.max(intensity * 100, 8)}%`,
                        background: `rgba(231, 99, 21, ${0.15 + intensity * 0.7})`,
                        border: `1px solid rgba(231, 99, 21, ${0.2 + intensity * 0.4})`,
                      }}
                    >
                      {row.capital_active > 0 && (
                        <div className="absolute inset-0 flex items-center justify-center">
                          <span className="text-[10px] font-bold text-white/80">
                            {row.capital_active} active
                          </span>
                        </div>
                      )}
                    </div>
                    <span className="text-[10px] text-white/30 shrink-0">
                      {row.attendee_count} total · {(row.avg_deal_readiness * 100).toFixed(0)}% ready
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Enrichment coverage */}
      <div className="p-6 rounded-2xl bg-white/[0.03] border border-white/10">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <Brain className="w-5 h-5 text-[#E76315]" />
            <h2 className="text-lg font-semibold">AI Processing Coverage</h2>
          </div>
          <span className="text-2xl font-bold text-[#E76315]">
            {(stats.enrichment_coverage * 100).toFixed(0)}%
          </span>
        </div>
        <div className="h-3 bg-white/5 rounded-full overflow-hidden">
          <div
            className="h-full rounded-full bg-gradient-to-r from-[#D35400] to-[#FF833A] transition-all duration-500"
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
                  <span className="text-sm font-bold text-[#E76315]">{(match.overall_score * 100).toFixed(0)}%</span>
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
                <div className="w-9 h-9 rounded-full bg-gradient-to-br from-[#E76315]/20 to-[#D35400]/20 flex items-center justify-center text-[#E76315] font-bold shrink-0">
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

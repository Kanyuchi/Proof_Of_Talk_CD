import { useState } from "react";
import {
  Users, Handshake, Check, TrendingUp, BarChart3, Brain,
  Lightbulb, DollarSign, Activity, Zap, RefreshCw, X, Sparkles, Download,
} from "lucide-react";
import type { Attendee, Match } from "../types";
import {
  useDashboardStats, useMatchQuality, useMatchesByType,
  useAttendeesBySector, useTriggerProcessing, useTriggerMatching,
} from "../hooks/useDashboard";
import { useAuth } from "../hooks/useAuth";
import { enrichAll, syncExtasy, syncSpeakers, getInvestorHeatmap, getRevenueStats, getSponsors, generateSponsorReport, reEnrichGrid } from "../api/client";
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
  const [reEnrichingGrid, setReEnrichingGrid] = useState(false);
  const [selectedSponsor, setSelectedSponsor] = useState("");
  const [sponsorReport, setSponsorReport] = useState<Record<string, unknown> | null>(null);
  const [generatingReport, setGeneratingReport] = useState(false);
  const [reportError, setReportError] = useState<string | null>(null);

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
  const { data: sponsorsData } = useQuery({
    queryKey: ["sponsors"],
    queryFn: getSponsors,
    staleTime: 300_000,
    enabled: isAdmin,
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

  const handleDownloadReport = () => {
    if (!sponsorReport) return;
    const sponsor = sponsorReport.sponsor as Record<string, unknown>;
    const grid = sponsorReport.grid_data as Record<string, unknown>;
    const explanations = sponsorReport.explanations as Record<string, unknown>[];
    const attendees = sponsorReport.attendees as Record<string, unknown>[];
    const team = sponsorReport.team_members as Record<string, unknown>[];
    const summary = sponsorReport.summary as Record<string, number>;
    const meta = sponsorReport.meta as Record<string, string>;

    const rows = (explanations || []).map((exp, i) => {
      const idx = (exp.attendee_index as number) - 1;
      const a = attendees?.[idx] || {};
      const conf = exp.confidence as Record<string, unknown> | undefined;
      const confColor = (conf?.label as string) === "high" ? "#34d399" : (conf?.label as string) === "medium" ? "#fbbf24" : "#94a3b8";
      return `
        <div style="background:#13131f;border:1px solid rgba(255,255,255,0.06);border-radius:12px;padding:20px;margin-bottom:12px;">
          <div style="display:flex;justify-content:space-between;margin-bottom:8px;">
            <div><span style="color:#E76315;font-family:'Instrument Serif',serif;font-size:18px;margin-right:8px;">#${i+1}</span><strong style="color:#e8e8f0">${a.name || ""}</strong><span style="color:rgba(255,255,255,0.4);font-size:13px;margin-left:8px;">${a.title || ""}${a.company ? " · " + a.company : ""}</span></div>
            <div><span style="padding:2px 10px;border-radius:100px;font-size:11px;font-weight:600;background:${exp.relevance === "HIGH" ? "rgba(52,211,153,0.2)" : exp.relevance === "MEDIUM" ? "rgba(251,191,36,0.2)" : "rgba(255,255,255,0.1)"};color:${exp.relevance === "HIGH" ? "#34d399" : exp.relevance === "MEDIUM" ? "#fbbf24" : "rgba(255,255,255,0.4)"}">${exp.relevance}</span><span style="width:8px;height:8px;border-radius:50%;background:${confColor};display:inline-block;margin-left:8px;" title="Confidence: ${conf?.label || "low"}"></span></div>
          </div>
          <p style="font-size:14px;color:rgba(255,255,255,0.7);margin-bottom:8px;">${exp.why_they_matter || ""}</p>
          <div style="font-size:12px;color:rgba(255,255,255,0.5);"><strong style="color:#E76315">Open with:</strong> ${exp.conversation_opener || ""}</div>
          <div style="font-size:12px;color:rgba(255,255,255,0.5);"><strong style="color:#a78bfa">Deal potential:</strong> ${exp.deal_potential || ""}</div>
          ${(exp.caveats as string) ? `<div style="margin-top:6px;padding:4px 8px;border-radius:6px;background:rgba(251,191,36,0.05);border:1px solid rgba(251,191,36,0.1);font-size:11px;color:rgba(251,191,36,0.7);">⚠ ${exp.caveats}</div>` : ""}
          ${(exp.key_evidence as string[])?.length ? `<div style="margin-top:6px;display:flex;flex-wrap:wrap;gap:4px;">${(exp.key_evidence as string[]).map(ev => `<span style="padding:2px 6px;border-radius:4px;font-size:10px;background:rgba(255,255,255,0.05);color:rgba(255,255,255,0.3)">${ev}</span>`).join("")}</div>` : ""}
        </div>`;
    }).join("");

    const gridSection = grid?.found ? `
      <div style="margin:12px 0;">
        <span style="background:rgba(16,185,129,0.1);color:#34d399;padding:4px 12px;border-radius:100px;font-size:12px;font-weight:600;">✓ Verified by The Grid</span>
        <span style="background:rgba(167,139,250,0.1);color:#a78bfa;padding:4px 12px;border-radius:100px;font-size:12px;margin-left:8px;">${grid.sector || ""}</span>
      </div>
      <p style="color:rgba(255,255,255,0.4);font-size:14px;">${grid.description || ""}</p>
      ${(grid.products as string[])?.length ? `<p style="font-size:13px;color:rgba(255,255,255,0.6);"><strong>Products:</strong> ${(grid.products as string[]).join(", ")}</p>` : ""}
    ` : `<p style="color:rgba(255,255,255,0.3);font-size:13px;">Grid data not available — report based on company name only</p>`;

    const teamSection = (team?.length) ? `
      <div style="margin:32px 0;">
        <h2 style="font-family:'Instrument Serif',serif;font-size:24px;font-weight:400;margin-bottom:12px;color:#e8e8f0;">Your Team at POT 2026</h2>
        <ul style="padding-left:20px;">${team.map(t => `<li style="margin:4px 0;font-size:14px;color:rgba(255,255,255,0.7);"><strong>${t.name}</strong> — ${t.title} (${t.ticket_type})</li>`).join("")}</ul>
      </div>` : "";

    const html = `<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"><title>${sponsor.name} — POT 2026 Intelligence Briefing</title><link href="https://fonts.googleapis.com/css2?family=Instrument+Serif:ital@0;1&family=DM+Sans:wght@400;500;600;700&display=swap" rel="stylesheet"><style>*{margin:0;padding:0;box-sizing:border-box}body{background:#0d0d1a;color:#e8e8f0;font-family:'DM Sans',sans-serif;line-height:1.6}.page{max-width:900px;margin:0 auto;padding:60px 32px 80px}.hero{text-align:center;padding:60px 0 40px}.hero h1{font-family:'Instrument Serif',serif;font-size:42px;font-weight:400}.hero h1 em{color:#E76315;font-style:italic}.badge{display:inline-block;font-size:11px;font-weight:600;letter-spacing:0.12em;text-transform:uppercase;color:#E76315;border:1px solid rgba(231,99,21,0.3);padding:6px 16px;border-radius:100px;margin-bottom:24px}.stats{display:grid;grid-template-columns:repeat(4,1fr);gap:1px;background:rgba(255,255,255,0.06);border-radius:12px;overflow:hidden;margin:24px 0}.stat{background:#13131f;padding:20px;text-align:center}.stat .num{font-family:'Instrument Serif',serif;font-size:28px;color:#E76315}.stat .label{font-size:11px;color:rgba(255,255,255,0.4);text-transform:uppercase;letter-spacing:0.06em;margin-top:4px}.disclaimer{margin:16px 0;padding:12px;border-radius:8px;background:rgba(251,191,36,0.05);border:1px solid rgba(251,191,36,0.1);font-size:12px;color:rgba(251,191,36,0.6)}.footer{text-align:center;margin-top:48px;font-size:12px;color:rgba(255,255,255,0.2)}</style></head><body><div class="page"><div class="hero"><div class="badge">${sponsor.tier} Sponsor · Confidential</div><h1>${sponsor.name} — <em>Intelligence Briefing</em></h1><p style="color:rgba(255,255,255,0.4);font-size:15px;">Proof of Talk 2026 · Louvre Palace, Paris · June 2–3</p>${gridSection}</div><div class="stats"><div class="stat"><div class="num">${summary?.total_targets || 0}</div><div class="label">Target attendees</div></div><div class="stat"><div class="num">${summary?.high_relevance || 0}</div><div class="label">High relevance</div></div><div class="stat"><div class="num">${summary?.medium_relevance || 0}</div><div class="label">Medium</div></div><div class="stat"><div class="num">${summary?.team_attending || 0}</div><div class="label">Your team</div></div></div><div class="disclaimer">⚠ ${meta?.disclaimer || "This report combines verified data and AI-generated analysis. Fields marked [AI-INFERRED] should be verified."}<br>Average data confidence: ${((summary?.avg_confidence || 0) * 100).toFixed(0)}%</div>${teamSection}<div style="margin:32px 0;"><h2 style="font-family:'Instrument Serif',serif;font-size:28px;font-weight:400;margin-bottom:16px;color:#e8e8f0;">Your Top ${summary?.total_targets || 0} Targets</h2>${rows}</div><div class="footer">Proof of Talk 2026 · Sponsor Intelligence Report · Generated ${new Date().toLocaleDateString("en-GB", {day:"numeric",month:"long",year:"numeric"})} · Confidential</div></div></body></html>`;

    const blob = new Blob([html], { type: "text/html" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${(sponsor.name as string).toLowerCase().replace(/\s+/g, "-")}-intelligence-report.html`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleGenerateSponsorReport = async () => {
    if (!selectedSponsor) return;
    setGeneratingReport(true);
    setSponsorReport(null);
    setReportError(null);
    try {
      const report = await generateSponsorReport(selectedSponsor);
      if (report.error) {
        setReportError(String(report.error));
      } else {
        setSponsorReport(report);
      }
    } catch (err: unknown) {
      setReportError(err instanceof Error ? err.message : "Failed to generate report");
    } finally {
      setGeneratingReport(false);
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
            <button
              onClick={async () => {
                setReEnrichingGrid(true); setActionResult(null);
                try {
                  const r = await reEnrichGrid();
                  setActionResult(`Grid re-enrichment: ${r.newly_enriched} new, ${r.already_enriched} already had Grid, ${r.not_found} not found in Grid`);
                } catch (err: unknown) {
                  setActionResult(`Grid re-enrichment error: ${err instanceof Error ? err.message : "failed"}`);
                } finally { setReEnrichingGrid(false); }
              }}
              disabled={reEnrichingGrid}
              className="flex items-center gap-2 px-4 py-2 rounded-lg bg-emerald-500/10 border border-emerald-500/30 text-sm text-emerald-400 hover:bg-emerald-500/20 hover:border-emerald-500/50 transition-all disabled:opacity-50"
            >
              <RefreshCw className={`w-4 h-4 ${reEnrichingGrid ? "animate-spin" : ""}`} />
              {reEnrichingGrid ? "Re-enriching Grid…" : "Re-enrich Grid B2B"}
            </button>
          </div>
          {actionResult && (
            <div className="mt-3 text-sm text-emerald-400 flex items-center gap-1.5">
              <Check className="w-3.5 h-3.5" /> {actionResult}
            </div>
          )}
        </div>
      )}

      {/* Sponsor Intelligence */}
      {isAdmin && sponsorsData && (
        <div className="p-5 rounded-2xl bg-purple-500/5 border border-purple-500/20">
          <div className="flex items-center gap-2 mb-4">
            <Sparkles className="w-5 h-5 text-purple-400" />
            <h2 className="font-semibold text-purple-400">Sponsor Intelligence Reports</h2>
          </div>
          <div className="flex flex-wrap items-end gap-3">
            <div>
              <label className="block text-xs text-white/40 mb-1">Select Sponsor</label>
              <select
                value={selectedSponsor}
                onChange={(e) => { setSelectedSponsor(e.target.value); setSponsorReport(null); setReportError(null); }}
                className="px-3 py-2 rounded-lg bg-white/5 border border-white/10 text-sm text-white/80 min-w-[220px]"
              >
                <option value="">Choose a sponsor…</option>
                {sponsorsData.sponsors.map((s) => (
                  <option key={s.name} value={s.name}>
                    {s.name} ({s.tier}, €{s.value.toLocaleString()})
                  </option>
                ))}
              </select>
            </div>
            <button
              onClick={handleGenerateSponsorReport}
              disabled={!selectedSponsor || generatingReport}
              className="flex items-center gap-2 px-4 py-2 rounded-lg bg-purple-500/10 border border-purple-500/30 text-sm text-purple-400 hover:bg-purple-500/20 hover:border-purple-500/50 transition-all disabled:opacity-50"
            >
              <Sparkles className={`w-4 h-4 ${generatingReport ? "animate-pulse" : ""}`} />
              {generatingReport ? "Generating (15-30s)…" : "Generate Report"}
            </button>
            {sponsorReport && (
              <button
                onClick={handleDownloadReport}
                className="flex items-center gap-2 px-4 py-2 rounded-lg bg-emerald-500/10 border border-emerald-500/30 text-sm text-emerald-400 hover:bg-emerald-500/20 hover:border-emerald-500/50 transition-all"
              >
                <Download className="w-4 h-4" />
                Download Report
              </button>
            )}
          </div>

          {reportError && (
            <div className="mt-3 text-sm text-red-400">{reportError}</div>
          )}

          {sponsorReport && (
            <div className="mt-4 space-y-4">
              {/* Summary stats */}
              <div className="grid grid-cols-2 md:grid-cols-5 gap-2">
                {[
                  { label: "Targets", value: (sponsorReport.summary as Record<string, number>)?.total_targets || 0 },
                  { label: "High", value: (sponsorReport.summary as Record<string, number>)?.high_relevance || 0, color: "text-emerald-400" },
                  { label: "Medium", value: (sponsorReport.summary as Record<string, number>)?.medium_relevance || 0, color: "text-yellow-400" },
                  { label: "Low", value: (sponsorReport.summary as Record<string, number>)?.low_relevance || 0, color: "text-white/40" },
                  { label: "Team", value: (sponsorReport.summary as Record<string, number>)?.team_attending || 0, color: "text-blue-400" },
                ].map(({ label, value, color }) => (
                  <div key={label} className="p-3 rounded-lg bg-white/5 text-center">
                    <div className={`text-lg font-bold ${color || "text-white"}`}>{value}</div>
                    <div className="text-[10px] text-white/40 uppercase">{label}</div>
                  </div>
                ))}
              </div>

              {/* Grid status */}
              {(sponsorReport.grid_data as Record<string, unknown>)?.found ? (
                <div className="flex items-center gap-2 text-xs">
                  <span className="px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400">✓ Grid Verified</span>
                  <span className="text-white/40">{(sponsorReport.grid_data as Record<string, unknown>)?.sector as string} · {((sponsorReport.grid_data as Record<string, unknown>)?.products as string[])?.join(", ")}</span>
                </div>
              ) : (
                <div className="text-xs text-white/30">Grid data not available for this sponsor — report based on name only</div>
              )}

              {/* Avg confidence */}
              <div className="text-xs text-white/40">
                Avg data confidence: <span className={`font-semibold ${(sponsorReport.summary as Record<string, number>)?.avg_confidence >= 0.7 ? "text-emerald-400" : (sponsorReport.summary as Record<string, number>)?.avg_confidence >= 0.4 ? "text-yellow-400" : "text-red-400"}`}>
                  {((sponsorReport.summary as Record<string, number>)?.avg_confidence * 100).toFixed(0)}%
                </span>
                {" · "}
                <span className="text-white/30">{(sponsorReport.meta as Record<string, string>)?.disclaimer}</span>
              </div>

              {/* Explanation cards */}
              <div className="space-y-2 max-h-[500px] overflow-y-auto">
                {((sponsorReport.explanations as Record<string, unknown>[]) || []).map((exp, i) => {
                  const attendees = sponsorReport.attendees as Record<string, unknown>[];
                  const idx = (exp.attendee_index as number) - 1;
                  const attendee = attendees?.[idx];
                  const confidence = exp.confidence as Record<string, unknown> | undefined;
                  const confLabel = (confidence?.label as string) || "low";
                  const confColor = confLabel === "high" ? "bg-emerald-500" : confLabel === "medium" ? "bg-yellow-500" : "bg-white/20";

                  return (
                    <div key={i} className="p-4 rounded-xl bg-white/[0.03] border border-white/5">
                      <div className="flex items-start justify-between mb-2">
                        <div>
                          <span className="text-[#E76315] font-serif text-lg mr-2">#{i + 1}</span>
                          <strong className="text-white/90">{attendee?.name as string}</strong>
                          <span className="text-white/40 text-sm ml-2">{attendee?.title as string}{attendee?.company ? ` · ${attendee.company}` : ""}</span>
                        </div>
                        <div className="flex items-center gap-2">
                          <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${exp.relevance === "HIGH" ? "bg-emerald-500/20 text-emerald-400" : exp.relevance === "MEDIUM" ? "bg-yellow-500/20 text-yellow-400" : "bg-white/10 text-white/40"}`}>
                            {exp.relevance as string}
                          </span>
                          <span className={`w-2 h-2 rounded-full ${confColor}`} title={`Data confidence: ${confLabel}`} />
                        </div>
                      </div>
                      <p className="text-sm text-white/70 mb-2">{exp.why_they_matter as string}</p>
                      <div className="text-xs text-white/50 space-y-1">
                        <div><strong className="text-[#E76315]">Open with:</strong> {exp.conversation_opener as string}</div>
                        <div><strong className="text-purple-400">Deal potential:</strong> {exp.deal_potential as string}</div>
                        {(exp.caveats as string) && (
                          <div className="mt-1 px-2 py-1 rounded bg-yellow-500/5 border border-yellow-500/10 text-yellow-400/70">
                            ⚠ {exp.caveats as string}
                          </div>
                        )}
                        {(exp.key_evidence as string[])?.length > 0 && (
                          <div className="flex flex-wrap gap-1 mt-1">
                            {(exp.key_evidence as string[]).map((ev, j) => (
                              <span key={j} className="px-1.5 py-0.5 rounded text-[10px] bg-white/5 text-white/30">{ev}</span>
                            ))}
                          </div>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
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

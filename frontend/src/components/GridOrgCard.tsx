import { useState } from "react";
import { ChevronDown, ChevronUp, ExternalLink } from "lucide-react";

interface GridData {
  grid_name?: string;
  grid_tagline?: string;
  grid_description?: string;
  grid_description_long?: string;
  grid_type?: string;
  grid_sector?: string;
  grid_logo_url?: string;
  grid_founded?: string;
  grid_website?: string;
  grid_profile_url?: string;
  grid_socials?: Record<string, string>;
  grid_products?: Array<{
    name: string;
    description?: string;
    type?: string;
    type_slug?: string;
    is_main?: boolean;
  }>;
  grid_entities?: Array<{
    name: string;
    trade_name?: string;
    type?: string;
    country?: string;
  }>;
}

const SOCIAL_LABELS: Record<string, string> = {
  twitter_x: "Twitter / X",
  discord: "Discord",
  telegram: "Telegram",
  github: "GitHub",
  linkedin: "LinkedIn",
  youtube: "YouTube",
  medium: "Medium",
  Farcaster: "Farcaster",
};

export default function GridOrgCard({ grid }: { grid: GridData }) {
  const [expanded, setExpanded] = useState(false);

  if (!grid?.grid_description) return null;

  const socialEntries = Object.entries(grid.grid_socials ?? {}).filter(([, url]) => url);
  const products = grid.grid_products ?? [];
  const entities = grid.grid_entities ?? [];
  const hasDetails = products.length > 0 || entities.length > 0 || socialEntries.length > 0;

  return (
    <div className="rounded-xl bg-emerald-500/5 border border-emerald-500/10 overflow-hidden">
      {/* Compact header — always visible */}
      <div className="p-3">
        <div className="flex items-start gap-3">
          {/* Logo */}
          {grid.grid_logo_url ? (
            <img
              src={grid.grid_logo_url}
              alt={grid.grid_name}
              className="w-10 h-10 rounded-lg object-contain bg-white/5 p-1 shrink-0"
              onError={(e) => { (e.target as HTMLImageElement).style.display = "none"; }}
            />
          ) : (
            <div className="w-10 h-10 rounded-lg bg-emerald-500/10 flex items-center justify-center text-emerald-400 text-sm font-bold shrink-0">
              {(grid.grid_name ?? "?")[0]}
            </div>
          )}

          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="text-[9px] font-medium text-emerald-400 uppercase tracking-wider">Verified by The Grid</span>
              {grid.grid_sector && (
                <span className="px-1.5 py-0.5 rounded bg-emerald-500/10 text-emerald-400 text-[9px]">{grid.grid_sector}</span>
              )}
              {grid.grid_type && (
                <span className="px-1.5 py-0.5 rounded bg-white/5 text-white/30 text-[9px]">{grid.grid_type}</span>
              )}
            </div>
            {grid.grid_tagline && (
              <p className="text-[11px] text-white/40 mt-0.5 italic truncate">{grid.grid_tagline}</p>
            )}
            <p className="text-[11px] text-white/50 mt-1 line-clamp-2">{grid.grid_description}</p>
          </div>
        </div>

        {/* Expand toggle */}
        {hasDetails && (
          <button
            onClick={() => setExpanded(!expanded)}
            className="flex items-center gap-1 mt-2 text-[10px] text-emerald-400/60 hover:text-emerald-400 transition-colors"
          >
            {expanded ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
            {expanded ? "Show less" : `Show more${products.length ? ` · ${products.length} product${products.length > 1 ? "s" : ""}` : ""}${entities.length ? ` · ${entities.length} entit${entities.length > 1 ? "ies" : "y"}` : ""}`}
          </button>
        )}
      </div>

      {/* Expanded details */}
      {expanded && (
        <div className="border-t border-emerald-500/10 p-3 space-y-3">
          {/* Full description */}
          {grid.grid_description_long && grid.grid_description_long !== grid.grid_description && (
            <div>
              <div className="text-[9px] text-white/30 uppercase font-medium mb-1">About</div>
              <p className="text-[11px] text-white/50 leading-relaxed">{grid.grid_description_long}</p>
            </div>
          )}

          {/* Socials */}
          {socialEntries.length > 0 && (
            <div>
              <div className="text-[9px] text-white/30 uppercase font-medium mb-1.5">Socials</div>
              <div className="flex flex-wrap gap-1.5">
                {socialEntries.map(([slug, url]) => (
                  <a
                    key={slug}
                    href={url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="px-2 py-0.5 rounded bg-white/5 text-white/40 hover:text-white/70 text-[10px] transition-colors"
                  >
                    {SOCIAL_LABELS[slug] ?? slug}
                  </a>
                ))}
              </div>
            </div>
          )}

          {/* Products */}
          {products.length > 0 && (
            <div>
              <div className="text-[9px] text-white/30 uppercase font-medium mb-1.5">Products</div>
              <div className="space-y-1.5">
                {products.slice(0, 5).map((p) => (
                  <div key={p.name} className="flex items-start gap-2">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-1.5">
                        <span className="text-[11px] text-white/60 font-medium">{p.name}</span>
                        {p.is_main && (
                          <span className="px-1 py-0.5 rounded bg-emerald-500/10 text-emerald-400 text-[8px]">Main</span>
                        )}
                        {p.type && (
                          <span className="text-[9px] text-white/25">{p.type}</span>
                        )}
                      </div>
                      {p.description && (
                        <p className="text-[10px] text-white/35 line-clamp-1 mt-0.5">{p.description}</p>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Entities */}
          {entities.length > 0 && (
            <div>
              <div className="text-[9px] text-white/30 uppercase font-medium mb-1.5">Legal Entities</div>
              <div className="space-y-1">
                {entities.map((e) => (
                  <div key={e.name} className="text-[10px] text-white/40">
                    <span className="text-white/55">{e.trade_name || e.name}</span>
                    {e.trade_name && e.name !== e.trade_name && (
                      <span className="text-white/25"> ({e.name})</span>
                    )}
                    {(e.type || e.country) && (
                      <span className="text-white/25"> · {[e.type, e.country].filter(Boolean).join(", ")}</span>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Founded + Grid profile link */}
          <div className="flex items-center justify-between pt-1">
            {grid.grid_founded && (
              <span className="text-[9px] text-white/20">Founded {grid.grid_founded.slice(0, 4)}</span>
            )}
            {grid.grid_profile_url && (
              <a
                href={grid.grid_profile_url}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-1 text-[10px] text-emerald-400/60 hover:text-emerald-400 transition-colors"
              >
                View on The Grid <ExternalLink className="w-2.5 h-2.5" />
              </a>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

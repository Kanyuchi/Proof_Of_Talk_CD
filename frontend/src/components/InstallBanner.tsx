import { useEffect, useState } from "react";
import { useLocation } from "react-router-dom";
import { Download, X } from "lucide-react";

// Chrome / Edge / Samsung Internet fire `beforeinstallprompt` when the
// site meets PWA installability criteria (we have a manifest + sw.js).
// Safari/iOS don't fire it — we render iOS-specific copy instead.

interface BeforeInstallPromptEvent extends Event {
  readonly platforms: string[];
  readonly userChoice: Promise<{ outcome: "accepted" | "dismissed"; platform: string }>;
  prompt(): Promise<void>;
}

const DISMISS_KEY = "pot_install_banner_dismissed_at";
const DISMISS_TTL_MS = 14 * 24 * 60 * 60 * 1000; // 14 days

function isInstalled(): boolean {
  // Standalone mode = launched from home-screen icon.
  if (window.matchMedia("(display-mode: standalone)").matches) return true;
  // iOS Safari sets navigator.standalone when added to home screen.
  if ((window.navigator as { standalone?: boolean }).standalone === true) return true;
  return false;
}

function isIOS(): boolean {
  const ua = navigator.userAgent.toLowerCase();
  // iPadOS now reports as Mac; check for touch points too.
  if (/iphone|ipod/.test(ua)) return true;
  if (/macintosh/.test(ua) && navigator.maxTouchPoints > 1) return true;
  return false;
}

function recentlyDismissed(): boolean {
  const ts = Number(localStorage.getItem(DISMISS_KEY) || 0);
  return ts > 0 && Date.now() - ts < DISMISS_TTL_MS;
}

export default function InstallBanner() {
  const location = useLocation();
  const [installEvent, setInstallEvent] = useState<BeforeInstallPromptEvent | null>(null);
  const [showIOSHint, setShowIOSHint] = useState(false);
  const [dismissed, setDismissed] = useState(false);

  // Suppress on magic-link routes — the in-page "Set your password" CTA owns
  // the top real-estate for first-impression conversion. The banner returns
  // once the visitor claims an account and lands on /matches.
  const isMagicLink = location.pathname.startsWith("/m/");

  useEffect(() => {
    if (isInstalled() || recentlyDismissed()) return;

    // Android / desktop Chrome path.
    const handler = (e: Event) => {
      e.preventDefault();
      setInstallEvent(e as BeforeInstallPromptEvent);
    };
    window.addEventListener("beforeinstallprompt", handler as EventListener);

    // iOS path — no native prompt event, so we show our own copy.
    // Only on mobile-sized viewports; desktop Safari doesn't install PWAs.
    if (isIOS() && window.innerWidth < 768) {
      setShowIOSHint(true);
    }

    return () => window.removeEventListener("beforeinstallprompt", handler as EventListener);
  }, []);

  const handleInstall = async () => {
    if (!installEvent) return;
    await installEvent.prompt();
    const choice = await installEvent.userChoice;
    if (choice.outcome === "accepted") {
      setInstallEvent(null);
    } else {
      handleDismiss();
    }
  };

  const handleDismiss = () => {
    localStorage.setItem(DISMISS_KEY, String(Date.now()));
    setDismissed(true);
  };

  if (dismissed) return null;
  if (isMagicLink) return null;
  if (!installEvent && !showIOSHint) return null;

  return (
    <div className="fixed top-0 inset-x-0 z-50 px-3 pt-[calc(env(safe-area-inset-top)+0.75rem)] sm:hidden">
      <div className="rounded-xl bg-[#1a1a1a]/95 border border-[#E76315]/30 backdrop-blur-xl shadow-2xl p-3 flex items-center gap-3">
        <div className="w-10 h-10 rounded-lg bg-[#E76315] flex items-center justify-center shrink-0">
          <Download className="w-5 h-5 text-black" />
        </div>
        <div className="flex-1 min-w-0">
          {installEvent ? (
            <>
              <div className="text-sm font-semibold text-white">Install PoT Matchmaker</div>
              <div className="text-[11px] text-white/50">Open as an app — full-screen, faster.</div>
            </>
          ) : (
            <>
              <div className="text-sm font-semibold text-white">Install PoT Matchmaker</div>
              <div className="text-[11px] text-white/50">Tap <span className="text-white/80">Share</span> → <span className="text-white/80">Add to Home Screen</span></div>
            </>
          )}
        </div>
        {installEvent && (
          <button
            onClick={handleInstall}
            className="shrink-0 px-3 py-1.5 rounded-lg bg-[#E76315] text-black text-xs font-semibold hover:bg-[#FF833A] transition-all"
          >
            Install
          </button>
        )}
        <button
          onClick={handleDismiss}
          className="shrink-0 w-8 h-8 flex items-center justify-center rounded-lg text-white/40 hover:text-white hover:bg-white/5 transition-all"
          aria-label="Dismiss install prompt"
        >
          <X className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
}

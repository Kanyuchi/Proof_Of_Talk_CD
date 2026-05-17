import { useState } from "react";
import { Brain, X } from "lucide-react";
import ChatPanel from "./ChatPanel";

export default function ChatWidget() {
  const [open, setOpen] = useState(false);

  return (
    <>
      {/* Floating button — lifted above the mobile bottom-tab bar so it
          doesn't cover the right-most tab (Sign out / Dashboard). */}
      <button
        onClick={() => setOpen((v) => !v)}
        className={`fixed bottom-[calc(env(safe-area-inset-bottom)+5rem)] sm:bottom-6 right-4 sm:right-6 z-50 w-14 h-14 rounded-full shadow-2xl flex items-center justify-center transition-all duration-200 ${
          open
            ? "bg-white/10 border border-white/20 text-white/60 scale-90"
            : "bg-gradient-to-br from-[#E76315] to-[#D35400] text-black hover:scale-110"
        }`}
        aria-label="Open AI Concierge"
      >
        {open ? <X className="w-5 h-5" /> : <Brain className="w-6 h-6" />}
      </button>

      {/* Chat panel — full-width on mobile (minus 1rem gutter each side)
          and taller, so the keyboard doesn't shrink it to nothing. */}
      {open && (
        <div className="fixed bottom-36 sm:bottom-24 right-4 sm:right-6 left-4 sm:left-auto z-50 sm:w-[380px] h-[70vh] sm:h-[520px] max-h-[600px] rounded-2xl bg-[#0d0d15] border border-white/10 shadow-2xl flex flex-col overflow-hidden animate-in slide-in-from-bottom-4 duration-200">
          <ChatPanel onClose={() => setOpen(false)} />
        </div>
      )}
    </>
  );
}

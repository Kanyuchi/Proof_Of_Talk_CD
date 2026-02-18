import { useState } from "react";
import { Brain, X } from "lucide-react";
import ChatPanel from "./ChatPanel";

export default function ChatWidget() {
  const [open, setOpen] = useState(false);

  return (
    <>
      {/* Floating button */}
      <button
        onClick={() => setOpen((v) => !v)}
        className={`fixed bottom-6 right-6 z-50 w-14 h-14 rounded-full shadow-2xl flex items-center justify-center transition-all duration-200 ${
          open
            ? "bg-white/10 border border-white/20 text-white/60 scale-90"
            : "bg-gradient-to-br from-amber-400 to-amber-600 text-black hover:scale-110"
        }`}
        aria-label="Open AI Concierge"
      >
        {open ? <X className="w-5 h-5" /> : <Brain className="w-6 h-6" />}
      </button>

      {/* Chat panel */}
      {open && (
        <div className="fixed bottom-24 right-6 z-50 w-[380px] h-[520px] rounded-2xl bg-[#0d0d15] border border-white/10 shadow-2xl flex flex-col overflow-hidden animate-in slide-in-from-bottom-4 duration-200">
          <ChatPanel onClose={() => setOpen(false)} />
        </div>
      )}
    </>
  );
}

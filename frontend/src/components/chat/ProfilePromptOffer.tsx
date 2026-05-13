import { useState } from "react";
import { Sparkles } from "lucide-react";
import {
  draftField,
  saveDraftedField,
  declineProfilePrompt,
  type OfferableField,
} from "../../api/client";

interface Props {
  field: OfferableField;
  completenessPct: number;
  onResolved: () => void;
}

type Phase = "idle" | "drafting" | "picking" | "editing" | "saving" | "saved";

const FIELD_LABEL: Record<OfferableField, string> = {
  goals: "conference goals",
  target_companies: "target companies",
  interests: "Web3 interests",
};

const FIELD_PROMPT_VERB: Record<OfferableField, string> = {
  goals: "draft your conference goals",
  target_companies: "suggest companies you should prioritise meeting",
  interests: "suggest Web3 sectors you likely follow",
};

export default function ProfilePromptOffer({
  field,
  completenessPct,
  onResolved,
}: Props) {
  const [phase, setPhase] = useState<Phase>("idle");
  const [candidates, setCandidates] = useState<string[]>([]);
  const [isSparse, setIsSparse] = useState(false);
  const [editingValue, setEditingValue] = useState("");
  const [error, setError] = useState<string | null>(null);

  const fieldLabel = FIELD_LABEL[field];

  const handleAccept = async () => {
    setPhase("drafting");
    setError(null);
    try {
      const res = await draftField(field);
      setCandidates(res.candidates);
      setIsSparse(res.is_sparse);
      setPhase("picking");
    } catch {
      setError(
        "Couldn't draft suggestions right now. You can edit this from your Profile page anytime.",
      );
      setPhase("idle");
    }
  };

  const handleDecline = async () => {
    try {
      await declineProfilePrompt(field);
    } catch {
      // Best-effort — local UI dismisses regardless
    }
    onResolved();
  };

  const handlePickCandidate = (candidate: string) => {
    setEditingValue(candidate);
    setPhase("editing");
  };

  const handleSave = async () => {
    const trimmed = editingValue.trim();
    if (!trimmed) {
      setError("Looks empty — try a few words.");
      return;
    }
    setPhase("saving");
    setError(null);
    try {
      await saveDraftedField(field, trimmed);
      setPhase("saved");
    } catch {
      setError("Save failed. Please try again from your Profile page.");
      setPhase("editing");
    }
  };

  return (
    <div className="flex items-start gap-2.5">
      <div className="w-7 h-7 rounded-full bg-[#E76315]/10 flex items-center justify-center shrink-0 mt-0.5">
        <Sparkles className="w-3.5 h-3.5 text-[#E76315]" />
      </div>
      <div className="flex-1 space-y-2.5">
        {/* Headline message */}
        <div className="bg-white/5 rounded-2xl rounded-tl-sm p-3 text-sm text-white/70">
          Your profile is{" "}
          <span className="text-white font-medium">{completenessPct}%</span>{" "}
          complete — I can {FIELD_PROMPT_VERB[field]} based on your role and
          profile. It'll sharpen your matches.
        </div>

        {/* Idle: Yes / Maybe later */}
        {phase === "idle" && (
          <div className="flex flex-wrap gap-2">
            <button
              onClick={handleAccept}
              className="px-3 py-1.5 rounded-full bg-[#E76315] text-black text-xs font-semibold hover:bg-[#FF833A] transition-all"
            >
              Yes, {field === "goals" ? "draft my goals" : "show me ideas"}
            </button>
            <button
              onClick={handleDecline}
              className="px-3 py-1.5 rounded-full bg-white/5 border border-white/10 text-white/60 text-xs hover:text-white hover:border-white/20 transition-all"
            >
              Maybe later
            </button>
          </div>
        )}

        {/* Drafting: spinner */}
        {phase === "drafting" && (
          <div className="text-xs text-white/40 px-1">
            Drafting suggestions…
          </div>
        )}

        {/* Picking: 2-3 chip buttons */}
        {phase === "picking" && (
          <div className="space-y-2">
            {isSparse && (
              <p className="text-[10px] text-white/30 uppercase font-medium px-1">
                Starting points — feel free to rewrite
              </p>
            )}
            <p className="text-xs text-white/50 px-1">
              Tap one to edit and save:
            </p>
            {candidates.map((c, i) => (
              <button
                key={i}
                onClick={() => handlePickCandidate(c)}
                className="block w-full text-left px-3 py-2 rounded-xl bg-white/[0.03] border border-white/10 text-sm text-white/70 hover:text-white hover:border-[#E76315]/40 hover:bg-white/[0.06] transition-all"
              >
                {c}
              </button>
            ))}
            <button
              onClick={handleDecline}
              className="text-[11px] text-white/30 hover:text-white/60 transition-all px-1"
            >
              None of these — skip
            </button>
          </div>
        )}

        {/* Editing: textarea + Save/Cancel */}
        {(phase === "editing" || phase === "saving") && (
          <div className="space-y-2 bg-white/[0.03] border border-white/10 rounded-xl p-2.5">
            <textarea
              value={editingValue}
              onChange={(e) => setEditingValue(e.target.value)}
              className="w-full bg-transparent text-sm text-white placeholder:text-white/30 focus:outline-none resize-none min-h-[72px]"
              placeholder={`Edit your ${fieldLabel}…`}
              disabled={phase === "saving"}
            />
            <div className="flex items-center justify-end gap-2">
              <button
                onClick={() => setPhase("picking")}
                disabled={phase === "saving"}
                className="px-3 py-1 rounded-lg text-xs text-white/50 hover:text-white transition-all disabled:opacity-40"
              >
                Cancel
              </button>
              <button
                onClick={handleSave}
                disabled={phase === "saving" || !editingValue.trim()}
                className="px-3 py-1 rounded-lg bg-[#E76315] text-black text-xs font-semibold hover:bg-[#FF833A] transition-all disabled:opacity-40"
              >
                {phase === "saving" ? "Saving…" : "Save"}
              </button>
            </div>
          </div>
        )}

        {/* Saved: confirmation */}
        {phase === "saved" && (
          <div className="space-y-2">
            <div className="bg-emerald-500/10 border border-emerald-500/20 rounded-xl p-2.5 text-xs text-emerald-300">
              Saved. I've kicked off a match refresh in the background — new
              recommendations will appear shortly.
            </div>
            <button
              onClick={onResolved}
              className="text-[11px] text-white/40 hover:text-white/70 transition-all px-1"
            >
              Continue chatting →
            </button>
          </div>
        )}

        {error && (
          <div className="text-[11px] text-red-400 px-1">{error}</div>
        )}
      </div>
    </div>
  );
}

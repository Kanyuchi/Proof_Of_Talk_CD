// frontend/src/components/PhotoUpload.tsx
import { useRef, useState } from "react";
import { Camera } from "lucide-react";
import { cropImageToSquareJpeg } from "../utils/cropImage";

type Props = {
  /** Uploads the processed blob; resolves to the new public photo URL. */
  uploadFn: (blob: Blob) => Promise<{ photo_url: string }>;
  /** Called with the new URL on success (e.g. to refresh cache/UI). */
  onUploaded?: (url: string) => void;
};

type State = "idle" | "processing" | "uploading" | "success" | "error";

export default function PhotoUpload({ uploadFn, onUploaded }: Props) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [state, setState] = useState<State>("idle");
  const [error, setError] = useState<string>("");

  async function handleFile(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    e.target.value = ""; // allow re-selecting the same file
    if (!file) return;
    setError("");
    try {
      setState("processing");
      const blob = await cropImageToSquareJpeg(file);
      setState("uploading");
      const { photo_url } = await uploadFn(blob);
      setState("success");
      onUploaded?.(photo_url);
    } catch (err: unknown) {
      const e = err as { response?: { data?: { detail?: string } }; message?: string };
      setState("error");
      setError(e?.response?.data?.detail || e?.message || "Upload failed.");
    }
  }

  const label =
    state === "processing" ? "Processing…" :
    state === "uploading" ? "Uploading…" :
    state === "success" ? "Photo updated" : "Upload / change photo";

  return (
    <div className="flex flex-col gap-1">
      <button
        type="button"
        onClick={() => inputRef.current?.click()}
        disabled={state === "processing" || state === "uploading"}
        className="inline-flex items-center gap-2 px-3 py-2 rounded-lg bg-white/5 border border-white/10 text-sm text-white/70 hover:text-white hover:border-[#E76315]/50 transition-all disabled:opacity-50"
      >
        <Camera className="w-4 h-4" />
        {label}
      </button>
      <input
        ref={inputRef}
        type="file"
        accept="image/*"
        aria-label="Upload or change profile photo"
        className="hidden"
        onChange={handleFile}
      />
      {state === "error" && <p className="text-xs text-red-400">{error}</p>}
    </div>
  );
}

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import QRCode from "react-qr-code";
import { QrCode, Copy, CheckCheck, Download } from "lucide-react";
import { getMyMagicLink } from "../api/client";

export default function QRCard() {
  const { data, isLoading } = useQuery({
    queryKey: ["my-magic-link"],
    queryFn: getMyMagicLink,
    staleTime: Infinity,
  });

  const [copied, setCopied] = useState(false);

  if (isLoading || !data) return null;

  const magicUrl = `${window.location.origin}/m/${data.magic_token}`;

  const handleCopy = () => {
    navigator.clipboard.writeText(magicUrl).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  };

  const handleDownload = () => {
    const svg = document.getElementById("qr-card-svg");
    if (!svg) return;
    const svgData = new XMLSerializer().serializeToString(svg);
    const canvas = document.createElement("canvas");
    const ctx = canvas.getContext("2d");
    const img = new Image();
    img.onload = () => {
      canvas.width = 512;
      canvas.height = 512;
      if (ctx) {
        ctx.fillStyle = "#ffffff";
        ctx.fillRect(0, 0, 512, 512);
        ctx.drawImage(img, 0, 0, 512, 512);
      }
      const a = document.createElement("a");
      a.download = "pot-matchmaker-qr.png";
      a.href = canvas.toDataURL("image/png");
      a.click();
    };
    img.src = "data:image/svg+xml;base64," + btoa(svgData);
  };

  return (
    <div className="p-6 rounded-2xl bg-white/[0.03] border border-white/10">
      <div className="flex items-center gap-2 mb-4">
        <QrCode className="w-5 h-5 text-[#E76315]" />
        <h3 className="font-semibold">Your QR Business Card</h3>
      </div>
      <p className="text-xs text-white/40 mb-4">
        Share this QR code at the event. Anyone who scans it sees your match profile instantly — no app needed.
      </p>

      <div className="flex flex-col items-center gap-4">
        <div className="bg-white p-4 rounded-xl">
          <QRCode
            id="qr-card-svg"
            value={magicUrl}
            size={180}
            level="M"
            fgColor="#0d0d1a"
            bgColor="#ffffff"
          />
        </div>

        <div className="flex items-center gap-2 w-full">
          <button
            onClick={handleCopy}
            className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl border border-white/10 text-sm text-white/60 hover:border-[#E76315]/30 hover:text-[#E76315] transition-all"
          >
            {copied ? (
              <><CheckCheck className="w-4 h-4" /> Copied!</>
            ) : (
              <><Copy className="w-4 h-4" /> Copy link</>
            )}
          </button>
          <button
            onClick={handleDownload}
            className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl border border-white/10 text-sm text-white/60 hover:border-[#E76315]/30 hover:text-[#E76315] transition-all"
          >
            <Download className="w-4 h-4" /> Save QR
          </button>
        </div>
      </div>
    </div>
  );
}

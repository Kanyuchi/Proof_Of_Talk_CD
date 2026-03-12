import { useState } from "react";
import type { Attendee } from "../types";

interface Props {
  attendee: Pick<Attendee, "name" | "company" | "enriched_profile">;
  size?: "sm" | "md" | "lg";
}

const sizes = {
  sm: "w-8 h-8 text-xs",
  md: "w-10 h-10 text-sm",
  lg: "w-14 h-14 text-base",
};

// Extract photo URL from enriched_profile — Proxycurl uses different key names
function getPhotoUrl(enriched: Record<string, unknown>): string | null {
  const candidates = [
    enriched?.profile_photo_url,
    enriched?.photo_url,
    (enriched?.linkedin as Record<string, unknown>)?.profile_pic_url,
    (enriched?.linkedin as Record<string, unknown>)?.photo_url,
  ];
  for (const c of candidates) {
    if (typeof c === "string" && c.startsWith("http")) return c;
  }
  return null;
}

export default function AttendeeAvatar({ attendee, size = "md" }: Props) {
  const [imgError, setImgError] = useState(false);
  const photoUrl = !imgError ? getPhotoUrl(attendee.enriched_profile ?? {}) : null;
  const initials = attendee.name
    .split(" ")
    .slice(0, 2)
    .map((w) => w[0])
    .join("")
    .toUpperCase();

  if (photoUrl) {
    return (
      <img
        src={photoUrl}
        alt={attendee.name}
        onError={() => setImgError(true)}
        className={`${sizes[size]} rounded-lg object-cover shrink-0 bg-white/5`}
      />
    );
  }

  // Deterministic color based on name
  const colors = [
    "bg-blue-500/20 text-blue-300",
    "bg-purple-500/20 text-purple-300",
    "bg-emerald-500/20 text-emerald-300",
    "bg-[#E76315]/20 text-[#FF833A]",
    "bg-pink-500/20 text-pink-300",
  ];
  const color = colors[initials.charCodeAt(0) % colors.length];

  return (
    <div
      className={`${sizes[size]} rounded-lg ${color} flex items-center justify-center font-semibold shrink-0`}
    >
      {initials}
    </div>
  );
}

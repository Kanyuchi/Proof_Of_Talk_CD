import { useState, useEffect } from "react";
import type { Attendee } from "../types";

interface Props {
  attendee: Pick<Attendee, "name" | "company" | "company_website" | "enriched_profile" | "photo_url"> & {
    email?: string;
  };
  size?: "sm" | "md" | "lg";
}

const sizes = {
  sm: "w-8 h-8 text-xs",
  md: "w-10 h-10 text-sm",
  lg: "w-14 h-14 text-base",
};

// Layer 1: explicit photo_url or enriched LinkedIn photo
function getExplicitPhoto(
  photoUrl: string | null | undefined,
  enriched: Record<string, unknown>,
): string | null {
  if (photoUrl) return photoUrl;
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

// Layer 3: Clearbit company logo from domain
function clearbitUrl(companyWebsite: string | null | undefined): string | null {
  if (!companyWebsite) return null;
  try {
    const url = companyWebsite.startsWith("http")
      ? companyWebsite
      : `https://${companyWebsite}`;
    const domain = new URL(url).hostname.replace(/^www\./, "");
    if (!domain || domain.includes(" ")) return null;
    return `https://logo.clearbit.com/${domain}`;
  } catch {
    return null;
  }
}

// Layer 2: Gravatar via SHA-256 (async, uses native Web Crypto)
async function gravatarUrl(email: string): Promise<string | null> {
  try {
    const clean = email.trim().toLowerCase();
    const encoded = new TextEncoder().encode(clean);
    const hashBuffer = await crypto.subtle.digest("SHA-256", encoded);
    const hex = Array.from(new Uint8Array(hashBuffer))
      .map((b) => b.toString(16).padStart(2, "0"))
      .join("");
    return `https://gravatar.com/avatar/${hex}?d=404&s=200&r=g`;
  } catch {
    return null;
  }
}

export default function AttendeeAvatar({ attendee, size = "md" }: Props) {
  const explicit = getExplicitPhoto(attendee.photo_url, attendee.enriched_profile ?? {});
  const clearbit = clearbitUrl(attendee.company_website);

  // Cycle: explicit → gravatar → clearbit → initials
  // We track which sources have failed so we can move to the next
  const [failedSources, setFailedSources] = useState<Set<string>>(new Set());
  const [gravatarSrc, setGravatarSrc] = useState<string | null>(null);

  // Compute Gravatar async once email is available
  useEffect(() => {
    if (!attendee.email || explicit) return;
    gravatarUrl(attendee.email).then(setGravatarSrc);
  }, [attendee.email, explicit]);

  const markFailed = (src: string) =>
    setFailedSources((prev) => new Set([...prev, src]));

  // Pick the first non-failed source
  const src =
    explicit && !failedSources.has(explicit)
      ? explicit
      : gravatarSrc && !failedSources.has(gravatarSrc)
      ? gravatarSrc
      : clearbit && !failedSources.has(clearbit)
      ? clearbit
      : null;

  const initials = attendee.name
    .split(" ")
    .slice(0, 2)
    .map((w) => w[0])
    .join("")
    .toUpperCase();

  const colors = [
    "bg-blue-500/20 text-blue-300",
    "bg-purple-500/20 text-purple-300",
    "bg-emerald-500/20 text-emerald-300",
    "bg-[#E76315]/20 text-[#FF833A]",
    "bg-pink-500/20 text-pink-300",
  ];
  const color = colors[initials.charCodeAt(0) % colors.length];

  if (src) {
    return (
      <img
        src={src}
        alt={attendee.name}
        onError={() => markFailed(src)}
        className={`${sizes[size]} rounded-lg object-cover shrink-0 bg-white/5`}
      />
    );
  }

  return (
    <div
      className={`${sizes[size]} rounded-lg ${color} flex items-center justify-center font-semibold shrink-0`}
    >
      {initials}
    </div>
  );
}

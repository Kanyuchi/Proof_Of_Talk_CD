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

// Layer 3: ui-avatars — always returns a styled letter avatar (no external dependency issues)
function uiAvatarsUrl(name: string): string {
  return `https://ui-avatars.com/api/?name=${encodeURIComponent(name)}&background=1a1a2e&color=E76315&size=200&bold=true&format=svg`;
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
  const uiAvatar = uiAvatarsUrl(attendee.name);

  // Cycle: explicit → gravatar → ui-avatars (always works)
  const [failedSources, setFailedSources] = useState<Set<string>>(new Set());
  const [gravatarSrc, setGravatarSrc] = useState<string | null>(null);

  // Compute Gravatar async once email is available
  useEffect(() => {
    if (!attendee.email || explicit) return;
    gravatarUrl(attendee.email).then(setGravatarSrc);
  }, [attendee.email, explicit]);

  const markFailed = (src: string) =>
    setFailedSources((prev) => new Set([...prev, src]));

  // Pick the first non-failed source; ui-avatars is always the final fallback
  const src =
    explicit && !failedSources.has(explicit)
      ? explicit
      : gravatarSrc && !failedSources.has(gravatarSrc)
      ? gravatarSrc
      : uiAvatar;

  return (
    <img
      src={src}
      alt={attendee.name}
      onError={src !== uiAvatar ? () => markFailed(src) : undefined}
      className={`${sizes[size]} rounded-lg object-cover shrink-0 bg-white/5`}
    />
  );
}

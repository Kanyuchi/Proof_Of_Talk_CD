import { Crown, Mic, Megaphone, User, Handshake, Lightbulb, DollarSign } from "lucide-react";

/** Normalize a twitter_handle field (which may be a handle, @handle, or full URL) to a clickable URL. */
export function twitterUrl(handle: string): string {
  const trimmed = handle.trim();
  if (trimmed.startsWith("http://") || trimmed.startsWith("https://")) return trimmed;
  const clean = trimmed.replace(/^@/, "");
  return `https://x.com/${clean}`;
}

// Conference time slots — June 2 & 3, 2026
export const CONFERENCE_SLOTS = [
  { day: "June 2", label: "Tue 2 Jun — Morning", slots: ["09:00", "09:30", "10:00", "10:30", "11:00", "11:30"] },
  { day: "June 2", label: "Tue 2 Jun — Afternoon", slots: ["13:00", "13:30", "14:00", "14:30", "15:00", "15:30", "16:00", "16:30"] },
  { day: "June 2", label: "Tue 2 Jun — Evening", slots: ["18:00", "18:30", "19:00"] },
  { day: "June 3", label: "Wed 3 Jun — Morning", slots: ["09:00", "09:30", "10:00", "10:30", "11:00", "11:30"] },
  { day: "June 3", label: "Wed 3 Jun — Afternoon", slots: ["13:00", "13:30", "14:00", "14:30", "15:00", "15:30", "16:00", "16:30"] },
];

// The physical spots an attendee can pick when booking a meeting (from the
// venue floor plan). Order matters: the first entry is the default selection.
export const MEETING_LOCATIONS = [
  "B2B Networking Lounge (Edge & Node)",
  "Concierge Desk",
  "Networking Area (Food & Beverages)",
] as const;

export const DEFAULT_MEETING_LOCATION = MEETING_LOCATIONS[0];

export function slotToISO(day: string, time: string): string {
  const dateStr = day === "June 2" ? "2026-06-02" : "2026-06-03";
  return `${dateStr}T${time}:00`;
}

/** True if a slot (Paris wall-clock) has already started. Compares against
 *  current Paris time regardless of the viewer's device timezone, so a slot
 *  that has passed at the venue is disabled for everyone. */
export function isSlotPast(iso: string): boolean {
  const slot = new Date(iso); // naive ISO → parsed as device-local wall-clock
  // Current Paris wall-clock, expressed in the same device-local frame.
  const parisNow = new Date(
    new Date().toLocaleString("en-US", { timeZone: "Europe/Paris" }),
  );
  return slot.getTime() < parisNow.getTime();
}

// Meeting/slot times must ALWAYS read as Louvre (Europe/Paris) wall-clock, never
// the viewer's device timezone — otherwise the app and the confirmation email
// disagree (e.g. app 18:00 vs email 16:00) for anyone not on a Paris clock.
const PARIS_TZ = "Europe/Paris";

/** Normalise a backend ISO string to a Paris wall-clock instant.
 *
 *  Every meeting/slot time carries a Paris WALL-CLOCK number, not a UTC instant:
 *   - free-slot chips come from `all_slots()` as NAIVE ISO ("2026-06-02T14:00:00");
 *   - a booked `meeting_time` comes from the `timestamptz` column with a spurious
 *     "+00" offset ("2026-06-02T14:00:00+00:00"). The slot picker sent a naive
 *     14:00 (the 14:00 Paris slot); the column glued "+00" on at write time. The
 *     offset is a STORAGE ARTIFACT - the number is still the Paris time booked.
 *  So we discard any offset and pin the wall-clock to Paris (CEST, UTC+02:00 - the
 *  conference is entirely within CEST, no DST change). Rendering in PARIS_TZ then
 *  shows the booked number verbatim (14:00 stays 14:00) on every device. We never
 *  treat the "+00" as real UTC - that would shift 14:00 -> 16:00. */
function toInstant(iso: string): Date {
  const naive = iso.replace(/([zZ])|([+-]\d{2}:?\d{2})$/, "");
  return new Date(`${naive}+02:00`);
}

export function formatMeetingTime(iso: string): string {
  const d = toInstant(iso);
  return d.toLocaleString("en-GB", {
    weekday: "short", day: "numeric", month: "long",
    hour: "2-digit", minute: "2-digit",
    timeZone: PARIS_TZ,
  }) + " (Louvre time)";
}

/** Compact slot label for one-click-book chips, e.g. "Tue 09:30" (Louvre time). */
export function formatSlotChip(iso: string): string {
  const parts = new Intl.DateTimeFormat("en-GB", {
    weekday: "short", hour: "2-digit", minute: "2-digit",
    hour12: false, timeZone: PARIS_TZ,
  }).formatToParts(toInstant(iso));
  const get = (t: string) => parts.find((p) => p.type === t)?.value ?? "";
  return `${get("weekday")} ${get("hour")}:${get("minute")}`;
}

export function downloadICS(
  meetingTime: string,
  _attendeeName: string,
  matchedName: string,
  matchedCompany: string,
  location: string,
  explanation: string,
) {
  const start = toInstant(meetingTime);
  const end = new Date(start.getTime() + 30 * 60 * 1000); // 30-min block
  const fmt = (d: Date) =>
    d.toISOString().replace(/[-:]/g, "").split(".")[0] + "Z";
  const ics = [
    "BEGIN:VCALENDAR",
    "VERSION:2.0",
    "PRODID:-//POT Matchmaker//POT 2026//EN",
    "BEGIN:VEVENT",
    `UID:${Date.now()}@pot2026.com`,
    `DTSTAMP:${fmt(new Date())}`,
    `DTSTART:${fmt(start)}`,
    `DTEND:${fmt(end)}`,
    `SUMMARY:POT 2026 Meeting — ${matchedName} (${matchedCompany})`,
    `DESCRIPTION:${explanation.replace(/\n/g, "\\n")}`,
    `LOCATION:${location}`,
    "END:VEVENT",
    "END:VCALENDAR",
  ].join("\r\n");

  const blob = new Blob([ics], { type: "text/calendar" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `POT2026_${matchedName.replace(/\s+/g, "_")}.ics`;
  a.click();
  URL.revokeObjectURL(url);
}

export const matchTypeConfig = {
  complementary: {
    icon: Handshake,
    label: "Complementary",
    color: "text-blue-400",
    bg: "bg-blue-400/10 border-blue-400/20",
    leftBorder: "border-l-blue-400/70",
    description: "One party has what the other needs",
  },
  non_obvious: {
    icon: Lightbulb,
    label: "Non-Obvious",
    color: "text-purple-400",
    bg: "bg-purple-400/10 border-purple-400/20",
    leftBorder: "border-l-purple-400/70",
    description: "Different sectors, similar underlying problems",
  },
  deal_ready: {
    icon: DollarSign,
    label: "Deal Ready",
    color: "text-emerald-400",
    bg: "bg-emerald-400/10 border-emerald-400/20",
    leftBorder: "border-l-emerald-400/70",
    description: "Both parties positioned to transact",
  },
} as const;

export const ticketIcons: Record<string, React.ReactNode> = {
  vip: <Crown className="w-3 h-3" />,
  speaker: <Mic className="w-3 h-3" />,
  sponsor: <Megaphone className="w-3 h-3" />,
  delegate: <User className="w-3 h-3" />,
};

// Build a natural icebreaker opener from match data.
// Prioritises action_items (specific discussion topics) over raw synergy strings,
// and falls back to the person's title/company when those aren't available.
export function buildIcebreaker(
  matchedName: string,
  matchedTitle?: string,
  matchedCompany?: string,
  topics?: string[],
): string {
  const firstName = matchedName.split(" ")[0];
  const topic = topics?.find((t) => t.length < 140);
  const cleanTopic = topic
    ? topic.replace(/^discuss\s+/i, "").replace(/^explore\s+/i, "")
    : null;

  if (cleanTopic && matchedCompany) {
    return `Hi ${firstName}, the POT 2026 AI matched us as a strong connection. Given your work at ${matchedCompany}, I'd love to explore ${cleanTopic} at the conference. Are you free on June 2 or 3?`;
  }
  if (cleanTopic) {
    return `Hi ${firstName}, I'd love to explore ${cleanTopic} with you at POT 2026. Are you free on June 2 or 3?`;
  }
  if (matchedTitle && matchedCompany) {
    return `Hi ${firstName}, I noticed you're ${matchedTitle} at ${matchedCompany}. The POT 2026 AI flagged us as a strong match — I'd love to connect briefly at the conference. Are you free on June 2 or 3?`;
  }
  return `Hi ${firstName}, the POT 2026 matchmaker highlighted us as a strong connection. I'd love to meet briefly during the conference — are you available on June 2 or 3?`;
}

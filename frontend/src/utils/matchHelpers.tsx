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
  { day: "June 2", label: "Mon 2 Jun — Morning", slots: ["09:00", "09:30", "10:00", "10:30", "11:00", "11:30"] },
  { day: "June 2", label: "Mon 2 Jun — Afternoon", slots: ["14:00", "14:30", "15:00", "15:30", "16:00", "16:30"] },
  { day: "June 2", label: "Mon 2 Jun — Evening", slots: ["18:00", "18:30", "19:00"] },
  { day: "June 3", label: "Tue 3 Jun — Morning", slots: ["09:00", "09:30", "10:00", "10:30", "11:00", "11:30"] },
  { day: "June 3", label: "Tue 3 Jun — Afternoon", slots: ["14:00", "14:30", "15:00", "15:30", "16:00", "16:30"] },
];

export function slotToISO(day: string, time: string): string {
  const dateStr = day === "June 2" ? "2026-06-02" : "2026-06-03";
  return `${dateStr}T${time}:00`;
}

export function formatMeetingTime(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleString("en-GB", {
    weekday: "short", day: "numeric", month: "long",
    hour: "2-digit", minute: "2-digit",
  });
}

export function downloadICS(
  meetingTime: string,
  _attendeeName: string,
  matchedName: string,
  matchedCompany: string,
  location: string,
  explanation: string,
) {
  const start = new Date(meetingTime);
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

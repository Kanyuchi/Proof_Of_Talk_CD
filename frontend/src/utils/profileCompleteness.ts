/**
 * Profile-completeness computation, shared between AttendeeMatches (admin
 * view) and MyMatches (where it now also gates how many matches the user
 * sees — added 2026-05-13 to drive self-enrichment).
 *
 * The 8 fields below are the ones that materially feed the matching
 * pipeline. Each is equal-weight; perfect == 100%.
 */
import type { Attendee } from "../types";

export interface CompletenessField {
  label: string;
  ok: boolean;
  /** UX copy used on the unlock card when this field is missing. */
  suggestion: string;
}

export function profileCompleteness(attendee: Attendee | undefined | null): {
  percent: number;
  fields: CompletenessField[];
  missingHighImpact: CompletenessField[];
} {
  if (!attendee) {
    return { percent: 0, fields: [], missingHighImpact: [] };
  }
  const fields: CompletenessField[] = [
    {
      label: "Goals",
      ok: !!(attendee.goals && attendee.goals.trim()),
      suggestion: "Tell us what you're looking for at the conference",
    },
    {
      label: "Who you want to meet",
      ok: !!(attendee.target_companies && attendee.target_companies.trim()),
      suggestion: "Name companies or types of attendees you want to meet",
    },
    {
      label: "LinkedIn URL",
      ok: !!attendee.linkedin_url,
      suggestion: "Add your LinkedIn so the AI can read your experience",
    },
    {
      label: "Interests",
      ok: (attendee.interests?.length ?? 0) > 0,
      suggestion: "Pick the sectors you care about",
    },
    {
      label: "Twitter",
      ok: !!attendee.twitter_handle,
      suggestion: "Add your Twitter/X handle",
    },
    {
      label: "Company website",
      ok: !!attendee.company_website,
      suggestion: "Link your company site so the AI understands your offering",
    },
    {
      label: "Profile photo",
      ok: !!attendee.photo_url,
      suggestion: "Upload a photo so people recognise you at the venue",
    },
    {
      label: "Title & company",
      ok: !!(attendee.title && attendee.company),
      suggestion: "Make sure your title and company are filled in",
    },
  ];
  const okCount = fields.filter((f) => f.ok).length;
  const percent = Math.round((okCount / fields.length) * 100);

  // Goals + Who-you-want-to-meet + LinkedIn are the three with the
  // biggest match-quality impact — surface them first on the unlock card.
  const highImpactLabels = new Set(["Goals", "Who you want to meet", "LinkedIn URL"]);
  const missingHighImpact = fields.filter((f) => !f.ok && highImpactLabels.has(f.label));

  return { percent, fields, missingHighImpact };
}

/**
 * How many matches the user is allowed to see, based on profile completeness.
 * Sparse profiles get the top few; only complete profiles see the long tail.
 * This is the locked-match-preview mechanic that drives self-enrichment.
 */
export function visibleMatchLimit(percent: number, totalMatches: number): number {
  if (percent >= 80) return totalMatches;
  if (percent >= 60) return Math.min(totalMatches, 8);
  if (percent >= 40) return Math.min(totalMatches, 5);
  return Math.min(totalMatches, 3);
}

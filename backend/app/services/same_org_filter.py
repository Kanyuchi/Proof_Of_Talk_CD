"""
Same-organization filter for the matching engine.

Two attendees who work at the same organization should not be recommended
to each other as matches — they already know each other or have direct
internal access. Reported 2026-05-29 by Erin McMahon (Axe Compute) whose
#1 recommended match was Chris Miglino, the CEO of her own company.

Detection is OR-of-two-signals:
  1. Normalized company name match (case + whitespace + corp-suffix
     insensitive). Generic / freelance / single-person values like "self",
     "freelance", "consultant", "n/a" never match each other.
  2. Corporate email domain match, excluding personal/freemail providers
     like gmail.com, outlook.com. Two people on @gmail.com are NOT the
     same org; two on @elliptic.co are.

The filter is intentionally strict: it requires either an exact normalized
match OR a shared corporate domain. Fuzzy matching ("Acme" vs "Acme Inc."
collapses to the same root via CORP_SUFFIXES stripping, but "Acme" vs
"Acme Computing" stays distinct). If fuzzier behaviour is needed later
we can layer SequenceMatcher on top — but starting strict avoids false
positives that would silently kill legitimate cross-company matches.
"""

from typing import Any

PERSONAL_EMAIL_DOMAINS: set[str] = {
    "gmail.com", "googlemail.com",
    "yahoo.com", "yahoo.co.uk", "ymail.com", "rocketmail.com",
    "outlook.com", "hotmail.com", "live.com", "msn.com",
    "icloud.com", "me.com", "mac.com",
    "proton.me", "protonmail.com", "pm.me",
    "aol.com", "gmx.com", "gmx.de", "gmx.net",
    "fastmail.com", "yandex.com", "yandex.ru",
    "mail.com", "zoho.com",
    "qq.com", "163.com", "126.com", "mail.ru",
    "web.de", "t-online.de",
    "tutanota.com", "tuta.io",
    # PoT-allocated speaker mailboxes — synthesised by the 1000 Minds
    # sync, shared across unrelated speakers, so treat as personal-equivalent.
    "speaker.proofoftalk.io",
}

GENERIC_COMPANY_VALUES: set[str] = {
    "", "self", "self-employed", "selfemployed", "self employed",
    "freelance", "freelancer", "independent",
    "consultant", "consulting",
    "n/a", "na", "none", "-", "--",
    "private", "individual",
    "stealth", "stealth startup", "stealth mode",
    "tbd", "tba", "unemployed",
}

CORP_SUFFIXES: tuple[str, ...] = (
    " inc", " inc.", " ltd", " ltd.", " llc", " llc.",
    " corp", " corp.", " corporation", " co", " co.",
    " gmbh", " s.a.", " sa", " ag", " bv", " s.a.r.l.", " sarl",
    " ab", " oy", " plc", " pvt", " pvt.",
    " group", " holdings", " holding",
    ", inc", ", inc.", ", ltd", ", ltd.", ", llc", ", corp",
)


def _normalize_company(value: str) -> str:
    if not value:
        return ""
    v = " ".join(value.strip().lower().split())
    if v in GENERIC_COMPANY_VALUES:
        return ""
    changed = True
    while changed:
        changed = False
        for suffix in CORP_SUFFIXES:
            if v.endswith(suffix):
                v = v[: -len(suffix)].rstrip(" ,.")
                changed = True
                break
    if v in GENERIC_COMPANY_VALUES:
        return ""
    return v


def _email_domain(value: str) -> str:
    if not value or "@" not in value:
        return ""
    return value.split("@", 1)[1].strip().lower()


def is_same_organization(a: Any, b: Any) -> bool:
    """Return True if attendees a and b appear to work at the same org.

    Accepts ORM Attendee instances or dicts (uses getattr/get).
    """
    def _get(obj: Any, attr: str) -> str:
        if isinstance(obj, dict):
            return (obj.get(attr) or "")
        return (getattr(obj, attr, "") or "")

    company_a = _normalize_company(_get(a, "company"))
    company_b = _normalize_company(_get(b, "company"))
    if company_a and company_b and company_a == company_b:
        return True

    domain_a = _email_domain(_get(a, "email"))
    domain_b = _email_domain(_get(b, "email"))
    if domain_a and domain_b and domain_a == domain_b:
        if domain_a not in PERSONAL_EMAIL_DOMAINS:
            return True

    return False

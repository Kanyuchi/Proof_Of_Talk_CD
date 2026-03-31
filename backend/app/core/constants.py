"""Canonical vertical tag definitions shared across classification, matching, and API."""

VERTICAL_DISPLAY_NAMES: dict[str, str] = {
    "tokenisation_of_finance": "Tokenisation of Finance",
    "infrastructure_and_scaling": "Infrastructure & Scaling",
    "decentralized_finance": "Decentralized Finance",
    "ai_depin_frontier_tech": "AI, DePIN & Frontier Tech",
    "policy_regulation_macro": "Policy, Regulation & Macro",
    "ecosystem_and_foundations": "Ecosystem & Foundations",
    "investment_and_capital_markets": "Investment & Capital Markets",
    "culture_media_gaming": "Culture, Media & Gaming",
    "bitcoin": "Bitcoin",
    "prediction_markets": "Prediction Markets",
    "decentralized_ai": "Decentralized AI",
    "privacy": "Privacy",
}

VALID_VERTICALS: list[str] = list(VERTICAL_DISPLAY_NAMES.keys())

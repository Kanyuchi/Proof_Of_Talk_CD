export const VERTICAL_DISPLAY_NAMES: Record<string, string> = {
  tokenisation_of_finance: "Tokenisation of Finance",
  infrastructure_and_scaling: "Infrastructure & Scaling",
  decentralized_finance: "Decentralized Finance",
  ai_depin_frontier_tech: "AI, DePIN & Frontier Tech",
  policy_regulation_macro: "Policy, Regulation & Macro",
  ecosystem_and_foundations: "Ecosystem & Foundations",
  investment_and_capital_markets: "Investment & Capital Markets",
  culture_media_gaming: "Culture, Media & Gaming",
  bitcoin: "Bitcoin",
  prediction_markets: "Prediction Markets",
  decentralized_ai: "Decentralized AI",
  privacy: "Privacy",
};

export function verticalDisplayName(tag: string): string {
  return VERTICAL_DISPLAY_NAMES[tag] ?? tag.replace(/_/g, " ");
}

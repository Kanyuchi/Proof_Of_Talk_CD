# POT Matchmaker — Sample Match Report

**Generated from 196 matches across 109 attendees.**
_Proof of Talk + X Ventures organiser staff (7) excluded from this report. Zohair Dehnadi and Victor Blas are kept as they use the matchmaker like any other VC._
Score range: 0.600 → 0.780, mean 0.711.

## How scoring works

Each match has three scores:
- **Embedding similarity** — cosine similarity of the two attendees' profile embeddings (text-embedding-3-small, 1536-dim). Pure semantic overlap.
- **Complementary score** — deterministic rerank based on sector pairing, intent alignment, and ICP signal-keyword overlap (does A offer what B is seeking?).
- **Overall score** — the final score used for ranking. Combines similarity + complementary signals.

Match types:
- 💼 `deal_ready` — both parties in a position to transact (investor + startup, buyer + seller).
- ✨ `non_obvious` — different sectors solving the same underlying problem.
- 🤝 `complementary` — one party has what the other needs.

## Top matches (≥0.75)

### 🤝 Bruno Calabretta  ↔  Daniel Fratean
**Overall score: 0.78**  |  Match type: `complementary`  |  Embedding similarity: 0.62  |  Complementary: 0.85

- **Bruno Calabretta** — [VIP]
  - Intents: deal_making, knowledge_exchange, seeking_partnerships
  - LinkedIn: AI & Blockchain | Strategy & Ecosystem Growth | GTM & Community Development | Institutional Partnerships | LinkedIn Positioning | Public Speaker | Mos…
- **Daniel Fratean** — [DELEGATE]
  - Sectors: culture_media_gaming
  - Intents: knowledge_exchange, deal_making
  - LinkedIn: Independent Java Consultant

**Why they should meet (GPT-4o):**
> Daniel Fratean, with his media coverage focus, aligns well with Bruno Calabretta's need for media companies to increase conference visibility. Daniel can provide the necessary exposure for Web3 startups attending the conference, enhancing their visibility and credibility.

**Shared context:** sectors: culture_media_gaming | synergies: media coverage for Web3 startups, increased visibility for conference | action_items: Discuss potential media partnerships, Explore coverage opportunities for conference events, Identify key startups for feature stories

_Explanation confidence: 0.80_

---

### 🤝 pouneh bligaard  ↔  Mees Vlasveld
**Overall score: 0.78**  |  Match type: `complementary`  |  Embedding similarity: 0.65  |  Complementary: 0.85

- **pouneh bligaard** — Dragonflydigitalassets — [DELEGATE]
  - Sectors: investment_and_capital_markets, policy_regulation_macro, tokenisation_of_finance
  - Intents: deploying_capital, knowledge_exchange
  - LinkedIn: Co-Founder & Chief Investment Officer at Dragonfly Asset Management
- **Mees Vlasveld** — Investment Manager at Vanlanschotkempen — [DELEGATE]
  - Sectors: investment_and_capital_markets, tokenisation_of_finance, decentralized_finance
  - Intents: deploying_capital, deal_making, knowledge_exchange
  - LinkedIn: Investment Professional | Education Coordinator at CFA Society Netherlands | Author of “Bitcoin Treasury Companies”

**Why they should meet (GPT-4o):**
> Mees Vlasveld from Van Lanschot Kempen is seeking innovative investment opportunities in sustainable finance, aligning with Dragonfly Digital Assets' focus on bridging traditional finance with digital assets. Both parties are interested in tokenization and DeFi, providing a strong foundation for collaboration on sustainable investment products.

**Shared context:** sectors: investment_and_capital_markets, tokenisation_of_finance, decentralized_finance | synergies: sustainable finance strategies, institutional investment in DeFi | action_items: Discuss potential investment in tokenization platforms, Explore sustainable finance solutions in digital assets, Identify joint opportunities in DeFi protocols

_Explanation confidence: 0.80_

---

### 💼 Zohair Dehnadi  ↔  Victor Blas
**Overall score: 0.78**  |  Match type: `deal_ready`  |  Embedding similarity: 0.61  |  Complementary: 0.85

- **Zohair Dehnadi** — CEO at Proof of Talk — [VIP]
  - Sectors: investment_and_capital_markets, infrastructure_and_scaling, tokenisation_of_finance
  - Intents: seeking_partnerships, raising_capital, deal_making
  - Goals: Meet future business partners
  - LinkedIn: Investor | Founding Partner | Hiring!
  - Grid: Proof of Talk is a Web3 & AI networking event held in Paris.
- **Victor Blas** — Head of Investment at X Ventures — [VIP]
  - Sectors: investment_and_capital_markets, tokenisation_of_finance, infrastructure_and_scaling
  - Intents: deploying_capital, deal_making, seeking_partnerships
  - Goals: I want to meet early stage start up
  - LinkedIn: Venture Capitalist at X Ventures | Early investor in Web3 & Blockchain start-up | DeAI Accelerator
  - Grid: X Ventures is a venture capital firm and studio that invests in Web3 and blockchain startups, providing funding and strategic support for early-stage companies.

**Why they should meet (GPT-4o):**
> Victor Blas from X Ventures is actively seeking early-stage startups in institutional custody and layer-2 solutions, aligning with Zohair Dehnadi's interest in blockchain infrastructure and tokenization. Both parties are deal-ready, with Victor's capital deployment capabilities matching Zohair's goal of raising capital and forming strategic partnerships.

**Shared context:** sectors: investment_and_capital_markets, infrastructure_and_scaling | synergies: capital deployment for blockchain infrastructure, strategic partnerships in tokenization | action_items: Discuss potential investment in blockchain infrastructure projects, Explore co-investment opportunities in tokenization startups, Evaluate layer-2 solutions for institutional custody

_Explanation confidence: 0.80_

---

### 💼 Max Kantelia  ↔  Victor Blas
**Overall score: 0.78**  |  Match type: `deal_ready`  |  Embedding similarity: 0.60  |  Complementary: 0.85

- **Max Kantelia** — CEO & Co-Founder at Zilliqa Group — [VIP]
  - Sectors: infrastructure_and_scaling, ecosystem_and_foundations, investment_and_capital_markets, decentralized_ai
  - Intents: seeking_partnerships, knowledge_exchange, deal_making
  - Goals: Max Kantelia is a serial entrepreneur and a primary architect of the high-performance blockchain ecosystem as the co-founder of Zilliqa. With over 25 years of experience in deep te…
  - LinkedIn: Divisional Account Director
  - Grid: Zilliqa is a Layer 1 blockchain that lets developers and enterprises build scalable applications using EVM-compatible tools and customizable application-specific shards.
- **Victor Blas** — Head of Investment at X Ventures — [VIP]
  - Sectors: investment_and_capital_markets, tokenisation_of_finance, infrastructure_and_scaling
  - Intents: deploying_capital, deal_making, seeking_partnerships
  - Goals: I want to meet early stage start up
  - LinkedIn: Venture Capitalist at X Ventures | Early investor in Web3 & Blockchain start-up | DeAI Accelerator
  - Grid: X Ventures is a venture capital firm and studio that invests in Web3 and blockchain startups, providing funding and strategic support for early-stage companies.

**Why they should meet (GPT-4o):**
> Victor Blas from X Ventures is actively seeking early-stage startups in the blockchain space, aligning with Max Kantelia's focus on integrating decentralized infrastructure with consumer experiences. This match is deal-ready as Victor is deploying capital and Max is seeking partnerships, creating a strong opportunity for investment in Zilliqa's innovative projects.

**Shared context:** sectors: infrastructure_and_scaling, investment_and_capital_markets | synergies: capital deployment for blockchain infrastructure, investment in scalable consumer engagement solutions | action_items: Discuss investment opportunities in Zilliqa's projects, Explore potential for co-investment in spatial web applications, Evaluate strategic partnerships for scaling blockchain solutions

_Explanation confidence: 0.80_

---

## High (0.70–0.75)

### 🤝 Bruno Calabretta  ↔  Richard Holmes
**Overall score: 0.74**  |  Match type: `complementary`  |  Embedding similarity: 0.60  |  Complementary: 0.78

- **Bruno Calabretta** — [VIP]
  - Intents: deal_making, knowledge_exchange, seeking_partnerships
  - LinkedIn: AI & Blockchain | Strategy & Ecosystem Growth | GTM & Community Development | Institutional Partnerships | LinkedIn Positioning | Public Speaker | Mos…
- **Richard Holmes** — [DELEGATE]
  - Sectors: investment_and_capital_markets, infrastructure_and_scaling, ecosystem_and_foundations
  - Intents: knowledge_exchange, technology_evaluation

**Why they should meet (GPT-4o):**
> Richard Holmes offers strategic insights and capital for blockchain investments, aligning with Bruno's goal of connecting institutional investors with vetted Web3 projects. This match can facilitate investment discussions and strategic partnerships.

**Shared context:** sectors: investment_and_capital_markets, infrastructure_and_scaling | synergies: capital for blockchain startups, strategic partnerships for scaling | action_items: Discuss investment opportunities in Web3 projects, Explore strategic partnerships for infrastructure scaling, Identify startups needing seed funding

_Explanation confidence: 0.76_

---

### 💼 Hedeyeh Taheri  ↔  pouneh bligaard
**Overall score: 0.74**  |  Match type: `deal_ready`  |  Embedding similarity: 0.59  |  Complementary: 0.75

- **Hedeyeh Taheri** — Atos — [DELEGATE]
  - Sectors: ai_depin_frontier_tech, infrastructure_and_scaling, decentralized_ai
  - Intents: technology_evaluation, knowledge_exchange, seeking_partnerships
  - LinkedIn: Head of Client Innovation for Financial Services EMEA at Atos
- **pouneh bligaard** — Dragonflydigitalassets — [DELEGATE]
  - Sectors: investment_and_capital_markets, policy_regulation_macro, tokenisation_of_finance
  - Intents: deploying_capital, knowledge_exchange
  - LinkedIn: Co-Founder & Chief Investment Officer at Dragonfly Asset Management

**Why they should meet (GPT-4o):**
> Pouneh Bligaard from Dragonfly Digital Assets and Hedeyeh Taheri from Atos are both seeking strategic partnerships. Dragonfly's focus on bridging traditional finance with digital assets complements Atos's expertise in sustainable digital transformation, providing a strong foundation for collaboration in regulatory advancements and investment opportunities.

**Shared context:** sectors: investment_and_capital_markets, policy_regulation_macro | synergies: Atos's sustainable infrastructure solutions with Dragonfly's investment strategies | action_items: Explore regulatory advancements in digital assets, Discuss potential investment opportunities in sustainable digital transformation, Identify strategic partnerships to enhance both companies' offerings

_Explanation confidence: 0.75_

---

### ✨ Victor Blas  ↔  Xavier Gomez, MD
**Overall score: 0.72**  |  Match type: `non_obvious`  |  Embedding similarity: 0.65  |  Complementary: 0.75

- **Victor Blas** — Head of Investment at X Ventures — [VIP]
  - Sectors: investment_and_capital_markets, tokenisation_of_finance, infrastructure_and_scaling
  - Intents: deploying_capital, deal_making, seeking_partnerships
  - Goals: I want to meet early stage start up
  - LinkedIn: Venture Capitalist at X Ventures | Early investor in Web3 & Blockchain start-up | DeAI Accelerator
  - Grid: X Ventures is a venture capital firm and studio that invests in Web3 and blockchain startups, providing funding and strategic support for early-stage companies.
- **Xavier Gomez, MD** — Chief Operating Officer at Vancelian — [VIP]
  - Sectors: tokenisation_of_finance, infrastructure_and_scaling
  - Intents: seeking_partnerships, technology_evaluation, knowledge_exchange, regulatory_engagement
  - Goals: Xavier Gomez is the COO and Co-Founder of Invyo and a seasoned C-level executive with a deep background in investment banking and digital transformation. A recognized expert in the…
  - Grid: Vancelian helps you build wealth by combining traditional finance with blockchain technology through savings, investment, and digital payment solutions.

**Why they should meet (GPT-4o):**
> Xavier Gomez from Vancelian is focused on integrating AI into financial institutions, which could provide unique insights into enhancing operational efficiency for Victor Blas's portfolio companies. This non-obvious connection could lead to innovative solutions for scaling and compliance in Web3 projects.

**Shared context:** sectors: tokenisation_of_finance, infrastructure_and_scaling | synergies: AI-driven compliance solutions, operational efficiency in financial services, scaling Web3 projects | action_items: Discuss AI integration for operational efficiency, Explore compliance solutions for Web3 startups, Evaluate potential for strategic advisory roles

_Explanation confidence: 0.74_

---

## Medium (0.65–0.70)

### 🤝 Shaun Kutsanzira  ↔  Steve Wallace
**Overall score: 0.68**  |  Match type: `complementary`  |  Embedding similarity: 0.56  |  Complementary: 0.65

- **Shaun Kutsanzira** — Managing Director at The Nerds Int — [DELEGATE]
  - Sectors: infrastructure_and_scaling, policy_regulation_macro, ai_depin_frontier_tech
  - Intents: technology_evaluation, knowledge_exchange, seeking_partnerships
  - LinkedIn: ML Engineer | Economist | Data Scientist  | AI Automation & Strategy | Operations Management| GenAl &MLOps
- **Steve Wallace** — Co Founder, DeFi & Capital Markets at Monolythic — [DELEGATE]
  - Sectors: ecosystem_and_foundations, infrastructure_and_scaling
  - Intents: seeking_partnerships, ecosystem_expansion, business_development, knowledge_exchange
  - LinkedIn: Head of International Portfolio Management

**Why they should meet (GPT-4o):**
> Steve Wallace from Monolythic seeks strategic partnerships for ecosystem expansion, aligning with Shaun Kutsanzira's interest in blockchain infrastructure. Their collaboration could enhance cross-chain interoperability and drive adoption in the MENA region.

**Shared context:** sectors: ecosystem_and_foundations, infrastructure_and_scaling | synergies: ecosystem expansion, cross-chain interoperability | action_items: Discuss strategic partnerships in MENA, Explore cross-chain solutions for ecosystem growth, Evaluate infrastructure needs for regional adoption

_Explanation confidence: 0.70_

---

### ✨ Harry Horsfall  ↔  Nova Lorraine
**Overall score: 0.68**  |  Match type: `non_obvious`  |  Embedding similarity: 0.53  |  Complementary: 0.70

- **Harry Horsfall** — Flight3 — [VIP]
  - Sectors: culture_media_gaming, ecosystem_and_foundations, ai_depin_frontier_tech
  - Intents: seeking_partnerships, seeking_customers, knowledge_exchange
  - LinkedIn: Co-Founder - CEO @ Flight3
- **Nova Lorraine** — Founder & Creative Director at House of Nova — [VIP]
  - Sectors: culture_media_gaming
  - Intents: seeking_partnerships, knowledge_exchange, technology_evaluation
  - Goals: Nova Lorraine is an award-winning futurist, NASA T2X graduate, and a pioneer at the intersection of AI, Fashion, and Digital Sovereignty. In 2024, she made history as the first fas…
  - LinkedIn: Art on the Moon | Founder, House of Nova | Fashion × AI × Immersive Worlds | Filmmaker & Worldbuilder | Award-Winning Futurist 🇯🇲
  - Grid: House of Nova is a fashion and lifestyle brand merging couture with art and technology, offering designer collections and an AI-powered personal styling service.

**Why they should meet (GPT-4o):**
> Nova Lorraine from House of Nova is pioneering 'Phygital' couture using AI and blockchain, which can offer unique insights into integrating blockchain in aviation for customer experience enhancement. Both parties can explore innovative applications of blockchain in their respective fields.

**Shared context:** sectors: culture_media_gaming, infrastructure_and_scaling | synergies: AI and blockchain integration for customer experience, innovative blockchain applications in aviation | action_items: Discuss AI-driven customer experience enhancements in aviation, Explore blockchain applications in luxury retail and aviation, Identify potential collaborations in digital sovereignty

_Explanation confidence: 0.71_

---

### 💼 Leo Mercier  ↔  Victor Blas
**Overall score: 0.68**  |  Match type: `deal_ready`  |  Embedding similarity: 0.54  |  Complementary: 0.72

- **Leo Mercier** — Crowdform — [DELEGATE]
  - Sectors: infrastructure_and_scaling, ecosystem_and_foundations, culture_media_gaming
  - Intents: seeking_partnerships, technology_evaluation, knowledge_exchange
  - LinkedIn: Co-Founder at Crowdform
- **Victor Blas** — Head of Investment at X Ventures — [VIP]
  - Sectors: investment_and_capital_markets, tokenisation_of_finance, infrastructure_and_scaling
  - Intents: deploying_capital, deal_making, seeking_partnerships
  - Goals: I want to meet early stage start up
  - LinkedIn: Venture Capitalist at X Ventures | Early investor in Web3 & Blockchain start-up | DeAI Accelerator
  - Grid: X Ventures is a venture capital firm and studio that invests in Web3 and blockchain startups, providing funding and strategic support for early-stage companies.

**Why they should meet (GPT-4o):**
> Victor Blas from X Ventures is seeking early-stage startups for investment, aligning with Crowdform's expertise in developing Web3 applications. This presents a deal-ready opportunity for Crowdform to secure investment and scale their projects.

**Shared context:** sectors: investment_and_capital_markets, infrastructure_and_scaling | synergies: capital deployment for Web3 projects, scaling innovative solutions | action_items: Discuss investment opportunities in Crowdform's projects, Explore strategic partnerships for scaling, Identify potential co-investment opportunities

_Explanation confidence: 0.71_

---

## Borderline (0.60–0.65)

### 🤝 COREY CITRON  ↔  Patrick Jahnke
**Overall score: 0.64**  |  Match type: `complementary`  |  Embedding similarity: 0.67  |  Complementary: 0.66

- **COREY CITRON** — [DELEGATE]
  - Sectors: decentralized_finance, investment_and_capital_markets, infrastructure_and_scaling
  - Intents: knowledge_exchange, deal_making
  - LinkedIn: Founder & CMO at Yoli - The Better Body Company
- **Patrick Jahnke** — [DELEGATE]
  - Sectors: investment_and_capital_markets, infrastructure_and_scaling, ecosystem_and_foundations
  - Intents: knowledge_exchange, deal_making
  - LinkedIn: Portfolio Manager, Global Impact & Sustainable Equity Funds / ESG

**Why they should meet (GPT-4o):**
> Patrick Jahnke offers capital and strategic partnerships for Web3 projects, which aligns with Corey's focus on decentralized finance and infrastructure. Their collaboration could lead to strategic investments and partnerships that enhance technological capabilities.

**Shared context:** sectors: investment_and_capital_markets, infrastructure_and_scaling | synergies: strategic investments in Web3 projects, enhancing technological capabilities | action_items: Discuss potential investments in Web3 startups, Explore partnerships for infrastructure scaling, Evaluate opportunities for strategic collaborations

_Explanation confidence: 0.68_

---

### 🤝 Jill Kenney  ↔  Mees Vlasveld
**Overall score: 0.63**  |  Match type: `complementary`  |  Embedding similarity: 0.50  |  Complementary: 0.65

- **Jill Kenney** — Sundaebar — [DELEGATE]
  - Sectors: ai_depin_frontier_tech, decentralized_ai
  - Intents: seeking_partnerships, technology_evaluation, knowledge_exchange
  - LinkedIn: CEO, sundae_barI | Co-Founder, Paidia Gaming Former:  Head of Red Bull Media Network Canada
  - Grid: sundae_bar helps businesses find, deploy, and manage AI agents for enterprise workflows through a live marketplace.
- **Mees Vlasveld** — Investment Manager at Vanlanschotkempen — [DELEGATE]
  - Sectors: investment_and_capital_markets, tokenisation_of_finance, decentralized_finance
  - Intents: deploying_capital, deal_making, knowledge_exchange
  - LinkedIn: Investment Professional | Education Coordinator at CFA Society Netherlands | Author of “Bitcoin Treasury Companies”

**Why they should meet (GPT-4o):**
> Mees Vlasveld from Van Lanschot Kempen and Jill Kenney from Sundaebar can explore investment opportunities where Van Lanschot Kempen's focus on sustainable finance aligns with Sundaebar's AI marketplace. This partnership could provide capital for Sundaebar's expansion and offer Van Lanschot Kempen access to cutting-edge AI technologies.

**Shared context:** sectors: investment_and_capital_markets, decentralized_ai | synergies: Sustainable finance investment, AI technology integration | action_items: Discuss investment in AI marketplace expansion, Explore sustainable finance initiatives, Evaluate potential for joint AI technology development

_Explanation confidence: 0.67_

---

### ✨ COREY CITRON  ↔  Jill Kenney
**Overall score: 0.62**  |  Match type: `non_obvious`  |  Embedding similarity: 0.55  |  Complementary: 0.64

- **COREY CITRON** — [DELEGATE]
  - Sectors: decentralized_finance, investment_and_capital_markets, infrastructure_and_scaling
  - Intents: knowledge_exchange, deal_making
  - LinkedIn: Founder & CMO at Yoli - The Better Body Company
- **Jill Kenney** — Sundaebar — [DELEGATE]
  - Sectors: ai_depin_frontier_tech, decentralized_ai
  - Intents: seeking_partnerships, technology_evaluation, knowledge_exchange
  - LinkedIn: CEO, sundae_barI | Co-Founder, Paidia Gaming Former:  Head of Red Bull Media Network Canada
  - Grid: sundae_bar helps businesses find, deploy, and manage AI agents for enterprise workflows through a live marketplace.

**Why they should meet (GPT-4o):**
> Jill Kenney from Sundaebar offers a marketplace for advanced AI agents, which could provide innovative solutions for Corey's interest in decentralized finance. Their collaboration could lead to the integration of AI technologies into blockchain applications, enhancing operational efficiency.

**Shared context:** sectors: ai_depin_frontier_tech, decentralized_ai | synergies: AI integration into blockchain applications, enhancing operational efficiency | action_items: Explore AI solutions for decentralized finance, Discuss potential partnerships for AI integration, Evaluate opportunities for enhancing operational efficiency with AI agents

_Explanation confidence: 0.66_

---

### ✨ Adrian Bejenaru-Rohian  ↔  Sumakshi Chauhan
**Overall score: 0.62**  |  Match type: `non_obvious`  |  Embedding similarity: 0.66  |  Complementary: 0.65

- **Adrian Bejenaru-Rohian** — Project Manager — [DELEGATE]
  - Sectors: culture_media_gaming
  - Intents: knowledge_exchange, technology_evaluation
  - LinkedIn: Project Manager at Art Dynasty
- **Sumakshi Chauhan** — [DELEGATE]
  - Sectors: investment_and_capital_markets, ecosystem_and_foundations, infrastructure_and_scaling
  - Intents: knowledge_exchange, seeking_partnerships
  - LinkedIn: Senior Talent Acquisition Partner | CIPD Qualified

**Why they should meet (GPT-4o):**
> Sumakshi Chauhan is in the exploratory phase of seeking strategic partnerships, which could be complemented by Adrian's media expertise to highlight potential collaborations. Adrian can gain insights into Sumakshi's exploration of Web3 opportunities, enriching his media narratives.

**Shared context:** sectors: investment_and_capital_markets, culture_media_gaming | synergies: media coverage of strategic partnerships, insights into Web3 exploration | action_items: Explore media opportunities for partnership announcements, Discuss potential for exclusive interviews, Plan coverage of Sumakshi's exploratory findings

_Explanation confidence: 0.66_

---

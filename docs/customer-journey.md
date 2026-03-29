# POT Matchmaker — Complete Customer Journey

```mermaid
flowchart TD
    %% ── Ticket Purchase ──────────────────────────────────────
    A[Attendee Buys Ticket on Rhuna/Extasy] --> B[Extasy API Sync]
    B --> C[Attendee Created in DB]
    C --> D[Magic Access Token Generated]

    %% ── Data Enrichment ──────────────────────────────────────
    C --> E[Data Enrichment Pipeline]
    E --> E1[LinkedIn via Proxycurl]
    E --> E2[Twitter/X API]
    E --> E3[Company Website Scrape]
    E1 & E2 & E3 --> F[AI Profile Synthesis]
    F --> F1[GPT-4o: AI Summary]
    F --> F2[GPT-4o: Intent Tags]
    F --> F3[GPT-4o: Vertical Tags]
    F1 & F2 & F3 --> G[Generate Embedding]
    G --> G1[text-embedding-3-small → 1536-dim vector stored in pgvector]

    %% ── Match Intro Email ────────────────────────────────────
    G1 --> H[3-Stage Matching Pipeline]
    H --> H1[Stage 1: pgvector Cosine Retrieval — Top 50 Candidates]
    H1 --> H2[Stage 2: Hard Filters — Seeking, Geography, Deal Stage]
    H2 --> H3[Stage 3: GPT-4o Rank & Explain — Top 10 Scored + Explained]
    H3 --> I[Matches Stored in DB]
    I --> J{Email Delivery}
    J -->|SES/Email Provider| K[Match Intro Email]
    K --> K1[Branded Email with Top Match Preview]
    K --> K2[QR Code — CID Attachment]
    K --> K3[Magic Link CTA Button]

    %% ── Attendee Entry Points ────────────────────────────────
    K1 & K3 --> L{Attendee Clicks Magic Link}
    K2 --> L
    L --> M[/m/:token — Magic Match Dashboard]
    M --> M1[See All AI Matches — No Login Required]
    M --> M2{Profile Incomplete?}
    M2 -->|Yes| M3[Enrichment Card: Twitter + Who Do You Want to Meet]
    M3 --> M4[PATCH /m/:token/profile — Save Without Login]
    M4 --> M5[target_companies Fed Into Next Match Refresh]

    %% ── Attendee Logs In ─────────────────────────────────────
    M1 --> N{Wants Full Access?}
    N -->|Yes| O[Log In / Register]
    O --> P[My Matches Dashboard]

    %% ── Match Interaction ────────────────────────────────────
    P --> Q{For Each Match Card}
    Q --> Q1[View: Name, Title, Company, Score, Explanation]
    Q --> Q2[Social Links: LinkedIn, Twitter, Website]
    Q --> Q3[ThumbsUp: More Like This]
    Q --> Q4[ThumbsDown: Not Relevant]
    Q --> Q5[Accept: I'd Like to Meet]
    Q --> Q6[Decline: Maybe Later + Reason]

    %% ── Mutual Match Flow ────────────────────────────────────
    Q5 --> R{Both Parties Accepted?}
    R -->|No| R1[Pending — Badge Shows on Nav]
    R -->|Yes| S[Mutual Match Confirmed]
    S --> S1[Mutual Match Email Sent]
    S --> S2[Chat Unlocked — In-App Messaging]
    S --> S3[Meeting Scheduler — June 2-3 Slots]
    S3 --> S4[ICS Calendar Download]
    S3 --> S5[Meeting Confirmation Email]

    %% ── Post-Meeting ─────────────────────────────────────────
    S4 & S5 --> T[Meeting at Proof of Talk]
    T --> U[Satisfaction Rating]
    U --> V[Feedback Loop → GPT-4o Prompt]

    %% ── Pre-Event Community ──────────────────────────────────
    P --> W[Pre-Event Warm-Up Threads]
    W --> W1[11 Sector-Based Discussion Threads]
    W1 --> W2[Post Messages — Build Connections Before Event]

    %% ── Profile & QR ─────────────────────────────────────────
    P --> X[Profile Page]
    X --> X1[Edit: Goals, Interests, Twitter, Photo]
    X --> X2[Who Do You Want to Meet — Free Text]
    X --> X3[QR Business Card — Scan to Share]
    X3 --> X4[Other Attendee Scans → Sees Your Magic Link Dashboard]

    %% ── Organiser Dashboard ──────────────────────────────────
    I --> Y[Organiser Dashboard]
    Y --> Y1[KPIs: Attendees, Matches, Acceptance Rate]
    Y --> Y2[Match Quality Distribution]
    Y --> Y3[Investor Heatmap — Capital Activity by Sector]
    Y --> Y4[Sector Breakdown]
    Y --> Y5[Admin: Trigger Processing / Matching / Extasy Sync]

    %% ── Daily Refresh ────────────────────────────────────────
    V --> Z[Daily Match Refresh — 02:00 UTC Cron]
    M5 --> Z
    Q6 --> Z
    Z --> H

    %% ── Styling ──────────────────────────────────────────────
    classDef orange fill:#E76315,stroke:#D35400,color:#fff
    classDef dark fill:#1a1a2e,stroke:#E76315,color:#e8e8f0
    classDef green fill:#10b981,stroke:#059669,color:#fff

    class A,O orange
    class S,S1,S2,S3 green
    class M,M1,P,W,X,Y dark
```

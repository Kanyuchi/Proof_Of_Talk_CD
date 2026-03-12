-- ============================================================
-- POT Matchmaker — Supabase Schema Setup
-- Run this in the Supabase SQL editor (once, in order)
-- ============================================================

-- 1. Enable pgvector (Supabase has this available as an extension)
CREATE EXTENSION IF NOT EXISTS vector;

-- 2. Ticket type enum
DO $$ BEGIN
    CREATE TYPE tickettype AS ENUM ('delegate', 'sponsor', 'speaker', 'vip');
EXCEPTION
    WHEN duplicate_object THEN NULL;
END $$;

-- 3. Attendees table
CREATE TABLE IF NOT EXISTS attendees (
    id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at            TIMESTAMPTZ NOT NULL DEFAULT now(),

    -- Registration / identity
    name                  VARCHAR(255) NOT NULL,
    email                 VARCHAR(255) NOT NULL UNIQUE,
    company               VARCHAR(255) NOT NULL DEFAULT '',
    title                 VARCHAR(255) NOT NULL DEFAULT '',
    ticket_type           tickettype NOT NULL DEFAULT 'delegate',

    -- Intent fields
    interests             TEXT[] NOT NULL DEFAULT '{}',
    goals                 TEXT,
    seeking               TEXT[] NOT NULL DEFAULT '{}',
    not_looking_for       TEXT[] NOT NULL DEFAULT '{}',
    preferred_geographies TEXT[] NOT NULL DEFAULT '{}',
    deal_stage            VARCHAR(100),

    -- Enrichment
    linkedin_url          VARCHAR(500),
    twitter_handle        VARCHAR(255),
    company_website       VARCHAR(500),
    enriched_profile      JSONB NOT NULL DEFAULT '{}',

    -- AI-generated
    ai_summary            TEXT,
    embedding             vector(1536),
    intent_tags           TEXT[] NOT NULL DEFAULT '{}',
    deal_readiness_score  FLOAT,

    -- Data intelligence
    crunchbase_data       JSONB NOT NULL DEFAULT '{}',
    pot_history           JSONB NOT NULL DEFAULT '{}',
    enriched_at           TIMESTAMPTZ,

    -- Extasy source fields (ingestion tracking)
    extasy_order_id       VARCHAR(255),
    extasy_ticket_code    VARCHAR(50),
    extasy_ticket_name    VARCHAR(255),
    phone_number          VARCHAR(50),
    city                  VARCHAR(255),
    country_iso3          VARCHAR(10),
    ticket_bought_at      TIMESTAMPTZ
);

-- 4. Matches table
CREATE TABLE IF NOT EXISTS matches (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at              TIMESTAMPTZ NOT NULL DEFAULT now(),

    attendee_a_id           UUID NOT NULL REFERENCES attendees(id) ON DELETE CASCADE,
    attendee_b_id           UUID NOT NULL REFERENCES attendees(id) ON DELETE CASCADE,

    -- Scores
    similarity_score        FLOAT NOT NULL,
    complementary_score     FLOAT NOT NULL,
    overall_score           FLOAT NOT NULL,
    match_type              VARCHAR(50) NOT NULL,   -- complementary | non_obvious | deal_ready

    -- AI explanation
    explanation             TEXT NOT NULL,
    shared_context          JSONB NOT NULL DEFAULT '{}',

    -- Two-sided status
    status                  VARCHAR(50) NOT NULL DEFAULT 'pending',
    status_a                VARCHAR(50) NOT NULL DEFAULT 'pending',
    status_b                VARCHAR(50) NOT NULL DEFAULT 'pending',

    -- Scheduling
    meeting_time            TIMESTAMPTZ,
    meeting_location        VARCHAR(255),
    met_at                  TIMESTAMPTZ,
    meeting_outcome         VARCHAR(100),
    satisfaction_score      FLOAT,

    -- Feedback
    decline_reason          TEXT,
    hidden_by_user          BOOLEAN NOT NULL DEFAULT FALSE,
    explanation_confidence  FLOAT
);

-- 5. Users table (auth layer)
CREATE TABLE IF NOT EXISTS users (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    email           VARCHAR(255) NOT NULL UNIQUE,
    hashed_password VARCHAR(255) NOT NULL,
    full_name       VARCHAR(255) NOT NULL,
    is_admin        BOOLEAN NOT NULL DEFAULT FALSE,
    attendee_id     UUID REFERENCES attendees(id) ON DELETE SET NULL
);

-- 6. Indexes
CREATE INDEX IF NOT EXISTS idx_attendees_email         ON attendees(email);
CREATE INDEX IF NOT EXISTS idx_attendees_ticket_type   ON attendees(ticket_type);
CREATE INDEX IF NOT EXISTS idx_attendees_extasy_order  ON attendees(extasy_order_id);
CREATE INDEX IF NOT EXISTS idx_matches_attendee_a      ON matches(attendee_a_id);
CREATE INDEX IF NOT EXISTS idx_matches_attendee_b      ON matches(attendee_b_id);
CREATE INDEX IF NOT EXISTS idx_matches_overall_score   ON matches(overall_score DESC);
CREATE INDEX IF NOT EXISTS idx_matches_status          ON matches(status);

-- pgvector cosine similarity index (speeds up embedding lookups)
CREATE INDEX IF NOT EXISTS idx_attendees_embedding
    ON attendees USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 50);

-- 7. Auto-update updated_at trigger
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS set_attendees_updated_at ON attendees;
CREATE TRIGGER set_attendees_updated_at
    BEFORE UPDATE ON attendees
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================================
-- Done. Tables: attendees, matches, users
-- Extensions: vector (pgvector)
-- ============================================================

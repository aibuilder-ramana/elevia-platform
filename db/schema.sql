-- Elevia Platform Schema

CREATE TABLE IF NOT EXISTS clinics (
    id            SERIAL PRIMARY KEY,
    name          TEXT        NOT NULL,
    address       TEXT,
    website       TEXT,
    phone         TEXT,
    email         TEXT,
    mcp_endpoint  TEXT,
    created_at    TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS providers (
    id                    SERIAL PRIMARY KEY,
    clinic_id             INTEGER     NOT NULL REFERENCES clinics(id) ON DELETE CASCADE,
    provider_id           TEXT        UNIQUE NOT NULL,
    name                  TEXT        NOT NULL,
    specializations       TEXT,
    description           TEXT,
    email                 TEXT,
    phone                 TEXT,
    mailing_address       TEXT,
    insurance             TEXT[],
    accepting_new_patients BOOLEAN    DEFAULT TRUE,
    rating                INTEGER     DEFAULT 0,
    reviews               NUMERIC(3,1) DEFAULT 0.0,
    calendar_type         TEXT        DEFAULT 'google',
    calendar_id           TEXT,
    service_account_email TEXT,
    created_at            TIMESTAMPTZ DEFAULT NOW()
);

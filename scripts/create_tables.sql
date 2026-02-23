-- ==========================================================================
-- CREATE TABLE DDLs
-- Domains: Company, Channel (WhatsApp), Messaging, Agent
-- Database: PostgreSQL
-- ==========================================================================

-- ── Enum Types ──────────────────────────────────────────────────────────

CREATE TYPE company_status AS ENUM ('active', 'suspended');
CREATE TYPE branch_status AS ENUM ('active', 'inactive');
CREATE TYPE service_status AS ENUM ('active', 'inactive');
CREATE TYPE staff_status AS ENUM ('active', 'inactive');
CREATE TYPE override_type AS ENUM ('blocked', 'modified');
CREATE TYPE booking_status AS ENUM ('confirmed', 'cancelled', 'completed', 'no_show');
CREATE TYPE booked_via AS ENUM ('agent', 'member');
CREATE TYPE member_status AS ENUM ('active', 'deactivated');
CREATE TYPE invite_status AS ENUM ('active', 'used', 'revoked');
CREATE TYPE whatsapp_account_status AS ENUM ('pending', 'active', 'disconnected');
CREATE TYPE agent_status AS ENUM ('active', 'paused');
CREATE TYPE knowledge_entry_status AS ENUM ('active', 'archived');
CREATE TYPE channel_type AS ENUM ('whatsapp');
CREATE TYPE conversation_status AS ENUM ('active', 'escalated', 'resolved', 'expired');
CREATE TYPE message_role AS ENUM ('customer', 'agent', 'member');
CREATE TYPE tool_execution_status AS ENUM ('success', 'failure');
CREATE TYPE reply_template_trigger AS ENUM (
    'greeting',
    'availability_found',
    'availability_none',
    'booking_confirmed',
    'booking_slot_unavailable',
    'escalation'
);


-- ── Company Domain ──────────────────────────────────────────────────────

CREATE TABLE companies (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name        VARCHAR(255) NOT NULL,
    slug        VARCHAR(255) NOT NULL UNIQUE,
    domain      VARCHAR(255),
    timezone    VARCHAR(63)  NOT NULL DEFAULT 'UTC',
    status      company_status NOT NULL DEFAULT 'active',
    created_at  TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ  NOT NULL DEFAULT now()
);

CREATE INDEX idx_companies_slug ON companies (slug);


CREATE TABLE branches (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id      UUID         NOT NULL REFERENCES companies (id) ON DELETE CASCADE,
    name            VARCHAR(255) NOT NULL,
    address         VARCHAR(500) NOT NULL,
    phone           VARCHAR(31),
    timezone        VARCHAR(63)  NOT NULL,
    operating_hours JSONB        NOT NULL,
    status          branch_status NOT NULL DEFAULT 'active',
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ  NOT NULL DEFAULT now()
);

CREATE INDEX idx_branches_company_id ON branches (company_id);


CREATE TABLE services (
    id                       UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id               UUID           NOT NULL REFERENCES companies (id) ON DELETE CASCADE,
    name                     VARCHAR(255)   NOT NULL,
    description              TEXT,
    default_price            NUMERIC(10, 2) NOT NULL,
    default_duration_minutes INTEGER        NOT NULL,
    currency                 VARCHAR(3)     NOT NULL DEFAULT 'SGD',
    status                   service_status NOT NULL DEFAULT 'active',
    created_at               TIMESTAMPTZ    NOT NULL DEFAULT now(),
    updated_at               TIMESTAMPTZ    NOT NULL DEFAULT now()
);

CREATE INDEX idx_services_company_id ON services (company_id);


CREATE TABLE staff (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID         NOT NULL REFERENCES companies (id) ON DELETE CASCADE,
    name       VARCHAR(255) NOT NULL,
    email      VARCHAR(255),
    phone      VARCHAR(31),
    avatar_url VARCHAR(500),
    status     staff_status NOT NULL DEFAULT 'active',
    created_at TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ  NOT NULL DEFAULT now()
);

CREATE INDEX idx_staff_company_id ON staff (company_id);


CREATE TABLE staff_services (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    staff_id          UUID           NOT NULL REFERENCES staff (id) ON DELETE CASCADE,
    service_id        UUID           NOT NULL REFERENCES services (id) ON DELETE CASCADE,
    price_override    NUMERIC(10, 2),
    duration_override INTEGER,
    created_at        TIMESTAMPTZ    NOT NULL DEFAULT now(),
    updated_at        TIMESTAMPTZ    NOT NULL DEFAULT now(),

    CONSTRAINT uq_staff_service UNIQUE (staff_id, service_id)
);

CREATE INDEX idx_staff_services_staff_id   ON staff_services (staff_id);
CREATE INDEX idx_staff_services_service_id ON staff_services (service_id);


CREATE TABLE staff_availabilities (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    staff_id    UUID    NOT NULL REFERENCES staff (id) ON DELETE CASCADE,
    branch_id   UUID    NOT NULL REFERENCES branches (id) ON DELETE CASCADE,
    day_of_week INTEGER NOT NULL,
    start_time  TIME    NOT NULL,
    end_time    TIME    NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT ck_availability_time_order CHECK (start_time < end_time),
    CONSTRAINT ck_availability_day_range  CHECK (day_of_week >= 0 AND day_of_week <= 6)
);

CREATE INDEX idx_staff_availabilities_staff_id  ON staff_availabilities (staff_id);
CREATE INDEX idx_staff_availabilities_branch_id ON staff_availabilities (branch_id);


CREATE TABLE availability_overrides (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    staff_id   UUID          NOT NULL REFERENCES staff (id) ON DELETE CASCADE,
    branch_id  UUID          NOT NULL REFERENCES branches (id) ON DELETE CASCADE,
    date       DATE          NOT NULL,
    type       override_type NOT NULL,
    start_time TIME,
    end_time   TIME,
    reason     VARCHAR(500),
    created_at TIMESTAMPTZ   NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ   NOT NULL DEFAULT now()
);

CREATE INDEX idx_availability_overrides_staff_id  ON availability_overrides (staff_id);
CREATE INDEX idx_availability_overrides_branch_id ON availability_overrides (branch_id);


CREATE TABLE bookings (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id       UUID           NOT NULL REFERENCES companies (id) ON DELETE CASCADE,
    branch_id        UUID           NOT NULL REFERENCES branches (id) ON DELETE CASCADE,
    staff_id         UUID           NOT NULL REFERENCES staff (id) ON DELETE RESTRICT,
    service_id       UUID           NOT NULL REFERENCES services (id) ON DELETE RESTRICT,
    customer_phone   VARCHAR(31)    NOT NULL,
    customer_name    VARCHAR(255),
    date             DATE           NOT NULL,
    start_time       TIME           NOT NULL,
    end_time         TIME           NOT NULL,
    duration_minutes INTEGER        NOT NULL,
    price            NUMERIC(10, 2) NOT NULL,
    currency         VARCHAR(3)     NOT NULL,
    status           booking_status NOT NULL DEFAULT 'confirmed',
    booked_via       booked_via     NOT NULL,
    conversation_id  UUID,
    notes            TEXT,
    cancelled_at     TIMESTAMPTZ,
    created_at       TIMESTAMPTZ    NOT NULL DEFAULT now(),
    updated_at       TIMESTAMPTZ    NOT NULL DEFAULT now(),

    CONSTRAINT ck_booking_time_order CHECK (start_time < end_time)
);

CREATE INDEX idx_bookings_company_id ON bookings (company_id);
CREATE INDEX idx_bookings_branch_id  ON bookings (branch_id);
CREATE INDEX idx_bookings_staff_id   ON bookings (staff_id);
CREATE INDEX idx_bookings_service_id ON bookings (service_id);
CREATE INDEX idx_bookings_date       ON bookings (date);
CREATE INDEX idx_bookings_staff_date ON bookings (staff_id, date) WHERE status = 'confirmed';


CREATE TABLE members (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID         REFERENCES companies (id) ON DELETE CASCADE,
    name       VARCHAR(255) NOT NULL,
    email      VARCHAR(255) NOT NULL UNIQUE,
    avatar_url VARCHAR(500),
    status     member_status NOT NULL DEFAULT 'active',
    created_at TIMESTAMPTZ   NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ   NOT NULL DEFAULT now()
);

CREATE INDEX idx_members_company_id ON members (company_id);


CREATE TABLE invites (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID          NOT NULL REFERENCES companies (id) ON DELETE CASCADE,
    code       VARCHAR(20)   NOT NULL UNIQUE,
    created_by UUID          NOT NULL REFERENCES members (id) ON DELETE CASCADE,
    used_by    UUID          REFERENCES members (id) ON DELETE SET NULL,
    status     invite_status NOT NULL DEFAULT 'active',
    expires_at TIMESTAMPTZ   NOT NULL,
    created_at TIMESTAMPTZ   NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ   NOT NULL DEFAULT now()
);

CREATE INDEX idx_invites_company_id ON invites (company_id);
CREATE INDEX idx_invites_code       ON invites (code);


-- ── Channel Domain: WhatsApp ─────────────────────────────────────────────

CREATE TABLE whatsapp_config (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    access_token TEXT        NOT NULL,
    verify_token VARCHAR(255) NOT NULL,
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);


CREATE TABLE whatsapp_accounts (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    branch_id       UUID         NOT NULL UNIQUE REFERENCES branches (id) ON DELETE CASCADE,
    company_id      UUID         NOT NULL REFERENCES companies (id) ON DELETE CASCADE,
    waba_id         VARCHAR(255) NOT NULL,
    phone_number_id VARCHAR(255) NOT NULL UNIQUE,
    display_phone   VARCHAR(31)  NOT NULL,
    status          whatsapp_account_status NOT NULL DEFAULT 'pending',
    verified_at     TIMESTAMPTZ,
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ  NOT NULL DEFAULT now()
);

CREATE INDEX idx_whatsapp_accounts_company_id      ON whatsapp_accounts (company_id);
CREATE INDEX idx_whatsapp_accounts_phone_number_id ON whatsapp_accounts (phone_number_id);


-- ── Messaging Domain ────────────────────────────────────────────────────

CREATE TABLE contacts (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID         NOT NULL REFERENCES companies (id) ON DELETE CASCADE,
    phone      VARCHAR(31)  NOT NULL,
    name       VARCHAR(255),
    created_at TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ  NOT NULL DEFAULT now(),

    CONSTRAINT uq_contacts_company_phone UNIQUE (company_id, phone)
);

CREATE INDEX idx_contacts_company_id ON contacts (company_id);



CREATE TABLE conversations (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    branch_id    UUID                NOT NULL REFERENCES branches (id) ON DELETE CASCADE,
    company_id   UUID                NOT NULL REFERENCES companies (id) ON DELETE CASCADE,
    contact_id   UUID                NOT NULL REFERENCES contacts (id) ON DELETE CASCADE,
    channel      channel_type        NOT NULL,
    status       conversation_status NOT NULL DEFAULT 'active',
    escalated_at TIMESTAMPTZ,
    resolved_at  TIMESTAMPTZ,
    created_at   TIMESTAMPTZ         NOT NULL DEFAULT now(),
    updated_at   TIMESTAMPTZ         NOT NULL DEFAULT now()
);

CREATE INDEX idx_conversations_company_id ON conversations (company_id);
CREATE INDEX idx_conversations_branch_id  ON conversations (branch_id);
CREATE INDEX idx_conversations_contact_id ON conversations (contact_id);
CREATE UNIQUE INDEX uq_conversations_open_per_customer
    ON conversations (branch_id, channel, contact_id)
    WHERE status IN ('active', 'escalated');


CREATE TABLE messages (
    id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id    UUID         NOT NULL REFERENCES conversations (id) ON DELETE CASCADE,
    role               message_role NOT NULL,
    content            TEXT         NOT NULL,
    channel_message_id VARCHAR(255),
    created_at         TIMESTAMPTZ  NOT NULL DEFAULT now()
);

CREATE INDEX idx_messages_conversation_id ON messages (conversation_id);
CREATE UNIQUE INDEX uq_messages_channel_message_id
    ON messages (channel_message_id)
    WHERE channel_message_id IS NOT NULL;


-- ── Agent Domain ────────────────────────────────────────────────────────

CREATE TABLE agents (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    branch_id     UUID         NOT NULL UNIQUE REFERENCES branches (id) ON DELETE CASCADE,
    company_id    UUID         NOT NULL REFERENCES companies (id) ON DELETE CASCADE,
    name          VARCHAR(255) NOT NULL,
    system_prompt TEXT         NOT NULL,
    model         VARCHAR(127) NOT NULL,
    tools_enabled JSONB        NOT NULL DEFAULT '{}',
    status        agent_status NOT NULL DEFAULT 'active',
    created_at    TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_at    TIMESTAMPTZ  NOT NULL DEFAULT now()
);

CREATE INDEX idx_agents_company_id ON agents (company_id);


CREATE TABLE reply_templates (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id   UUID                   NOT NULL REFERENCES agents (id) ON DELETE CASCADE,
    trigger    reply_template_trigger NOT NULL,
    name       VARCHAR(255)           NOT NULL,
    content    TEXT                   NOT NULL,
    status     knowledge_entry_status NOT NULL DEFAULT 'active',
    created_at TIMESTAMPTZ            NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ            NOT NULL DEFAULT now()
);

CREATE INDEX idx_reply_templates_agent_id ON reply_templates (agent_id);
CREATE UNIQUE INDEX uq_reply_templates_active_trigger
    ON reply_templates (agent_id, trigger)
    WHERE status = 'active';


CREATE TABLE knowledge_entries (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id   UUID    NOT NULL REFERENCES agents (id) ON DELETE CASCADE,
    question   TEXT    NOT NULL,
    answer     TEXT    NOT NULL,
    category   VARCHAR(255),
    sort_order INTEGER NOT NULL DEFAULT 0,
    status     knowledge_entry_status NOT NULL DEFAULT 'active',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_knowledge_entries_agent_id ON knowledge_entries (agent_id);


CREATE TABLE tool_executions (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID                  NOT NULL REFERENCES conversations (id) ON DELETE CASCADE,
    message_id      UUID                  REFERENCES messages (id) ON DELETE SET NULL,
    tool            VARCHAR(63)           NOT NULL,
    input           JSONB                 NOT NULL,
    output          JSONB                 NOT NULL,
    status          tool_execution_status NOT NULL,
    duration_ms     INTEGER,
    created_at      TIMESTAMPTZ           NOT NULL DEFAULT now()
);

CREATE INDEX idx_tool_executions_conversation_id ON tool_executions (conversation_id);
CREATE INDEX idx_tool_executions_message_id      ON tool_executions (message_id);


-- ── Cross-domain FK (bookings → conversations) ─────────────────────────

ALTER TABLE bookings
    ADD CONSTRAINT fk_bookings_conversation
    FOREIGN KEY (conversation_id) REFERENCES conversations (id) ON DELETE SET NULL;


-- ==========================================================================
-- DROP ALL TABLES — ordered to respect foreign key dependencies
-- (leaf tables first, root tables last)
-- ==========================================================================

DROP TABLE IF EXISTS "tool_executions" CASCADE;
DROP TABLE IF EXISTS "knowledge_entries" CASCADE;
DROP TABLE IF EXISTS "reply_templates" CASCADE;
DROP TABLE IF EXISTS "agents" CASCADE;
DROP TABLE IF EXISTS "messages" CASCADE;
DROP TABLE IF EXISTS "conversations" CASCADE;
DROP TABLE IF EXISTS "contacts" CASCADE;
DROP TABLE IF EXISTS "whatsapp_accounts" CASCADE;
DROP TABLE IF EXISTS "whatsapp_config" CASCADE;
DROP TABLE IF EXISTS "invites" CASCADE;
DROP TABLE IF EXISTS "bookings" CASCADE;
DROP TABLE IF EXISTS "availability_overrides" CASCADE;
DROP TABLE IF EXISTS "staff_availabilities" CASCADE;
DROP TABLE IF EXISTS "staff_services" CASCADE;
DROP TABLE IF EXISTS "members" CASCADE;
DROP TABLE IF EXISTS "staff" CASCADE;
DROP TABLE IF EXISTS "services" CASCADE;
DROP TABLE IF EXISTS "branches" CASCADE;
DROP TABLE IF EXISTS "companies" CASCADE;
DROP TYPE IF EXISTS "tool_execution_status" CASCADE;
DROP TYPE IF EXISTS "reply_template_trigger" CASCADE;
DROP TYPE IF EXISTS "message_role" CASCADE;
DROP TYPE IF EXISTS "conversation_status" CASCADE;
DROP TYPE IF EXISTS "channel_type" CASCADE;
DROP TYPE IF EXISTS "knowledge_entry_status" CASCADE;
DROP TYPE IF EXISTS "agent_status" CASCADE;
DROP TYPE IF EXISTS "whatsapp_account_status" CASCADE;
DROP TYPE IF EXISTS "invite_status" CASCADE;
DROP TYPE IF EXISTS "member_status" CASCADE;
DROP TYPE IF EXISTS "booked_via" CASCADE;
DROP TYPE IF EXISTS "booking_status" CASCADE;
DROP TYPE IF EXISTS "override_type" CASCADE;
DROP TYPE IF EXISTS "staff_status" CASCADE;
DROP TYPE IF EXISTS "service_status" CASCADE;
DROP TYPE IF EXISTS "branch_status" CASCADE;
DROP TYPE IF EXISTS "company_status" CASCADE;
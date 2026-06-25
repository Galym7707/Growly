-- Polar billing for SaaS subscriptions.
CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE TABLE IF NOT EXISTS subscriptions (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id text NOT NULL,
    workspace_id text,
    polar_customer_id text,
    polar_subscription_id text,
    polar_product_id text,
    plan text NOT NULL DEFAULT 'free',
    status text NOT NULL DEFAULT 'free',
    current_period_start timestamptz,
    current_period_end timestamptz,
    cancel_at_period_end boolean NOT NULL DEFAULT false,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

ALTER TABLE subscriptions ADD COLUMN IF NOT EXISTS id uuid DEFAULT gen_random_uuid();
ALTER TABLE subscriptions ADD COLUMN IF NOT EXISTS user_id text;
ALTER TABLE subscriptions ADD COLUMN IF NOT EXISTS workspace_id text;
ALTER TABLE subscriptions ADD COLUMN IF NOT EXISTS polar_customer_id text;
ALTER TABLE subscriptions ADD COLUMN IF NOT EXISTS polar_subscription_id text;
ALTER TABLE subscriptions ADD COLUMN IF NOT EXISTS polar_product_id text;
ALTER TABLE subscriptions ADD COLUMN IF NOT EXISTS plan text DEFAULT 'free';
ALTER TABLE subscriptions ADD COLUMN IF NOT EXISTS status text DEFAULT 'free';
ALTER TABLE subscriptions ADD COLUMN IF NOT EXISTS current_period_start timestamptz;
ALTER TABLE subscriptions ADD COLUMN IF NOT EXISTS current_period_end timestamptz;
ALTER TABLE subscriptions ADD COLUMN IF NOT EXISTS cancel_at_period_end boolean DEFAULT false;
ALTER TABLE subscriptions ADD COLUMN IF NOT EXISTS created_at timestamptz DEFAULT now();
ALTER TABLE subscriptions ADD COLUMN IF NOT EXISTS updated_at timestamptz DEFAULT now();

UPDATE subscriptions SET plan = 'free' WHERE plan IS NULL;
UPDATE subscriptions SET status = 'free' WHERE status IS NULL;
UPDATE subscriptions SET cancel_at_period_end = false WHERE cancel_at_period_end IS NULL;
UPDATE subscriptions SET created_at = now() WHERE created_at IS NULL;
UPDATE subscriptions SET updated_at = now() WHERE updated_at IS NULL;

ALTER TABLE subscriptions ALTER COLUMN user_id SET NOT NULL;
ALTER TABLE subscriptions ALTER COLUMN plan SET DEFAULT 'free';
ALTER TABLE subscriptions ALTER COLUMN plan SET NOT NULL;
ALTER TABLE subscriptions ALTER COLUMN status SET DEFAULT 'free';
ALTER TABLE subscriptions ALTER COLUMN status SET NOT NULL;
ALTER TABLE subscriptions ALTER COLUMN cancel_at_period_end SET DEFAULT false;
ALTER TABLE subscriptions ALTER COLUMN cancel_at_period_end SET NOT NULL;
ALTER TABLE subscriptions ALTER COLUMN created_at SET DEFAULT now();
ALTER TABLE subscriptions ALTER COLUMN created_at SET NOT NULL;
ALTER TABLE subscriptions ALTER COLUMN updated_at SET DEFAULT now();
ALTER TABLE subscriptions ALTER COLUMN updated_at SET NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS uq_subscriptions_polar_subscription
    ON subscriptions(polar_subscription_id)
    WHERE polar_subscription_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_subscriptions_user
    ON subscriptions(user_id);
CREATE INDEX IF NOT EXISTS idx_subscriptions_user_workspace
    ON subscriptions(user_id, COALESCE(workspace_id, ''));

CREATE TABLE IF NOT EXISTS payments (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id text NOT NULL,
    polar_order_id text,
    polar_customer_id text,
    polar_product_id text,
    amount integer,
    currency text,
    status text NOT NULL DEFAULT 'created',
    raw_event jsonb,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

ALTER TABLE payments ADD COLUMN IF NOT EXISTS id uuid DEFAULT gen_random_uuid();
ALTER TABLE payments ADD COLUMN IF NOT EXISTS user_id text;
ALTER TABLE payments ADD COLUMN IF NOT EXISTS polar_order_id text;
ALTER TABLE payments ADD COLUMN IF NOT EXISTS polar_customer_id text;
ALTER TABLE payments ADD COLUMN IF NOT EXISTS polar_product_id text;
ALTER TABLE payments ADD COLUMN IF NOT EXISTS amount integer;
ALTER TABLE payments ADD COLUMN IF NOT EXISTS currency text;
ALTER TABLE payments ADD COLUMN IF NOT EXISTS status text DEFAULT 'created';
ALTER TABLE payments ADD COLUMN IF NOT EXISTS raw_event jsonb;
ALTER TABLE payments ADD COLUMN IF NOT EXISTS created_at timestamptz DEFAULT now();
ALTER TABLE payments ADD COLUMN IF NOT EXISTS updated_at timestamptz DEFAULT now();

UPDATE payments SET status = 'created' WHERE status IS NULL;
UPDATE payments SET created_at = now() WHERE created_at IS NULL;
UPDATE payments SET updated_at = now() WHERE updated_at IS NULL;

ALTER TABLE payments ALTER COLUMN user_id SET NOT NULL;
ALTER TABLE payments ALTER COLUMN status SET DEFAULT 'created';
ALTER TABLE payments ALTER COLUMN status SET NOT NULL;
ALTER TABLE payments ALTER COLUMN created_at SET DEFAULT now();
ALTER TABLE payments ALTER COLUMN created_at SET NOT NULL;
ALTER TABLE payments ALTER COLUMN updated_at SET DEFAULT now();
ALTER TABLE payments ALTER COLUMN updated_at SET NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS uq_payments_polar_order
    ON payments(polar_order_id)
    WHERE polar_order_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_payments_user
    ON payments(user_id);

CREATE TABLE IF NOT EXISTS billing_events (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    provider text NOT NULL DEFAULT 'polar',
    event_id text,
    event_type text NOT NULL,
    user_id text,
    workspace_id text,
    processed boolean NOT NULL DEFAULT false,
    payload jsonb NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now()
);

ALTER TABLE billing_events ADD COLUMN IF NOT EXISTS id uuid DEFAULT gen_random_uuid();
ALTER TABLE billing_events ADD COLUMN IF NOT EXISTS provider text DEFAULT 'polar';
ALTER TABLE billing_events ADD COLUMN IF NOT EXISTS event_id text;
ALTER TABLE billing_events ADD COLUMN IF NOT EXISTS event_type text;
ALTER TABLE billing_events ADD COLUMN IF NOT EXISTS user_id text;
ALTER TABLE billing_events ADD COLUMN IF NOT EXISTS workspace_id text;
ALTER TABLE billing_events ADD COLUMN IF NOT EXISTS processed boolean DEFAULT false;
ALTER TABLE billing_events ADD COLUMN IF NOT EXISTS payload jsonb;
ALTER TABLE billing_events ADD COLUMN IF NOT EXISTS created_at timestamptz DEFAULT now();

UPDATE billing_events SET provider = 'polar' WHERE provider IS NULL;
UPDATE billing_events SET event_type = 'unknown' WHERE event_type IS NULL;
UPDATE billing_events SET processed = false WHERE processed IS NULL;
UPDATE billing_events SET payload = '{}'::jsonb WHERE payload IS NULL;
UPDATE billing_events SET created_at = now() WHERE created_at IS NULL;

ALTER TABLE billing_events ALTER COLUMN provider SET DEFAULT 'polar';
ALTER TABLE billing_events ALTER COLUMN provider SET NOT NULL;
ALTER TABLE billing_events ALTER COLUMN event_type SET NOT NULL;
ALTER TABLE billing_events ALTER COLUMN processed SET DEFAULT false;
ALTER TABLE billing_events ALTER COLUMN processed SET NOT NULL;
ALTER TABLE billing_events ALTER COLUMN payload SET NOT NULL;
ALTER TABLE billing_events ALTER COLUMN created_at SET DEFAULT now();
ALTER TABLE billing_events ALTER COLUMN created_at SET NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS uq_billing_events_provider_event
    ON billing_events(provider, event_id)
    WHERE event_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_billing_events_created_at
    ON billing_events(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_billing_events_user
    ON billing_events(user_id);

CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS trigger AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DO $$
DECLARE
    table_name text;
BEGIN
    FOREACH table_name IN ARRAY ARRAY['subscriptions', 'payments']
    LOOP
        EXECUTE format('DROP TRIGGER IF EXISTS trg_%I_updated_at ON %I', table_name, table_name);
        EXECUTE format(
            'CREATE TRIGGER trg_%I_updated_at BEFORE UPDATE ON %I '
            'FOR EACH ROW EXECUTE FUNCTION set_updated_at()',
            table_name,
            table_name
        );
    END LOOP;
END;
$$;

DO $$
BEGIN
    IF to_regnamespace('auth') IS NOT NULL THEN
        ALTER TABLE subscriptions ENABLE ROW LEVEL SECURITY;
        ALTER TABLE payments ENABLE ROW LEVEL SECURITY;
        ALTER TABLE billing_events ENABLE ROW LEVEL SECURITY;

        DROP POLICY IF EXISTS subscriptions_read_own ON subscriptions;
        CREATE POLICY subscriptions_read_own ON subscriptions
            FOR SELECT USING (auth.uid()::text = user_id);

        DROP POLICY IF EXISTS payments_read_own ON payments;
        CREATE POLICY payments_read_own ON payments
            FOR SELECT USING (auth.uid()::text = user_id);
    END IF;
END;
$$;

-- ============================================
-- Telegram Bot SaaS - Database Schema
-- PostgreSQL 15+
-- ============================================

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================
-- ENUM TYPES
-- ============================================

CREATE TYPE subscription_plan AS ENUM ('free', 'pro', 'business');
CREATE TYPE subscription_status AS ENUM ('active', 'expired', 'cancelled', 'pending');
CREATE TYPE payment_status AS ENUM ('pending', 'completed', 'failed', 'refunded');
CREATE TYPE payment_provider AS ENUM ('yookassa', 'cloudpayments', 'stripe');
CREATE TYPE bot_status AS ENUM ('creating', 'running', 'stopped', 'error', 'restarting');
CREATE TYPE appointment_status AS ENUM ('pending', 'confirmed', 'completed', 'cancelled');
CREATE TYPE notification_status AS ENUM ('pending', 'sent', 'failed');
CREATE TYPE notification_type AS ENUM ('reminder_24h', 'reminder_2h', 'new_booking', 'cancelled_booking', 'custom');
CREATE TYPE event_type AS ENUM ('booking_created', 'booking_completed', 'booking_cancelled', 'bot_started', 'bot_stopped');

-- ============================================
-- TABLES
-- ============================================

-- Masters (platform users)
CREATE TABLE masters (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    telegram_id BIGINT UNIQUE NOT NULL,
    username VARCHAR(255),
    phone VARCHAR(20),
    full_name VARCHAR(255),
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Subscriptions (tariff plans)
CREATE TABLE subscriptions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    master_id UUID NOT NULL REFERENCES masters(id) ON DELETE CASCADE,
    plan subscription_plan NOT NULL DEFAULT 'free',
    status subscription_status NOT NULL DEFAULT 'active',
    bots_limit INTEGER NOT NULL DEFAULT 1,
    appointments_limit INTEGER, -- NULL for unlimited
    starts_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ,
    auto_renew BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Payments
CREATE TABLE payments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    master_id UUID NOT NULL REFERENCES masters(id) ON DELETE CASCADE,
    subscription_id UUID REFERENCES subscriptions(id) ON DELETE SET NULL,
    amount DECIMAL(10, 2) NOT NULL,
    currency VARCHAR(3) DEFAULT 'RUB',
    status payment_status NOT NULL DEFAULT 'pending',
    provider payment_provider NOT NULL,
    provider_payment_id VARCHAR(255),
    provider_transaction_id TEXT,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);

-- Bots (master's bots)
CREATE TABLE bots (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    master_id UUID NOT NULL REFERENCES masters(id) ON DELETE CASCADE,
    bot_token VARCHAR(500) NOT NULL UNIQUE, -- Encrypted token
    bot_username VARCHAR(255) NOT NULL UNIQUE,
    bot_name VARCHAR(255),
    business_name VARCHAR(255),
    business_description TEXT,
    business_address TEXT,
    business_phone VARCHAR(20),
    container_status bot_status NOT NULL DEFAULT 'creating',
    container_id VARCHAR(255),
    webhook_url VARCHAR(500),
    webhook_secret VARCHAR(255),
    is_active BOOLEAN DEFAULT true,
    timezone VARCHAR(50) DEFAULT 'Europe/Moscow',
    language VARCHAR(10) DEFAULT 'ru',
    settings JSONB DEFAULT '{}', -- Custom settings
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Services (provided by master)
CREATE TABLE services (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    bot_id UUID NOT NULL REFERENCES bots(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    price DECIMAL(10, 2) NOT NULL DEFAULT 0,
    duration_minutes INTEGER NOT NULL,
    prepayment_percent INTEGER DEFAULT 0, -- 0-100%
    photo_url VARCHAR(500),
    is_active BOOLEAN DEFAULT true,
    sort_order INTEGER DEFAULT 0,
    settings JSONB DEFAULT '{}', -- Flexible settings
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Schedules (working hours)
CREATE TABLE schedules (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    bot_id UUID NOT NULL REFERENCES bots(id) ON DELETE CASCADE,
    day_of_week INTEGER NOT NULL CHECK (day_of_week BETWEEN 0 AND 6), -- 0 = Monday
    start_time TIME NOT NULL DEFAULT '09:00:00',
    end_time TIME NOT NULL DEFAULT '18:00:00',
    is_working_day BOOLEAN DEFAULT true,
    break_start_time TIME,
    break_end_time TIME,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(bot_id, day_of_week)
);

-- Schedule exceptions (holidays, special days)
CREATE TABLE schedule_exceptions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    bot_id UUID NOT NULL REFERENCES bots(id) ON DELETE CASCADE,
    date DATE NOT NULL,
    is_working_day BOOLEAN NOT NULL DEFAULT false,
    start_time TIME,
    end_time TIME,
    reason VARCHAR(255),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(bot_id, date)
);

-- Clients (customers)
CREATE TABLE clients (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    bot_id UUID NOT NULL REFERENCES bots(id) ON DELETE CASCADE,
    telegram_id BIGINT NOT NULL,
    username VARCHAR(255),
    first_name VARCHAR(255),
    last_name VARCHAR(255),
    phone VARCHAR(20),
    email VARCHAR(255),
    notes TEXT,
    total_visits INTEGER DEFAULT 0,
    total_spent DECIMAL(10, 2) DEFAULT 0,
    is_blocked BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(bot_id, telegram_id)
);

-- Appointments (bookings)
CREATE TABLE appointments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    bot_id UUID NOT NULL REFERENCES bots(id) ON DELETE CASCADE,
    client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    service_id UUID NOT NULL REFERENCES services(id) ON DELETE CASCADE,
    start_time TIMESTAMPTZ NOT NULL,
    end_time TIMESTAMPTZ NOT NULL,
    status appointment_status NOT NULL DEFAULT 'pending',
    price DECIMAL(10, 2),
    prepayment_amount DECIMAL(10, 2) DEFAULT 0,
    is_prepaid BOOLEAN DEFAULT false,
    client_comment TEXT,
    master_comment TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    confirmed_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    cancelled_at TIMESTAMPTZ,
    cancellation_reason TEXT
);

-- Notifications queue
CREATE TABLE notifications_queue (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    bot_id UUID NOT NULL REFERENCES bots(id) ON DELETE CASCADE,
    client_id UUID REFERENCES clients(id) ON DELETE CASCADE,
    master_id UUID REFERENCES masters(id) ON DELETE CASCADE,
    type notification_type NOT NULL,
    message TEXT NOT NULL,
    send_at TIMESTAMPTZ NOT NULL,
    status notification_status NOT NULL DEFAULT 'pending',
    attempts INTEGER DEFAULT 0,
    max_attempts INTEGER DEFAULT 3,
    error_message TEXT,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    sent_at TIMESTAMPTZ
);

-- Analytics events (partitioned by month)
CREATE TABLE analytics_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    bot_id UUID NOT NULL REFERENCES bots(id) ON DELETE CASCADE,
    event_type event_type NOT NULL,
    event_data JSONB DEFAULT '{}',
    user_id BIGINT, -- Telegram ID
    session_id VARCHAR(255),
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
) PARTITION BY RANGE (created_at);

-- Create partitions for analytics_events (current + next month)
CREATE TABLE analytics_events_2025_01 PARTITION OF analytics_events
    FOR VALUES FROM ('2025-01-01') TO ('2025-02-01');

CREATE TABLE analytics_events_2025_02 PARTITION OF analytics_events
    FOR VALUES FROM ('2025-02-01') TO ('2025-03-01');

CREATE TABLE analytics_events_2025_03 PARTITION OF analytics_events
    FOR VALUES FROM ('2025-03-01') TO ('2025-04-01');

-- System logs
CREATE TABLE system_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    bot_id UUID REFERENCES bots(id) ON DELETE CASCADE,
    level VARCHAR(20) NOT NULL CHECK (level IN ('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL')),
    message TEXT NOT NULL,
    module VARCHAR(255),
    function_name VARCHAR(255),
    line_num INTEGER,
    extra_data JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- User sessions (for auth)
CREATE TABLE user_sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    master_id UUID NOT NULL REFERENCES masters(id) ON DELETE CASCADE,
    session_token VARCHAR(255) UNIQUE NOT NULL,
    ip_address INET,
    user_agent TEXT,
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    last_used_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- INDEXES
-- ============================================

-- Masters indexes
CREATE INDEX idx_masters_telegram_id ON masters(telegram_id);
CREATE INDEX idx_masters_username ON masters(username);
CREATE INDEX idx_masters_is_active ON masters(is_active);

-- Subscriptions indexes
CREATE INDEX idx_subscriptions_master_id ON subscriptions(master_id);
CREATE INDEX idx_subscriptions_status ON subscriptions(status);
CREATE INDEX idx_subscriptions_expires_at ON subscriptions(expires_at) WHERE status = 'active';

-- Payments indexes
CREATE INDEX idx_payments_master_id ON payments(master_id);
CREATE INDEX idx_payments_status ON payments(status);
CREATE INDEX idx_payments_provider_transaction_id ON payments(provider_transaction_id);
CREATE INDEX idx_payments_created_at ON payments(created_at);

-- Bots indexes
CREATE INDEX idx_bots_master_id ON bots(master_id);
CREATE INDEX idx_bots_bot_username ON bots(bot_username);
CREATE INDEX idx_bots_container_status ON bots(container_status);
CREATE INDEX idx_bots_is_active ON bots(is_active);

-- Services indexes
CREATE INDEX idx_services_bot_id ON services(bot_id);
CREATE INDEX idx_services_is_active ON services(is_active) WHERE bot_id IS NOT NULL;
CREATE INDEX idx_services_sort_order ON services(bot_id, sort_order);

-- Schedules indexes
CREATE INDEX idx_schedules_bot_id ON schedules(bot_id);

-- Schedule exceptions indexes
CREATE INDEX idx_schedule_exceptions_bot_id ON schedule_exceptions(bot_id);
CREATE INDEX idx_schedule_exceptions_date ON schedule_exceptions(date);

-- Clients indexes
CREATE INDEX idx_clients_bot_id ON clients(bot_id);
CREATE INDEX idx_clients_telegram_id ON clients(telegram_id);
CREATE INDEX idx_clients_phone ON clients(phone);
CREATE INDEX idx_clients_is_blocked ON clients(is_active) WHERE is_blocked = true;

-- Appointments indexes (CRITICAL for calendar)
CREATE INDEX idx_appointments_bot_id ON appointments(bot_id);
CREATE INDEX idx_appointments_client_id ON appointments(client_id);
CREATE INDEX idx_appointments_service_id ON appointments(service_id);
CREATE INDEX idx_appointments_bot_time ON appointments(bot_id, start_time);
CREATE INDEX idx_appointments_status ON appointments(status);
CREATE INDEX idx_appointments_start_time ON appointments(start_time);
CREATE INDEX idx_appointments_end_time ON appointments(end_time);

-- Composite index for availability checks
CREATE INDEX idx_appointments_availability ON appointments(bot_id, start_time, end_time, status)
    WHERE status IN ('pending', 'confirmed');

-- Notifications queue indexes
CREATE INDEX idx_notifications_bot_id ON notifications_queue(bot_id);
CREATE INDEX idx_notifications_send_at ON notifications_queue(send_at)
    WHERE status = 'pending';
CREATE INDEX idx_notifications_status ON notifications_queue(status);

-- Analytics events indexes
CREATE INDEX idx_analytics_bot_id ON analytics_events(bot_id);
CREATE INDEX idx_analytics_event_type ON analytics_events(event_type);
CREATE INDEX idx_analytics_created_at ON analytics_events(created_at);

-- System logs indexes
CREATE INDEX idx_logs_bot_id ON system_logs(bot_id);
CREATE INDEX idx_logs_level ON system_logs(level);
CREATE INDEX idx_logs_created_at ON system_logs(created_at);

-- User sessions indexes
CREATE INDEX idx_sessions_master_id ON user_sessions(master_id);
CREATE INDEX idx_sessions_token ON user_sessions(session_token);
CREATE INDEX idx_sessions_expires_at ON user_sessions(expires_at);

-- ============================================
-- VIEWS
-- ============================================

-- Active subscriptions view
CREATE VIEW active_subscriptions_view AS
SELECT
    s.id,
    s.master_id,
    m.telegram_id as master_telegram_id,
    m.full_name as master_name,
    s.plan,
    s.status,
    s.bots_limit,
    s.appointments_limit,
    s.starts_at,
    s.expires_at,
    s.auto_renew,
    COUNT(DISTINCT b.id) as active_bots_count
FROM subscriptions s
JOIN masters m ON m.id = s.master_id
LEFT JOIN bots b ON b.master_id = s.master_id AND b.is_active = true
WHERE s.status = 'active' AND (s.expires_at IS NULL OR s.expires_at > NOW())
GROUP BY s.id, m.telegram_id, m.full_name;

-- Today's appointments view
CREATE VIEW today_appointments_view AS
SELECT
    a.id,
    a.bot_id,
    b.bot_name,
    a.client_id,
    c.first_name || ' ' || COALESCE(c.last_name, '') as client_name,
    c.phone as client_phone,
    s.name as service_name,
    a.start_time,
    a.end_time,
    a.status,
    a.price,
    a.is_prepaid
FROM appointments a
JOIN bots b ON b.id = a.bot_id
JOIN clients c ON c.id = a.client_id
JOIN services s ON s.id = a.service_id
WHERE DATE(a.start_time) = CURRENT_DATE
ORDER BY a.start_time;

-- Bot statistics view
CREATE VIEW bot_statistics_view AS
SELECT
    b.id as bot_id,
    b.bot_name,
    b.master_id,
    COUNT(DISTINCT c.id) as total_clients,
    COUNT(DISTINCT CASE WHEN a.created_at > NOW() - INTERVAL '30 days' THEN a.id END) as appointments_last_30days,
    COUNT(DISTINCT CASE WHEN a.created_at > NOW() - INTERVAL '30 days' AND a.status = 'completed' THEN a.id END) as completed_last_30days,
    COALESCE(SUM(CASE WHEN a.status = 'completed' THEN a.price ELSE 0 END), 0) as total_revenue,
    COALESCE(SUM(CASE WHEN a.status = 'completed' AND a.created_at > NOW() - INTERVAL '30 days' THEN a.price ELSE 0 END), 0) as revenue_last_30days
FROM bots b
LEFT JOIN clients c ON c.bot_id = b.id
LEFT JOIN appointments a ON a.bot_id = b.id
GROUP BY b.id, b.bot_name, b.master_id;

-- ============================================
-- FUNCTIONS
-- ============================================

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Function to check time slot availability
CREATE OR REPLACE FUNCTION check_slot_availability(
    p_bot_id UUID,
    p_start_time TIMESTAMPTZ,
    p_end_time TIMESTAMPTZ
)
RETURNS BOOLEAN AS $$
DECLARE
    conflicting_appointments INTEGER;
BEGIN
    SELECT COUNT(*)
    INTO conflicting_appointments
    FROM appointments
    WHERE bot_id = p_bot_id
        AND start_time < p_end_time
        AND end_time > p_start_time
        AND status IN ('pending', 'confirmed');

    RETURN conflicting_appointments = 0;
END;
$$ LANGUAGE plpgsql;

-- Function to get available time slots
CREATE OR REPLACE FUNCTION get_available_slots(
    p_bot_id UUID,
    p_date DATE,
    p_service_id UUID
)
RETURNS TABLE (slot_time TIMESTAMPTZ, is_available BOOLEAN) AS $$
DECLARE
    v_service_duration INTEGER;
    v_schedule_start TIME;
    v_schedule_end TIME;
    v_is_working_day BOOLEAN;
BEGIN
    -- Get service duration
    SELECT duration_minutes
    INTO v_service_duration
    FROM services
    WHERE id = p_service_id;

    -- Get schedule for the day
    SELECT start_time, end_time, is_working_day
    INTO v_schedule_start, v_schedule_end, v_is_working_day
    FROM schedules
    WHERE bot_id = p_bot_id
        AND day_of_week = EXTRACT(DOW FROM p_date)::INTEGER;

    IF NOT FOUND OR NOT v_is_working_day THEN
        RETURN;
    END IF;

    -- Generate slots
    RETURN QUERY
    WITH time_series AS (
        SELECT generate_series(
            p_date + v_schedule_start,
            p_date + v_schedule_end - (v_service_duration || ' minutes')::INTERVAL,
            '30 minutes'::INTERVAL
        ) as slot_time
    )
    SELECT
        ts.slot_time,
        check_slot_availability(p_bot_id, ts.slot_time, ts.slot_time + (v_service_duration || ' minutes')::INTERVAL)
    FROM time_series ts;
END;
$$ LANGUAGE plpgsql;

-- Function to update client statistics
CREATE OR REPLACE FUNCTION update_client_stats(p_client_id UUID)
RETURNS VOID AS $$
BEGIN
    UPDATE clients
    SET
        total_visits = (
            SELECT COUNT(*)
            FROM appointments
            WHERE client_id = p_client_id AND status = 'completed'
        ),
        total_spent = COALESCE((
            SELECT SUM(price)
            FROM appointments
            WHERE client_id = p_client_id AND status = 'completed'
        ), 0),
        updated_at = NOW()
    WHERE id = p_client_id;
END;
$$ LANGUAGE plpgsql;

-- ============================================
-- TRIGGERS
-- ============================================

-- Update updated_at for masters
CREATE TRIGGER masters_updated_at
    BEFORE UPDATE ON masters
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Update updated_at for subscriptions
CREATE TRIGGER subscriptions_updated_at
    BEFORE UPDATE ON subscriptions
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Update updated_at for payments
CREATE TRIGGER payments_updated_at
    BEFORE UPDATE ON payments
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Update updated_at for bots
CREATE TRIGGER bots_updated_at
    BEFORE UPDATE ON bots
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Update updated_at for services
CREATE TRIGGER services_updated_at
    BEFORE UPDATE ON services
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Update updated_at for schedules
CREATE TRIGGER schedules_updated_at
    BEFORE UPDATE ON schedules
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Update updated_at for clients
CREATE TRIGGER clients_updated_at
    BEFORE UPDATE ON clients
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Update updated_at for appointments
CREATE TRIGGER appointments_updated_at
    BEFORE UPDATE ON appointments
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Trigger to update client stats after appointment completion
CREATE TRIGGER appointment_completed_update_client_stats
    AFTER UPDATE ON appointments
    FOR EACH ROW
    WHEN (OLD.status != 'completed' AND NEW.status = 'completed')
    EXECUTE FUNCTION update_client_stats(NEW.client_id);

-- ============================================
-- CLEANUP FUNCTIONS
-- ============================================

-- Function to delete old system logs (keep last 30 days)
CREATE OR REPLACE FUNCTION cleanup_old_logs()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM system_logs
    WHERE created_at < NOW() - INTERVAL '30 days';

    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- Function to delete old sent notifications
CREATE OR REPLACE FUNCTION cleanup_old_notifications()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM notifications_queue
    WHERE status IN ('sent', 'failed')
        AND created_at < NOW() - INTERVAL '7 days';

    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- ============================================
-- END OF SCHEMA
-- ============================================

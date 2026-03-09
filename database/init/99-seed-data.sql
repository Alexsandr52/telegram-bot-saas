-- ============================================
-- Seed Data (Optional)
-- Development/Test Data
-- ============================================

-- Uncomment the queries below to insert test data

-- ============================================
-- Insert Test Master
-- ============================================
-- INSERT INTO masters (telegram_id, username, full_name, phone, is_active)
-- VALUES (123456789, 'test_master', 'Иван Иванов', '+79001234567', true);

-- ============================================
-- Insert Test Subscription
-- ============================================
-- INSERT INTO subscriptions (master_id, plan, status, bots_limit, appointments_limit, expires_at)
-- VALUES (
--     (SELECT id FROM masters WHERE telegram_id = 123456789),
--     'pro',
--     'active',
--     3,
--     NULL,
--     NOW() + INTERVAL '30 days'
-- );

-- ============================================
-- Insert Test Bot
-- ============================================
-- INSERT INTO bots (master_id, bot_token, bot_username, bot_name, business_name, container_status, is_active)
-- VALUES (
--     (SELECT id FROM masters WHERE telegram_id = 123456789),
--     'encrypted_token_here',
--     'test_bot',
--     'Test Bot',
--     'Иванов Студия',
--     'running',
--     true
-- );

-- ============================================
-- Insert Test Services
-- ============================================
-- INSERT INTO services (bot_id, name, description, price, duration_minutes, is_active, sort_order)
-- VALUES
--     ((SELECT id FROM bots WHERE bot_username = 'test_bot'), 'Мужская стрижка', 'Классическая мужская стрижка', 1500.00, 60, true, 1),
--     ((SELECT id FROM bots WHERE bot_username = 'test_bot'), 'Окрашивание', 'Окрашивание волос', 3000.00, 120, true, 2),
--     ((SELECT id FROM bots WHERE bot_username = 'test_bot'), 'Укладка', 'Укладка и укладка волос', 1000.00, 45, true, 3);

-- ============================================
-- Insert Test Schedule (Mon-Fri 9:00-18:00)
-- ============================================
-- INSERT INTO schedules (bot_id, day_of_week, start_time, end_time, is_working_day)
-- SELECT id, day, '09:00:00', '18:00:00', true
-- FROM (SELECT id FROM bots WHERE bot_username = 'test_bot') CROSS JOIN (SELECT generate_series(0, 4) AS day) AS days;

-- ============================================
-- Insert Test Schedule Exceptions (Weekend)
-- ============================================
-- INSERT INTO schedules (bot_id, day_of_week, is_working_day)
-- SELECT id, day, false
-- FROM (SELECT id FROM bots WHERE bot_username = 'test_bot') CROSS JOIN (SELECT 5 AS day UNION SELECT 6) AS days;

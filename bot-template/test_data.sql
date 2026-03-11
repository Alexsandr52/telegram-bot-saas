-- ============================================
-- Test Data for Bot Template
-- Run this to create test master, bot, and services
-- ============================================

-- 1. Create Test Master
INSERT INTO masters (telegram_id, username, full_name, phone, is_active)
VALUES (123456789, 'test_master', 'Test Master', '+79001234567', true)
ON CONFLICT (telegram_id) DO UPDATE SET
    username = EXCLUDED.username,
    full_name = EXCLUDED.full_name;

-- 2. Create Test Bot
INSERT INTO bots (
    master_id,
    bot_token,
    bot_username,
    bot_name,
    business_name,
    business_description,
    business_address,
    business_phone,
    container_status,
    timezone,
    language,
    is_active,
    settings
)
SELECT 
    (SELECT id FROM masters WHERE telegram_id = 123456789),
    'ENCRYPTED_TOKEN_HERE',  -- Replace with real encrypted token
    'TestSalonBot',
    'Test Salon Bot',
    'Салон Красоты Тест',
    'Лучшая студия города! Работаем с 9:00 до 18:00.',
    'ул. Тестовая, д. 1',
    '+79001234567',
    'stopped',
    'Europe/Moscow',
    'ru',
    true,
    '{
        "custom_commands": [
            {
                "command": "c",
                "description": "Услуги",
                "handler_type": "catalog",
                "enabled": true
            },
            {
                "command": "info",
                "description": "О нас",
                "handler_type": "about",
                "enabled": true
            }
        ]
    }'::jsonb
WHERE NOT EXISTS (
    SELECT 1 FROM bots WHERE bot_username = 'TestSalonBot'
);

-- 3. Create Services
INSERT INTO services (bot_id, name, description, price, duration_minutes, is_active, sort_order)
SELECT 
    id,
    'Стрижка мужская',
    'Классическая мужская стрижка с мытьем головы',
    1500,
    60,
    true,
    1
FROM bots WHERE bot_username = 'TestSalonBot'
ON CONFLICT DO NOTHING;

INSERT INTO services (bot_id, name, description, price, duration_minutes, is_active, sort_order)
SELECT 
    id,
    'Окрашивание',
    'Окрашивание волос в один тон',
    3000,
    120,
    true,
    2
FROM bots WHERE bot_username = 'TestSalonBot'
ON CONFLICT DO NOTHING;

INSERT INTO services (bot_id, name, description, price, duration_minutes, is_active, sort_order)
SELECT 
    id,
    'Мужская укладка',
    'Укладка волос мужским стайлем',
    1000,
    45,
    true,
    3
FROM bots WHERE bot_username = 'TestSalonBot'
ON CONFLICT DO NOTHING;

INSERT INTO services (bot_id, name, description, price, duration_minutes, is_active, sort_order)
SELECT 
    id,
    'Комплекс "Стрижка + Укладка"',
    'Стрижка + укладка с учётом особенностей вашего типа лица',
    2000,
    90,
    true,
    4
FROM bots WHERE bot_username = 'TestSalonBot'
ON CONFLICT DO NOTHING;

-- 4. Create Schedule (Mon-Fri 9:00-18:00)
INSERT INTO schedules (bot_id, day_of_week, start_time, end_time, is_working_day)
SELECT id, 0, '09:00:00', '18:00:00', true FROM bots WHERE bot_username = 'TestSalonBot'
ON CONFLICT (bot_id, day_of_week) DO UPDATE SET
    start_time = EXCLUDED.start_time,
    end_time = EXCLUDED.end_time,
    is_working_day = EXCLUDED.is_working_day;

INSERT INTO schedules (bot_id, day_of_week, start_time, end_time, is_working_day)
SELECT id, 1, '09:00:00', '18:00:00', true FROM bots WHERE bot_username = 'TestSalonBot'
ON CONFLICT (bot_id, day_of_week) DO UPDATE SET
    start_time = EXCLUDED.start_time,
    end_time = EXCLUDED.end_time,
    is_working_day = EXCLUDED.is_working_day;

INSERT INTO schedules (bot_id, day_of_week, start_time, end_time, is_working_day)
SELECT id, 2, '09:00:00', '18:00:00', true FROM bots WHERE bot_username = 'TestSalonBot'
ON CONFLICT (bot_id, day_of_week) DO UPDATE SET
    start_time = EXCLUDED.start_time,
    end_time = EXCLUDED.end_time,
    is_working_day = EXCLUDED.is_working_day;

INSERT INTO schedules (bot_id, day_of_week, start_time, end_time, is_working_day)
SELECT id, 3, '09:00:00', '18:00:00', true FROM bots WHERE bot_username = 'TestSalonBot'
ON CONFLICT (bot_id, day_of_week) DO UPDATE SET
    start_time = EXCLUDED.start_time,
    end_time = EXCLUDED.end_time,
    is_working_day = EXCLUDED.is_working_day;

INSERT INTO schedules (bot_id, day_of_week, start_time, end_time, is_working_day)
SELECT id, 4, '09:00:00', '18:00:00', true FROM bots WHERE bot_username = 'TestSalonBot'
ON CONFLICT (bot_id, day_of_week) DO UPDATE SET
    start_time = EXCLUDED.start_time,
    end_time = EXCLUDED.end_time,
    is_working_day = EXCLUDED.is_working_day;

-- 5. Weekend (not working days)
INSERT INTO schedules (bot_id, day_of_week, start_time, end_time, is_working_day)
SELECT id, 5, '09:00:00', '18:00:00', false FROM bots WHERE bot_username = 'TestSalonBot'
ON CONFLICT (bot_id, day_of_week) DO UPDATE SET
    is_working_day = EXCLUDED.is_working_day;

INSERT INTO schedules (bot_id, day_of_week, start_time, end_time, is_working_day)
SELECT id, 6, '09:00:00', '18:00:00', false FROM bots WHERE bot_username = 'TestSalonBot'
ON CONFLICT (bot_id, day_of_week) DO UPDATE SET
    is_working_day = EXCLUDED.is_working_day;

-- ============================================
-- Notes:
-- 
-- 1. Replace 'ENCRYPTED_TOKEN_HERE' with actual encrypted bot token
--    Use encryption utility from platform-bot to encrypt token
--
-- 2. To get BOT_ID, run:
--    SELECT id FROM bots WHERE bot_username = 'TestSalonBot';
--
-- 3. To test locally, update bot-template/.env:
--    BOT_ID=<uuid from step 2>
--    BOT_TOKEN=<your actual bot token>
--
-- ============================================

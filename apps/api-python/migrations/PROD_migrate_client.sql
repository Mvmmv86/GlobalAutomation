-- =====================================================
-- GLOBALTRADE_PROD - CLIENT MIGRATION SCRIPT
-- Migrates client: trader@tradingplatform.com
-- From: GlobalTrade (DEV) -> GlobalTrade_PROD
-- Generated: 2025-11-27
-- =====================================================

-- ============================================================================
-- STEP 1: Insert User
-- ============================================================================

INSERT INTO users (
    id, email, name, password_hash, is_active, is_verified,
    totp_secret, totp_enabled, last_login_at,
    created_at, updated_at, is_admin
) VALUES (
    '37727e70-9445-4183-ac37-e9dd2fe3edce',
    'trader@tradingplatform.com',
    'Pro Trader',
    '$2b$12$6kxzajnuTkOGlVtlxgDux.IKYBDSIPVjBMKY6GoFLzo336XcSlQaa',
    true,
    true,
    'DEMO_SECRET_KEY_12345678',
    true,
    NULL,
    '2025-08-16 18:25:19.149748+00:00',
    '2025-08-16 18:25:19.149748+00:00',
    true
) ON CONFLICT (id) DO NOTHING;

-- ============================================================================
-- STEP 2: Insert Exchange Accounts
-- ============================================================================

-- Binance Account
INSERT INTO exchange_accounts (
    id, name, exchange, api_key, secret_key, passphrase,
    testnet, is_active, is_main, user_id, created_at, updated_at
) VALUES (
    '5a852638-fb08-46e5-94fc-efc531262101',
    'Binance',
    'binance',
    'oObUKzS5R5vlMWyb5G7we1P0SEiVbdUVLwpWJilqFDbSwDOkfk28hKV7HIp1Y8i3',
    'jK1CYuLmQoLcJCfAIVDYntHdmaPHlIl5VZCASznZOO1hKSjNERa5XfCFEGItFpq8',
    NULL,
    false,
    true,
    false,
    '37727e70-9445-4183-ac37-e9dd2fe3edce',
    '2025-10-26 00:43:52.558111+00:00',
    '2025-10-26 00:43:52.558111+00:00'
) ON CONFLICT (id) DO NOTHING;

-- BingX Account (Main)
INSERT INTO exchange_accounts (
    id, name, exchange, api_key, secret_key, passphrase,
    testnet, is_active, is_main, user_id, created_at, updated_at
) VALUES (
    '8a42489d-8b66-405d-ab04-a9bbaa091e31',
    'BingX_nova',
    'bingx',
    'YK7lnc70VwKVVRzzcvtfnhgl4blz8w0GsTWTOXhyoC3P9NYmF32ymDQXaJu8kzM2R2KRpQAJW86pdLQrg',
    '4gxl34k6GbE1TfyFhaAAD13JmkGwLYti2ZcROWhHQGYzdpqAx5Isky5dHYZTFHC1zJFwslru61IMc3jW9Fw',
    NULL,
    false,
    true,
    true,
    '37727e70-9445-4183-ac37-e9dd2fe3edce',
    '2025-11-12 14:47:04.599536+00:00',
    '2025-11-12 14:47:04.599536+00:00'
) ON CONFLICT (id) DO NOTHING;

-- ============================================================================
-- STEP 3: Insert Webhook
-- ============================================================================

INSERT INTO webhooks (
    id, name, url_path, secret, status, is_public,
    rate_limit_per_minute, rate_limit_per_hour, max_retries, retry_delay_seconds,
    allowed_ips, required_headers, payload_validation_schema,
    total_deliveries, successful_deliveries, failed_deliveries,
    last_delivery_at, last_success_at, auto_pause_on_errors,
    error_threshold, consecutive_errors, user_id,
    default_margin_usd, default_leverage, default_stop_loss_pct, default_take_profit_pct,
    created_at, updated_at
) VALUES (
    'd7b0f9c0-2cde-411a-9601-5e2c23a2ef79',
    'Bot BingX FUTUROS Teste',
    'bingx-futures-test',
    '2584b393-adc2-4662-80fa-ba5e41cb1dae',
    'active',
    false,
    60, 1000, 3, 60,
    NULL, NULL, NULL,
    0, 0, 0,  -- Reset counters for PROD
    NULL, NULL,
    true, 10, 0,
    '37727e70-9445-4183-ac37-e9dd2fe3edce',
    10.00, 5, 2.00, 3.00,
    '2025-11-10 20:49:26.272879+00:00',
    NOW()
) ON CONFLICT (id) DO NOTHING;

-- ============================================================================
-- STEP 4: Insert Bots
-- ============================================================================

-- Bot: BINGX_SOL
INSERT INTO bots (
    id, name, description, market_type, status,
    master_webhook_path, master_secret,
    default_leverage, default_margin_usd, default_stop_loss_pct, default_take_profit_pct,
    allowed_directions, total_subscribers, total_signals_sent,
    avg_win_rate, avg_pnl_pct, created_at, updated_at
) VALUES (
    '19725a81-10d9-4a11-8842-7976144d7b24',
    'BINGX_SOL',
    'testestsetset',
    'futures',
    'active',
    's-hbldbdwdfo66pj',
    'prod_secret_sol_' || gen_random_uuid()::text,
    10, 20.00, 3.00, 5.00,
    'both', 0, 0,  -- Reset counters for PROD
    NULL, NULL,
    '2025-11-05 22:32:39.340836',
    NOW()
) ON CONFLICT (id) DO NOTHING;

-- Bot: ADA_BINGx 5 min
INSERT INTO bots (
    id, name, description, market_type, status,
    master_webhook_path, master_secret,
    default_leverage, default_margin_usd, default_stop_loss_pct, default_take_profit_pct,
    allowed_directions, total_subscribers, total_signals_sent,
    avg_win_rate, avg_pnl_pct, created_at, updated_at
) VALUES (
    '495bddc3-0c13-47f1-ad20-73320c53a52d',
    'ADA_BINGx 5 min',
    'testsetset',
    'futures',
    'active',
    'a-vex95uujp4nwdc',
    'prod_secret_ada_' || gen_random_uuid()::text,
    10, 10.00, 3.00, 5.00,
    'both', 0, 0,
    NULL, NULL,
    '2025-11-05 23:22:50.910858',
    NOW()
) ON CONFLICT (id) DO NOTHING;

-- Bot: ETH_TPO_Bingx
INSERT INTO bots (
    id, name, description, market_type, status,
    master_webhook_path, master_secret,
    default_leverage, default_margin_usd, default_stop_loss_pct, default_take_profit_pct,
    allowed_directions, total_subscribers, total_signals_sent,
    avg_win_rate, avg_pnl_pct, created_at, updated_at
) VALUES (
    'bcc628a3-85bb-46de-8719-d9d88bab4370',
    'ETH_TPO_Bingx',
    'platafomra testeeee',
    'futures',
    'active',
    'e-7j8zyojw5srx71',
    'prod_secret_eth_' || gen_random_uuid()::text,
    10, 5.00, 2.00, 7.00,
    'both', 0, 0,
    NULL, NULL,
    '2025-11-05 19:29:49.969992',
    NOW()
) ON CONFLICT (id) DO NOTHING;

-- Bot: AAVE_BINGx 5 min
INSERT INTO bots (
    id, name, description, market_type, status,
    master_webhook_path, master_secret,
    default_leverage, default_margin_usd, default_stop_loss_pct, default_take_profit_pct,
    allowed_directions, total_subscribers, total_signals_sent,
    avg_win_rate, avg_pnl_pct, created_at, updated_at
) VALUES (
    'cdce9847-bd0a-44c7-a4db-1839234440a8',
    'AAVE_BINGx 5 min',
    'testestsetsets',
    'futures',
    'active',
    'b-7dsxpor313vb9t',
    'prod_secret_aave_' || gen_random_uuid()::text,
    10, 10.00, 3.00, 5.00,
    'both', 0, 0,
    NULL, NULL,
    '2025-11-05 23:15:41.794331',
    NOW()
) ON CONFLICT (id) DO NOTHING;

-- ============================================================================
-- STEP 5: Insert Bot Subscriptions
-- ============================================================================

-- Subscription: BINGX_SOL
INSERT INTO bot_subscriptions (
    id, user_id, bot_id, exchange_account_id, status,
    custom_leverage, custom_margin_usd, custom_stop_loss_pct, custom_take_profit_pct,
    max_daily_loss_usd, max_concurrent_positions,
    current_daily_loss_usd, current_positions,
    total_signals_received, total_orders_executed, total_orders_failed,
    total_pnl_usd, win_count, loss_count,
    created_at, updated_at, last_signal_at
) VALUES (
    'e6d9e3b9-7d73-4266-8602-9dd57d8b9ab6',
    '37727e70-9445-4183-ac37-e9dd2fe3edce',
    '19725a81-10d9-4a11-8842-7976144d7b24',
    '8a42489d-8b66-405d-ab04-a9bbaa091e31',
    'active',
    NULL, NULL, NULL, NULL,
    20.00, 1,
    0.00, 0,
    0, 0, 0,  -- Reset counters for PROD
    0.00, 0, 0,
    NOW(), NOW(), NULL
) ON CONFLICT (id) DO NOTHING;

-- Subscription: ETH_TPO_Bingx
INSERT INTO bot_subscriptions (
    id, user_id, bot_id, exchange_account_id, status,
    custom_leverage, custom_margin_usd, custom_stop_loss_pct, custom_take_profit_pct,
    max_daily_loss_usd, max_concurrent_positions,
    current_daily_loss_usd, current_positions,
    total_signals_received, total_orders_executed, total_orders_failed,
    total_pnl_usd, win_count, loss_count,
    created_at, updated_at, last_signal_at
) VALUES (
    '43bb4fe3-ed59-4215-baa1-f11b13a9781c',
    '37727e70-9445-4183-ac37-e9dd2fe3edce',
    'bcc628a3-85bb-46de-8719-d9d88bab4370',
    '8a42489d-8b66-405d-ab04-a9bbaa091e31',
    'active',
    NULL, NULL, NULL, NULL,
    20.00, 1,
    0.00, 0,
    0, 0, 0,
    0.00, 0, 0,
    NOW(), NOW(), NULL
) ON CONFLICT (id) DO NOTHING;

-- Subscription: AAVE_BINGx 5 min
INSERT INTO bot_subscriptions (
    id, user_id, bot_id, exchange_account_id, status,
    custom_leverage, custom_margin_usd, custom_stop_loss_pct, custom_take_profit_pct,
    max_daily_loss_usd, max_concurrent_positions,
    current_daily_loss_usd, current_positions,
    total_signals_received, total_orders_executed, total_orders_failed,
    total_pnl_usd, win_count, loss_count,
    created_at, updated_at, last_signal_at
) VALUES (
    'b83304ff-7bab-4ed4-b738-ed158a381898',
    '37727e70-9445-4183-ac37-e9dd2fe3edce',
    'cdce9847-bd0a-44c7-a4db-1839234440a8',
    '8a42489d-8b66-405d-ab04-a9bbaa091e31',
    'active',
    NULL, NULL, NULL, NULL,
    30.00, 2,
    0.00, 0,
    0, 0, 0,
    0.00, 0, 0,
    NOW(), NOW(), NULL
) ON CONFLICT (id) DO NOTHING;

-- Subscription: ADA_BINGx 5 min
INSERT INTO bot_subscriptions (
    id, user_id, bot_id, exchange_account_id, status,
    custom_leverage, custom_margin_usd, custom_stop_loss_pct, custom_take_profit_pct,
    max_daily_loss_usd, max_concurrent_positions,
    current_daily_loss_usd, current_positions,
    total_signals_received, total_orders_executed, total_orders_failed,
    total_pnl_usd, win_count, loss_count,
    created_at, updated_at, last_signal_at
) VALUES (
    '77fa0dd3-7129-44b4-b17f-66f53ef0406b',
    '37727e70-9445-4183-ac37-e9dd2fe3edce',
    '495bddc3-0c13-47f1-ad20-73320c53a52d',
    '8a42489d-8b66-405d-ab04-a9bbaa091e31',
    'active',
    NULL, NULL, NULL, NULL,
    30.00, 2,
    0.00, 0,
    0, 0, 0,
    0.00, 0, 0,
    NOW(), NOW(), NULL
) ON CONFLICT (id) DO NOTHING;

-- ============================================================================
-- STEP 6: Update bot subscriber counts
-- ============================================================================

UPDATE bots SET total_subscribers = (
    SELECT COUNT(*) FROM bot_subscriptions WHERE bot_id = bots.id AND status = 'active'
);

-- ============================================================================
-- STEP 7: Verification Query
-- ============================================================================

SELECT 'Migration Complete!' as status,
       (SELECT COUNT(*) FROM users WHERE email = 'trader@tradingplatform.com') as users_migrated,
       (SELECT COUNT(*) FROM exchange_accounts WHERE user_id = '37727e70-9445-4183-ac37-e9dd2fe3edce') as exchange_accounts,
       (SELECT COUNT(*) FROM webhooks WHERE user_id = '37727e70-9445-4183-ac37-e9dd2fe3edce') as webhooks,
       (SELECT COUNT(*) FROM bots) as bots,
       (SELECT COUNT(*) FROM bot_subscriptions WHERE user_id = '37727e70-9445-4183-ac37-e9dd2fe3edce') as subscriptions;

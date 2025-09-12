-- =====================================================
-- TRADING PLATFORM - DEMO DATA INSERTION
-- Execute this AFTER creating the schema
-- =====================================================

-- Insert demo users
INSERT INTO users (id, email, name, password_hash, is_active, is_verified, totp_enabled, totp_secret) VALUES
('550e8400-e29b-41d4-a716-446655440001', 'demo@tradingplatform.com', 'Demo User', '$2b$12$demo_password_hash_123456789abcdef', true, true, false, null),
('550e8400-e29b-41d4-a716-446655440002', 'trader@tradingplatform.com', 'Pro Trader', '$2b$12$trader_password_hash_123456789abcdef', true, true, true, 'DEMO_SECRET_KEY_12345678'),
('550e8400-e29b-41d4-a716-446655440003', 'admin@tradingplatform.com', 'Platform Admin', '$2b$12$admin_password_hash_123456789abcdef', true, true, true, 'ADMIN_SECRET_KEY_87654321');

-- Insert API keys
INSERT INTO api_keys (id, name, key_hash, prefix, is_active, permissions, user_id) VALUES
('660e8400-e29b-41d4-a716-446655440001', 'Demo API Key', 'hashed_demo_key_123456789abcdef', 'tp_demo1', true, '{"trading": true, "read_only": false}', '550e8400-e29b-41d4-a716-446655440001'),
('660e8400-e29b-41d4-a716-446655440002', 'Trader API Key', 'hashed_trader_key_123456789abcdef', 'tp_trade', true, '{"trading": true, "read_only": false}', '550e8400-e29b-41d4-a716-446655440002'),
('660e8400-e29b-41d4-a716-446655440003', 'Admin API Key', 'hashed_admin_key_123456789abcdef', 'tp_admin', true, '{"trading": true, "read_only": false, "admin": true}', '550e8400-e29b-41d4-a716-446655440003');

-- Insert exchange accounts
INSERT INTO exchange_accounts (id, name, exchange, api_key, secret_key, testnet, is_active, user_id) VALUES
('770e8400-e29b-41d4-a716-446655440001', 'Demo Binance Testnet', 'binance', 'encrypted_demo_binance_api_key', 'encrypted_demo_binance_secret', true, true, '550e8400-e29b-41d4-a716-446655440001'),
('770e8400-e29b-41d4-a716-446655440002', 'Demo Bybit Testnet', 'bybit', 'encrypted_demo_bybit_api_key', 'encrypted_demo_bybit_secret', true, true, '550e8400-e29b-41d4-a716-446655440001'),
('770e8400-e29b-41d4-a716-446655440003', 'Trader Binance Testnet', 'binance', 'encrypted_trader_binance_api_key', 'encrypted_trader_binance_secret', true, true, '550e8400-e29b-41d4-a716-446655440002'),
('770e8400-e29b-41d4-a716-446655440004', 'Admin Binance Live', 'binance', 'encrypted_admin_binance_api_key', 'encrypted_admin_binance_secret', false, true, '550e8400-e29b-41d4-a716-446655440003');

-- Insert webhooks
INSERT INTO webhooks (id, name, url_path, secret, status, user_id) VALUES
('880e8400-e29b-41d4-a716-446655440001', 'Demo TradingView Strategy', 'webhook_demo_abc123', 'demo_webhook_secret_xyz789', 'active', '550e8400-e29b-41d4-a716-446655440001'),
('880e8400-e29b-41d4-a716-446655440002', 'Pro Trading Bot', 'webhook_trader_def456', 'trader_webhook_secret_uvw456', 'active', '550e8400-e29b-41d4-a716-446655440002'),
('880e8400-e29b-41d4-a716-446655440003', 'Admin Strategy Monitor', 'webhook_admin_ghi789', 'admin_webhook_secret_rst123', 'active', '550e8400-e29b-41d4-a716-446655440003');

-- Insert sample orders
INSERT INTO orders (id, client_order_id, symbol, side, type, status, quantity, price, filled_quantity, average_fill_price, fees_paid, fee_currency, source, exchange_account_id) VALUES
('990e8400-e29b-41d4-a716-446655440001', 'demo_order_001_btc', 'BTCUSDT', 'buy', 'limit', 'filled', 0.01000000, 45000.00000000, 0.01000000, 45000.00000000, 0.45000000, 'USDT', 'demo', '770e8400-e29b-41d4-a716-446655440001'),
('990e8400-e29b-41d4-a716-446655440002', 'demo_order_002_eth', 'ETHUSDT', 'buy', 'market', 'filled', 0.10000000, null, 0.10000000, 2800.00000000, 0.28000000, 'USDT', 'demo', '770e8400-e29b-41d4-a716-446655440001'),
('990e8400-e29b-41d4-a716-446655440003', 'trader_order_001_btc', 'BTCUSDT', 'sell', 'limit', 'open', 0.02000000, 46000.00000000, 0.00000000, null, 0.00000000, null, 'webhook', '770e8400-e29b-41d4-a716-446655440003');

-- Insert sample positions
INSERT INTO positions (id, symbol, side, status, size, entry_price, mark_price, unrealized_pnl, initial_margin, maintenance_margin, leverage, liquidation_price, exchange_account_id) VALUES
('aa0e8400-e29b-41d4-a716-446655440001', 'BTCUSDT', 'long', 'open', 0.01000000, 45000.00000000, 46000.00000000, 10.00000000, 45.00000000, 22.50000000, 10.00, 40500.00000000, '770e8400-e29b-41d4-a716-446655440001'),
('aa0e8400-e29b-41d4-a716-446655440002', 'ETHUSDT', 'long', 'open', 0.10000000, 2800.00000000, 2850.00000000, 5.00000000, 28.00000000, 14.00000000, 10.00, 2520.00000000, '770e8400-e29b-41d4-a716-446655440001'),
('aa0e8400-e29b-41d4-a716-446655440003', 'BTCUSDT', 'short', 'open', 0.01500000, 46000.00000000, 45800.00000000, 3.00000000, 69.00000000, 34.50000000, 10.00, 51100.00000000, '770e8400-e29b-41d4-a716-446655440003');

-- Insert sample webhook delivery
INSERT INTO webhook_deliveries (id, status, payload, headers, source_ip, hmac_valid, ip_allowed, headers_valid, payload_valid, orders_created, orders_executed, webhook_id) VALUES
('bb0e8400-e29b-41d4-a716-446655440001', 'success', '{"action": "buy", "symbol": "BTCUSDT", "quantity": 0.01, "price": 45000}', '{"Content-Type": "application/json", "User-Agent": "TradingView-Webhook"}', '192.168.1.100', true, true, true, true, 1, 1, '880e8400-e29b-41d4-a716-446655440001');

-- =====================================================
-- VALIDATION QUERIES
-- =====================================================

-- Count all records
SELECT 
    (SELECT COUNT(*) FROM users) as users_count,
    (SELECT COUNT(*) FROM api_keys) as api_keys_count,
    (SELECT COUNT(*) FROM exchange_accounts) as accounts_count,
    (SELECT COUNT(*) FROM webhooks) as webhooks_count,
    (SELECT COUNT(*) FROM orders) as orders_count,
    (SELECT COUNT(*) FROM positions) as positions_count,
    (SELECT COUNT(*) FROM webhook_deliveries) as deliveries_count;

-- Show user data with relationships
SELECT 
    u.email,
    u.name,
    u.is_active,
    COUNT(DISTINCT ea.id) as exchange_accounts,
    COUNT(DISTINCT w.id) as webhooks,
    COUNT(DISTINCT o.id) as orders,
    COUNT(DISTINCT p.id) as positions
FROM users u
LEFT JOIN exchange_accounts ea ON u.id = ea.user_id
LEFT JOIN webhooks w ON u.id = w.user_id
LEFT JOIN orders o ON ea.id = o.exchange_account_id
LEFT JOIN positions p ON ea.id = p.exchange_account_id
GROUP BY u.id, u.email, u.name, u.is_active
ORDER BY u.email;

SELECT 'Demo Data Inserted Successfully! 🎉' as message,
       'Users, accounts, webhooks, orders, and positions created!' as details;
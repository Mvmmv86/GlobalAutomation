-- Fix exchange_accounts schema
-- Add missing columns that the code expects

-- Add api_key_encrypted column if it doesn't exist
ALTER TABLE exchange_accounts 
ADD COLUMN IF NOT EXISTS api_key_encrypted TEXT;

-- Add secret_key_encrypted column if it doesn't exist
ALTER TABLE exchange_accounts 
ADD COLUMN IF NOT EXISTS secret_key_encrypted TEXT;

-- Add passphrase_encrypted column if it doesn't exist
ALTER TABLE exchange_accounts 
ADD COLUMN IF NOT EXISTS passphrase_encrypted TEXT;

-- Add other commonly needed columns
ALTER TABLE exchange_accounts 
ADD COLUMN IF NOT EXISTS is_testnet BOOLEAN DEFAULT false;

ALTER TABLE exchange_accounts 
ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT true;

ALTER TABLE exchange_accounts 
ADD COLUMN IF NOT EXISTS last_sync TIMESTAMP;

ALTER TABLE exchange_accounts 
ADD COLUMN IF NOT EXISTS error_count INTEGER DEFAULT 0;

ALTER TABLE exchange_accounts 
ADD COLUMN IF NOT EXISTS last_error TEXT;

-- Insert a test exchange account for testing
INSERT INTO exchange_accounts (
    user_id, name, exchange, api_key_encrypted, 
    secret_key_encrypted, is_testnet, is_active
)
SELECT 
    id, 'Binance Demo', 'binance', 'demo_api_key', 
    'demo_secret_key', true, true
FROM users 
LIMIT 1
ON CONFLICT (user_id, name) DO UPDATE SET
    api_key_encrypted = 'demo_api_key',
    secret_key_encrypted = 'demo_secret_key',
    is_testnet = true,
    is_active = true;
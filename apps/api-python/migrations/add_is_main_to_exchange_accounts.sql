-- Migration: Add is_main column to exchange_accounts table
-- Purpose: Allow marking one account as the main account for dashboard data

-- Add the is_main column
ALTER TABLE exchange_accounts
ADD COLUMN is_main BOOLEAN DEFAULT FALSE;

-- Create index for faster queries on is_main
CREATE INDEX idx_exchange_accounts_is_main ON exchange_accounts(is_main);

-- Ensure only one account per exchange can be main
-- (We'll handle this in the application logic)

-- Add comment to the column
COMMENT ON COLUMN exchange_accounts.is_main IS 'Indicates if this is the main account used for dashboard data';
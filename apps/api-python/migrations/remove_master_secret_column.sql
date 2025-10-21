-- Migration: Remove master_secret column from bots table
-- Date: 2025-10-21
-- Description: Remove master_secret column as authentication is now done via unique webhook_path only

-- Remove the master_secret column
ALTER TABLE bots DROP COLUMN IF EXISTS master_secret;

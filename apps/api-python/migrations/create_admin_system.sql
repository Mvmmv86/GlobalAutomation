-- ============================================================================
-- Migration: Admin System
-- Description: Creates admin users table and related structures
-- Date: 2025-10-13
-- ============================================================================

-- Create admins table
CREATE TABLE IF NOT EXISTS admins (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role VARCHAR(50) NOT NULL DEFAULT 'admin', -- admin, super_admin
    permissions JSONB DEFAULT '{"bots": true, "users": true, "webhooks": true, "reports": true}'::jsonb,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by UUID REFERENCES admins(id),

    CONSTRAINT unique_admin_user UNIQUE(user_id)
);

-- Create index for faster lookups
CREATE INDEX IF NOT EXISTS idx_admins_user_id ON admins(user_id);
CREATE INDEX IF NOT EXISTS idx_admins_is_active ON admins(is_active);

-- Add is_admin flag to users table (if not exists)
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_name = 'users' AND column_name = 'is_admin') THEN
        ALTER TABLE users ADD COLUMN is_admin BOOLEAN DEFAULT false;
    END IF;
END $$;

-- Create index on users.is_admin
CREATE INDEX IF NOT EXISTS idx_users_is_admin ON users(is_admin);

-- Create function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_admins_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger for updated_at
DROP TRIGGER IF EXISTS trigger_update_admins_updated_at ON admins;
CREATE TRIGGER trigger_update_admins_updated_at
    BEFORE UPDATE ON admins
    FOR EACH ROW
    EXECUTE FUNCTION update_admins_updated_at();

-- Create admin activity log table
CREATE TABLE IF NOT EXISTS admin_activity_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    admin_id UUID NOT NULL REFERENCES admins(id) ON DELETE CASCADE,
    action VARCHAR(100) NOT NULL, -- created_bot, updated_user, deleted_webhook, etc.
    entity_type VARCHAR(50) NOT NULL, -- bot, user, webhook, etc.
    entity_id UUID,
    details JSONB,
    ip_address VARCHAR(45),
    user_agent TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for activity log
CREATE INDEX IF NOT EXISTS idx_admin_activity_admin_id ON admin_activity_log(admin_id);
CREATE INDEX IF NOT EXISTS idx_admin_activity_entity ON admin_activity_log(entity_type, entity_id);
CREATE INDEX IF NOT EXISTS idx_admin_activity_created_at ON admin_activity_log(created_at DESC);

-- Insert default super admin (using existing demo user)
-- This will be the first admin that can create other admins
DO $$
DECLARE
    demo_user_id UUID;
BEGIN
    -- Get demo user ID
    SELECT id INTO demo_user_id FROM users WHERE email = 'demo@tradingplatform.com' LIMIT 1;

    IF demo_user_id IS NOT NULL THEN
        -- Update user to be admin
        UPDATE users SET is_admin = true WHERE id = demo_user_id;

        -- Insert into admins table
        INSERT INTO admins (user_id, role, permissions, is_active)
        VALUES (
            demo_user_id,
            'super_admin',
            '{"bots": true, "users": true, "webhooks": true, "reports": true, "admins": true}'::jsonb,
            true
        )
        ON CONFLICT (user_id) DO UPDATE
        SET role = 'super_admin',
            permissions = '{"bots": true, "users": true, "webhooks": true, "reports": true, "admins": true}'::jsonb,
            is_active = true;

        RAISE NOTICE 'Super admin created successfully for user: %', demo_user_id;
    ELSE
        RAISE NOTICE 'Demo user not found, admin not created';
    END IF;
END $$;

-- Grant necessary permissions
GRANT SELECT, INSERT, UPDATE, DELETE ON admins TO PUBLIC;
GRANT SELECT, INSERT ON admin_activity_log TO PUBLIC;

-- Success message
DO $$
BEGIN
    RAISE NOTICE '✅ Admin system migration completed successfully!';
    RAISE NOTICE '👤 Default super admin: demo@tradingplatform.com';
    RAISE NOTICE '🔑 Use the same password as the demo user';
END $$;

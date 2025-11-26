-- =====================================================
-- NOTIFICATIONS TABLE - Sistema de Notificações
-- Execute this in Supabase SQL Editor
-- =====================================================

-- Drop type if exists for clean setup
DROP TYPE IF EXISTS notificationtype CASCADE;
DROP TYPE IF EXISTS notificationcategory CASCADE;

-- Create ENUM types for notifications
CREATE TYPE notificationtype AS ENUM ('success', 'warning', 'error', 'info');
CREATE TYPE notificationcategory AS ENUM ('order', 'position', 'system', 'market', 'bot', 'price_alert');

-- =====================================================
-- NOTIFICATIONS TABLE
-- =====================================================
CREATE TABLE IF NOT EXISTS notifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Notification content
    type notificationtype NOT NULL DEFAULT 'info',
    category notificationcategory NOT NULL DEFAULT 'system',
    title VARCHAR(255) NOT NULL,
    message TEXT NOT NULL,

    -- Status
    read BOOLEAN NOT NULL DEFAULT false,

    -- Optional action URL (e.g., link to order, position, etc.)
    action_url VARCHAR(512),

    -- Optional metadata (JSON for additional data like order_id, position_id, etc.)
    metadata JSONB,

    -- User relationship (required - each notification belongs to a user)
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,

    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- =====================================================
-- INDEXES FOR PERFORMANCE
-- =====================================================

-- Index for user_id (most common query - get notifications for a user)
CREATE INDEX IF NOT EXISTS ix_notifications_user_id ON notifications(user_id);

-- Index for read status (filter unread)
CREATE INDEX IF NOT EXISTS ix_notifications_read ON notifications(read);

-- Index for category (filter by type)
CREATE INDEX IF NOT EXISTS ix_notifications_category ON notifications(category);

-- Index for created_at (ordering by date)
CREATE INDEX IF NOT EXISTS ix_notifications_created_at ON notifications(created_at DESC);

-- Composite index for common query pattern (user's unread notifications)
CREATE INDEX IF NOT EXISTS ix_notifications_user_unread ON notifications(user_id, read) WHERE read = false;

-- =====================================================
-- ROW LEVEL SECURITY (RLS)
-- =====================================================

-- Enable RLS
ALTER TABLE notifications ENABLE ROW LEVEL SECURITY;

-- Policy: Users can only see their own notifications
CREATE POLICY notifications_select_policy ON notifications
    FOR SELECT
    USING (user_id = auth.uid());

-- Policy: Users can only update their own notifications (mark as read)
CREATE POLICY notifications_update_policy ON notifications
    FOR UPDATE
    USING (user_id = auth.uid());

-- Policy: Users can only delete their own notifications
CREATE POLICY notifications_delete_policy ON notifications
    FOR DELETE
    USING (user_id = auth.uid());

-- Policy: System can insert notifications for any user (for triggers/functions)
CREATE POLICY notifications_insert_policy ON notifications
    FOR INSERT
    WITH CHECK (true);

-- =====================================================
-- TRIGGER: Auto-update updated_at
-- =====================================================
CREATE OR REPLACE FUNCTION update_notifications_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_notifications_updated_at ON notifications;
CREATE TRIGGER trigger_notifications_updated_at
    BEFORE UPDATE ON notifications
    FOR EACH ROW
    EXECUTE FUNCTION update_notifications_updated_at();

-- =====================================================
-- SUCCESS MESSAGE
-- =====================================================
SELECT 'Notifications Table Created Successfully!' as message,
       'Table notifications with indexes and RLS ready!' as details;

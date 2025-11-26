-- Create or update demo admin user with correct password
DO $$
DECLARE
    demo_user_id UUID;
    demo_password_hash TEXT := '$2b$12$bZ6lTxpo35fpw3.6gywUFON5YSKZUH1Xz1t.dP07IfJutm8M1rfPG'; -- demo123
BEGIN
    -- Check if demo user exists
    SELECT id INTO demo_user_id FROM users WHERE email = 'demo@tradingplatform.com';

    IF demo_user_id IS NULL THEN
        -- Create new demo user
        INSERT INTO users (email, name, password_hash, is_active, is_verified, is_admin, totp_enabled)
        VALUES (
            'demo@tradingplatform.com',
            'Demo Admin',
            demo_password_hash,
            true,
            true,
            true,
            false
        )
        RETURNING id INTO demo_user_id;

        RAISE NOTICE 'Created new demo user with ID: %', demo_user_id;
    ELSE
        -- Update existing demo user
        UPDATE users
        SET
            password_hash = demo_password_hash,
            is_active = true,
            is_verified = true,
            is_admin = true,
            totp_enabled = false
        WHERE id = demo_user_id;

        RAISE NOTICE 'Updated existing demo user with ID: %', demo_user_id;
    END IF;

    -- Create or update admin entry
    INSERT INTO admins (user_id, role, permissions, is_active)
    VALUES (
        demo_user_id,
        'super_admin',
        '{"bots": true, "users": true, "webhooks": true, "reports": true, "admins": true}'::jsonb,
        true
    )
    ON CONFLICT (user_id) DO UPDATE
    SET
        role = 'super_admin',
        permissions = '{"bots": true, "users": true, "webhooks": true, "reports": true, "admins": true}'::jsonb,
        is_active = true;

    RAISE NOTICE '✅ Admin user configured successfully!';
    RAISE NOTICE '📧 Email: demo@tradingplatform.com';
    RAISE NOTICE '🔑 Password: demo123';
END $$;

-- Verify the user was created
SELECT
    u.id,
    u.email,
    u.name,
    u.is_admin,
    u.is_active,
    a.role
FROM users u
LEFT JOIN admins a ON u.id = a.user_id
WHERE u.email = 'demo@tradingplatform.com';

-- Criar usuário ADMIN para acesso ao sistema
-- Execute este SQL no Supabase SQL Editor

DO $$
DECLARE
    admin_user_id UUID;
    admin_password_hash TEXT := '$2b$12$83cWMKvOiDycbMoxLF0dDuY5ccEgE07TBmvt8cE7uE9Y44XTgxaNS'; -- admin123
BEGIN
    -- Verificar se usuário já existe
    SELECT id INTO admin_user_id FROM users WHERE email = 'admin@globalautomation.com';

    IF admin_user_id IS NULL THEN
        -- Criar novo usuário admin
        INSERT INTO users (email, name, password_hash, is_active, is_verified, is_admin, totp_enabled)
        VALUES (
            'admin@globalautomation.com',
            'Global Automation Admin',
            admin_password_hash,
            true,
            true,
            true,
            false
        )
        RETURNING id INTO admin_user_id;

        RAISE NOTICE 'Criado novo usuário admin com ID: %', admin_user_id;
    ELSE
        -- Atualizar usuário existente
        UPDATE users
        SET
            password_hash = admin_password_hash,
            is_active = true,
            is_verified = true,
            is_admin = true,
            totp_enabled = false
        WHERE id = admin_user_id;

        RAISE NOTICE 'Atualizado usuário admin com ID: %', admin_user_id;
    END IF;

    -- Criar ou atualizar entrada na tabela admins
    INSERT INTO admins (user_id, role, permissions, is_active)
    VALUES (
        admin_user_id,
        'super_admin',
        '{"bots": true, "users": true, "webhooks": true, "reports": true, "admins": true}'::jsonb,
        true
    )
    ON CONFLICT (user_id) DO UPDATE
    SET
        role = 'super_admin',
        permissions = '{"bots": true, "users": true, "webhooks": true, "reports": true, "admins": true}'::jsonb,
        is_active = true;

    RAISE NOTICE '✅ Usuário admin configurado com sucesso!';
    RAISE NOTICE '📧 Email: admin@globalautomation.com';
    RAISE NOTICE '🔑 Password: admin123';
END $$;

-- Verificar se o usuário foi criado
SELECT
    u.id,
    u.email,
    u.name,
    u.is_admin,
    u.is_active,
    a.role,
    a.permissions
FROM users u
LEFT JOIN admins a ON u.id = a.user_id
WHERE u.email = 'admin@globalautomation.com';

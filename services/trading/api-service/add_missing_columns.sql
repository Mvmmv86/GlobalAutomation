-- Script para adicionar colunas faltantes na tabela users
-- Execute este script no painel SQL do Supabase

-- Adicionar colunas faltantes na tabela users
ALTER TABLE users 
ADD COLUMN IF NOT EXISTS failed_login_attempts INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS locked_until TIMESTAMP WITH TIME ZONE,
ADD COLUMN IF NOT EXISTS reset_token VARCHAR(255),
ADD COLUMN IF NOT EXISTS reset_token_expires TIMESTAMP WITH TIME ZONE,
ADD COLUMN IF NOT EXISTS verification_token VARCHAR(255);

-- Adicionar comentários para documentar as colunas
COMMENT ON COLUMN users.failed_login_attempts IS 'Número de tentativas de login falhadas consecutivas';
COMMENT ON COLUMN users.locked_until IS 'Data/hora até quando a conta está bloqueada';
COMMENT ON COLUMN users.reset_token IS 'Token para reset de senha';
COMMENT ON COLUMN users.reset_token_expires IS 'Data/hora de expiração do token de reset';
COMMENT ON COLUMN users.verification_token IS 'Token para verificação de email';

-- Opcional: Desabilitar RLS temporariamente para testes (CUIDADO: apenas para desenvolvimento)
-- IMPORTANTE: Reative RLS em produção
ALTER TABLE users DISABLE ROW LEVEL SECURITY;

-- Verificar a estrutura da tabela após as alterações
SELECT 
    column_name,
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns 
WHERE table_name = 'users' 
ORDER BY ordinal_position;
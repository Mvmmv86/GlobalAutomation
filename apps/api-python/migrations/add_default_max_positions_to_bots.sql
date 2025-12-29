-- Migration: Add default_max_positions to bots table
-- Description: Permite que admins definam um max_positions padrão para o bot
-- Date: 2025-12-24

-- Adiciona coluna default_max_positions à tabela bots
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'bots' AND column_name = 'default_max_positions'
    ) THEN
        ALTER TABLE bots ADD COLUMN default_max_positions INTEGER DEFAULT 3;

        -- Add constraint para garantir valores válidos (1-20)
        ALTER TABLE bots ADD CONSTRAINT check_default_max_positions
            CHECK (default_max_positions >= 1 AND default_max_positions <= 20);

        RAISE NOTICE 'Coluna default_max_positions adicionada à tabela bots';
    ELSE
        RAISE NOTICE 'Coluna default_max_positions já existe na tabela bots';
    END IF;
END $$;

-- Adiciona comentário explicativo
COMMENT ON COLUMN bots.default_max_positions IS 'Número máximo de posições simultâneas sugerido pelo admin. Clientes podem sobrescrever na subscription (max_concurrent_positions).';

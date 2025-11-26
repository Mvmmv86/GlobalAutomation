#!/usr/bin/env python3
"""
Criar tabelas de ordens usando o connection manager que já funciona
"""

import asyncio
from infrastructure.database.connection_transaction_mode import transaction_db


async def create_orders_tables():
    """Criar tabelas usando connection manager existente"""

    print("🚀 Criando tabelas de ordens...")

    try:
        # Conectar usando o manager que já funciona
        await transaction_db.connect()
        print("✅ Conectado ao banco!")

        # SQL simplificado para criar tabelas
        sql = """
        -- Tabela de ordens
        CREATE TABLE IF NOT EXISTS trading_orders (
            id SERIAL PRIMARY KEY,
            webhook_delivery_id INTEGER,
            symbol VARCHAR(20) NOT NULL,
            side VARCHAR(10) NOT NULL,
            order_type VARCHAR(20) NOT NULL,
            quantity DECIMAL(18, 8) NOT NULL,
            price DECIMAL(18, 8),
            status VARCHAR(50) DEFAULT 'pending',
            exchange VARCHAR(50) DEFAULT 'binance',
            exchange_order_id VARCHAR(100),
            filled_quantity DECIMAL(18, 8) DEFAULT 0,
            average_price DECIMAL(18, 8),
            error_message TEXT,
            raw_response JSONB,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        -- Tabela de contas
        CREATE TABLE IF NOT EXISTS trading_accounts (
            id SERIAL PRIMARY KEY,
            exchange VARCHAR(50) NOT NULL,
            account_name VARCHAR(100) NOT NULL,
            testnet BOOLEAN DEFAULT true,
            is_active BOOLEAN DEFAULT true,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        -- Índices
        CREATE INDEX IF NOT EXISTS idx_trading_orders_status ON trading_orders(status);
        CREATE INDEX IF NOT EXISTS idx_trading_orders_symbol ON trading_orders(symbol);
        """

        # Executar SQL
        print("📝 Criando tabelas...")
        await transaction_db.execute(sql)

        # Verificar tabelas criadas
        tables = await transaction_db.fetch(
            """
            SELECT tablename 
            FROM pg_tables 
            WHERE schemaname = 'public' 
            AND tablename LIKE 'trading_%'
            ORDER BY tablename
        """
        )

        print("\n✅ Tabelas criadas:")
        for table in tables:
            print(f"   • {table['tablename']}")

        # Inserir conta demo da Binance
        existing_accounts = await transaction_db.fetchval(
            "SELECT COUNT(*) FROM trading_accounts WHERE exchange = 'binance'"
        )

        if existing_accounts == 0:
            await transaction_db.execute(
                """
                INSERT INTO trading_accounts (exchange, account_name, testnet, is_active)
                VALUES ('binance', 'Demo Account', true, true)
            """
            )
            print("   • Conta demo da Binance criada")

        return True

    except Exception as e:
        print(f"❌ Erro: {e}")
        return False

    finally:
        await transaction_db.disconnect()


if __name__ == "__main__":
    success = asyncio.run(create_orders_tables())

    if success:
        print("\n🎉 TABELAS CRIADAS COM SUCESSO!")
        print("Próximo: Implementar Binance connector")
    else:
        print("\n⚠️ Falha ao criar tabelas")

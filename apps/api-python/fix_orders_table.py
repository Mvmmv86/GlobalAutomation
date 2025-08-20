#!/usr/bin/env python3
"""
Corrigir tabela trading_orders - adicionar coluna updated_at
"""

import asyncio
from infrastructure.database.connection_transaction_mode import transaction_db


async def fix_orders_table():
    """Adicionar coluna updated_at na tabela"""

    try:
        await transaction_db.connect()
        print("✅ Conectado ao banco")

        # Adicionar coluna updated_at
        await transaction_db.execute(
            """
            ALTER TABLE trading_orders 
            ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        """
        )

        print("✅ Coluna updated_at adicionada")

        # Verificar estrutura da tabela
        columns = await transaction_db.fetch(
            """
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'trading_orders'
            ORDER BY ordinal_position
        """
        )

        print("\n📊 Estrutura da tabela trading_orders:")
        for col in columns:
            print(f"   • {col['column_name']}: {col['data_type']}")

        return True

    except Exception as e:
        print(f"❌ Erro: {e}")
        return False

    finally:
        await transaction_db.disconnect()


if __name__ == "__main__":
    success = asyncio.run(fix_orders_table())

    if success:
        print("\n✅ Tabela corrigida! Pode rodar o teste novamente.")
    else:
        print("\n⚠️ Erro ao corrigir tabela")

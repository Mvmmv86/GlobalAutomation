#!/usr/bin/env python3
"""
Script para atualizar o constraint de indicator_type no banco de dados.

Este script atualiza a constraint check_indicator_type na tabela strategy_indicators
para incluir todos os novos tipos de indicadores implementados.

Novos indicadores adicionados:
- stochastic
- stochastic_rsi
- supertrend
- adx
- vwap
- ichimoku
- obv
- ema_cross

Para executar:
    python scripts/update_indicator_constraint.py
"""

import asyncio
import os
from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv()


async def update_constraint():
    """Atualiza o constraint de indicator_type no banco de dados"""
    import asyncpg

    # URL do banco (Supabase)
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("ERROR: DATABASE_URL não encontrada")
        return False

    # Conectar ao banco
    print("Conectando ao banco de dados...")
    try:
        conn = await asyncpg.connect(database_url)
    except Exception as e:
        print(f"ERROR: Falha ao conectar: {e}")
        return False

    try:
        # Lista completa de todos os indicator types
        all_indicator_types = [
            # Indicadores originais
            'nadaraya_watson', 'tpo', 'rsi', 'macd', 'ema', 'ema_cross',
            'bollinger', 'atr', 'volume_profile',
            # Novos indicadores - Fase 1
            'stochastic', 'stochastic_rsi', 'supertrend',
            # Novos indicadores - Fase 2
            'adx', 'vwap', 'ichimoku', 'obv'
        ]

        # Formatar lista para SQL
        types_str = ", ".join([f"'{t}'" for t in all_indicator_types])

        # 1. Verificar se a constraint existe
        print("Verificando constraints existentes...")
        check_query = """
            SELECT constraint_name
            FROM information_schema.table_constraints
            WHERE table_name = 'strategy_indicators'
            AND constraint_type = 'CHECK'
        """
        existing = await conn.fetch(check_query)
        print(f"Constraints encontradas: {[r['constraint_name'] for r in existing]}")

        # 2. Remover constraint antiga (se existir)
        print("Removendo constraint antiga...")
        try:
            await conn.execute("""
                ALTER TABLE strategy_indicators
                DROP CONSTRAINT IF EXISTS check_indicator_type
            """)
            print("✓ Constraint antiga removida")
        except Exception as e:
            print(f"⚠ Aviso ao remover constraint: {e}")

        # 3. Adicionar nova constraint
        print("Adicionando nova constraint...")
        add_query = f"""
            ALTER TABLE strategy_indicators
            ADD CONSTRAINT check_indicator_type
            CHECK (indicator_type IN ({types_str}))
        """
        await conn.execute(add_query)
        print("✓ Nova constraint adicionada")

        # 4. Verificar constraint atualizada
        print("\nVerificando constraint atualizada...")
        verify_query = """
            SELECT pg_get_constraintdef(c.oid)
            FROM pg_constraint c
            JOIN pg_class t ON c.conrelid = t.oid
            WHERE t.relname = 'strategy_indicators'
            AND c.conname = 'check_indicator_type'
        """
        result = await conn.fetch(verify_query)
        if result:
            print(f"✓ Constraint verificada: {result[0][0]}")
        else:
            print("⚠ Constraint não encontrada após atualização")

        print("\n" + "=" * 60)
        print("CONSTRAINT ATUALIZADA COM SUCESSO!")
        print("=" * 60)
        print("\nIndicadores suportados:")
        for i, t in enumerate(all_indicator_types, 1):
            print(f"  {i:2}. {t}")

        return True

    except Exception as e:
        print(f"ERROR: {e}")
        return False
    finally:
        await conn.close()


if __name__ == "__main__":
    success = asyncio.run(update_constraint())
    exit(0 if success else 1)

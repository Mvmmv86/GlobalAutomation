#!/usr/bin/env python3
"""
Script para criar a tabela de candles no banco de dados
"""

import asyncio
import sys
from pathlib import Path

# Adicionar o diretório raiz ao path
sys.path.append(str(Path(__file__).parent))

from sqlalchemy import text
from infrastructure.database.connection import database_manager
from infrastructure.database.models.candle import Candle
from infrastructure.database.models.base import Base


async def create_candles_table():
    """Cria a tabela de candles no banco de dados"""
    try:
        print("🔄 Conectando ao banco de dados...")

        # Conectar ao database manager
        await database_manager.connect()

        # Criar todas as tabelas definidas nos modelos
        async with database_manager.engine.begin() as conn:
            print("📊 Criando tabela 'candles'...")

            # Criar a tabela usando o metadata do SQLAlchemy
            await conn.run_sync(Base.metadata.create_all)

            print("✅ Tabela 'candles' criada com sucesso!")

            # Verificar se a tabela foi criada
            result = await conn.execute(
                text("SELECT COUNT(*) FROM information_schema.tables WHERE table_name = 'candles'")
            )
            count = result.scalar()

            if count > 0:
                print("✅ Verificação: Tabela 'candles' existe no banco!")

                # Contar registros existentes
                result = await conn.execute(text("SELECT COUNT(*) FROM candles"))
                record_count = result.scalar()
                print(f"📊 Total de candles no cache: {record_count}")
            else:
                print("⚠️ Aviso: Tabela 'candles' não foi encontrada após criação")

    except Exception as e:
        print(f"❌ Erro ao criar tabela: {e}")
        return False

    return True


async def main():
    """Função principal"""
    print("=" * 50)
    print("🚀 CRIAÇÃO DA TABELA DE CANDLES")
    print("=" * 50)

    success = await create_candles_table()

    if success:
        print("\n✅ Processo concluído com sucesso!")
        print("📌 A tabela está pronta para armazenar cache de candles")
        print("💡 O cache irá melhorar a performance dos gráficos")
    else:
        print("\n❌ Falha ao criar tabela")
        print("📌 Verifique as configurações do banco de dados")

    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(main())
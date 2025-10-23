"""
Script para deletar contas Exchange antigas que foram criptografadas com chave diferente
"""
import asyncio
import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text

# Database URL de produção
DATABASE_URL = "postgresql+asyncpg://postgres.zmdqmrugotfftxvrwdsd:Wzg0kBvtrSbclQ9V@aws-1-us-east-2.pooler.supabase.com:5432/postgres"

async def delete_exchange_accounts():
    """Deleta todas as contas Exchange"""

    # Criar engine
    engine = create_async_engine(DATABASE_URL, echo=True)

    # Criar session factory
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    async with async_session() as session:
        try:
            # Listar contas antes de deletar
            print("\n📋 Contas Exchange existentes:")
            result = await session.execute(
                text("SELECT id, name, exchange, is_main, created_at FROM exchange_accounts ORDER BY created_at DESC")
            )
            accounts = result.fetchall()

            if not accounts:
                print("✅ Nenhuma conta encontrada no banco.")
                return

            print(f"\n🔍 Encontradas {len(accounts)} contas:")
            for account in accounts:
                print(f"  - {account.name} ({account.exchange}) - ID: {account.id}")

            # Deletar todas as contas automaticamente
            print("\n⚠️  ATENÇÃO: Deletando TODAS as contas Exchange...")

            # Deletar todas as contas
            print("\n🗑️  Deletando contas...")
            await session.execute(text("DELETE FROM exchange_accounts"))
            await session.commit()

            print("✅ Todas as contas Exchange foram deletadas com sucesso!")
            print("\n📝 Próximos passos:")
            print("1. Aguarde o build do Digital Ocean terminar")
            print("2. Acesse a produção e crie uma nova conta Exchange")
            print("3. Verifique se a sincronização funciona")

        except Exception as e:
            print(f"❌ Erro ao deletar contas: {e}")
            await session.rollback()
        finally:
            await engine.dispose()

if __name__ == "__main__":
    asyncio.run(delete_exchange_accounts())

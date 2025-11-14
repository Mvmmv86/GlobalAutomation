import asyncio
import asyncpg

async def test_connection():
    try:
        print("Testando conexão com Supabase...")
        # Tentando a URL completa
        # Removendo o +asyncpg para o teste direto
        url = "postgresql://postgres.zmdqmrugotfftxvrwdsd:Wzg0kBvtrSbclQ9V@aws-1-us-east-2.pooler.supabase.com:6543/postgres"

        print(f"URL: {url[:50]}...")

        conn = await asyncpg.connect(
            url,
            timeout=10,
            command_timeout=10
        )

        print("✅ Conexão estabelecida com sucesso!")

        # Testar uma query simples
        version = await conn.fetchval('SELECT version()')
        print(f"Versão do PostgreSQL: {version}")

        await conn.close()
        print("Conexão fechada.")

    except Exception as e:
        print(f"❌ Erro ao conectar: {e}")
        print(f"Tipo do erro: {type(e).__name__}")

if __name__ == "__main__":
    asyncio.run(test_connection())
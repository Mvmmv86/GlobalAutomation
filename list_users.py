import asyncio
import asyncpg
import json

async def list_users():
    try:
        print("🔍 Conectando ao Supabase para listar usuários...")

        # URL de conexão com o Supabase
        url = "postgresql://postgres.zmdqmrugotfftxvrwdsd:Wzg0kBvtrSbclQ9V@aws-1-us-east-2.pooler.supabase.com:6543/postgres"

        conn = await asyncpg.connect(url, timeout=10)

        # Primeiro descobrir as colunas da tabela
        columns_query = """
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_name = 'users'
            ORDER BY ordinal_position
        """

        columns = await conn.fetch(columns_query)
        print("\n📋 Estrutura da tabela users:")
        for col in columns:
            print(f"   - {col['column_name']}: {col['data_type']}")

        # Buscar usuários na tabela users
        query = """
            SELECT *
            FROM users
            ORDER BY created_at DESC
            LIMIT 10
        """

        users = await conn.fetch(query)

        if users:
            print("\n✅ Usuários encontrados no banco:\n")
            print("-" * 80)
            for user in users:
                print(f"📧 Email: {user.get('email', 'N/A')}")
                print(f"   Nome: {user.get('name', 'N/A')}")
                print(f"   ID: {user.get('id', 'N/A')}")
                print(f"   Ativo: {'Sim' if user.get('is_active', False) else 'Não'}")
                print(f"   Criado em: {user.get('created_at', 'N/A')}")
                print("-" * 80)
        else:
            print("❌ Nenhum usuário ativo encontrado no banco")

        # Verificar se existe algum usuário de teste
        test_users = await conn.fetch("""
            SELECT email, name FROM users
            WHERE email LIKE '%test%' OR email LIKE '%demo%'
            LIMIT 5
        """)

        if test_users:
            print("\n🧪 Usuários de teste/demo encontrados:")
            for user in test_users:
                print(f"   - {user['email']} ({user['name']})")

        await conn.close()

    except Exception as e:
        print(f"❌ Erro ao buscar usuários: {e}")
        print(f"   Tipo: {type(e).__name__}")

if __name__ == "__main__":
    asyncio.run(list_users())
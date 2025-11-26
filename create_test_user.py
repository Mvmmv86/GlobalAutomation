import asyncio
import asyncpg
from passlib.context import CryptContext
from datetime import datetime
import uuid

# Configurar o contexto de criptografia (mesmo que o backend usa)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

async def create_test_user():
    try:
        print("🔐 Criando usuário de teste...")

        # URL de conexão
        url = "postgresql://postgres.zmdqmrugotfftxvrwdsd:Wzg0kBvtrSbclQ9V@aws-1-us-east-2.pooler.supabase.com:6543/postgres"

        # Desabilitar statement cache por causa do pgbouncer
        conn = await asyncpg.connect(
            url,
            timeout=10,
            statement_cache_size=0  # Necessário para pgbouncer
        )

        # Dados do usuário de teste
        test_email = "test@globalautomation.com"
        test_password = "test123456"  # Senha em texto claro
        test_name = "Usuário de Teste"

        # Criptografar a senha
        hashed_password = pwd_context.hash(test_password)

        # Verificar se o usuário já existe
        existing = await conn.fetchrow(
            "SELECT id, email FROM users WHERE email = $1",
            test_email
        )

        if existing:
            print(f"⚠️ Usuário {test_email} já existe!")
            print("🔄 Atualizando a senha...")

            # Atualizar a senha do usuário existente
            await conn.execute(
                """
                UPDATE users
                SET password_hash = $1,
                    updated_at = $2
                WHERE email = $3
                """,
                hashed_password,
                datetime.utcnow(),
                test_email
            )
            print("✅ Senha atualizada com sucesso!")
        else:
            # Criar novo usuário
            user_id = str(uuid.uuid4())

            await conn.execute(
                """
                INSERT INTO users (id, email, name, password_hash, is_active, created_at, updated_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                """,
                user_id,
                test_email,
                test_name,
                hashed_password,
                True,
                datetime.utcnow(),
                datetime.utcnow()
            )
            print("✅ Usuário criado com sucesso!")

        print("\n" + "="*60)
        print("🎉 CREDENCIAIS DE ACESSO:")
        print("="*60)
        print(f"📧 Email: {test_email}")
        print(f"🔑 Senha: {test_password}")
        print("="*60)
        print("\n📝 Use essas credenciais para fazer login em http://localhost:3000")

        await conn.close()

    except Exception as e:
        print(f"❌ Erro: {e}")
        print(f"   Tipo: {type(e).__name__}")

if __name__ == "__main__":
    asyncio.run(create_test_user())
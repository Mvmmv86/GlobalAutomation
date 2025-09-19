#!/usr/bin/env python3
"""Script para testar o schema da tabela users após adicionar colunas"""

import asyncio
from infrastructure.database.connection import database_manager
from sqlalchemy import text


async def test_user_schema():
    """Testa se todas as colunas do modelo User existem na tabela"""

    print("🔍 Conectando ao Supabase...")
    await database_manager.connect()

    try:
        session = database_manager.get_session()
        async with session:
            # Testar se todas as colunas existem
            print("\n📋 Verificando colunas da tabela users...")

            query = text(
                """
                SELECT column_name, data_type, is_nullable, column_default
                FROM information_schema.columns 
                WHERE table_name = 'users' 
                ORDER BY ordinal_position
            """
            )

            result = await session.execute(query)
            columns = result.fetchall()

            print(f"\n✅ Encontradas {len(columns)} colunas:")
            for col in columns:
                print(
                    f"   - {col.column_name} ({col.data_type}) {'NULL' if col.is_nullable == 'YES' else 'NOT NULL'}"
                )

            # Verificar se todas as colunas necessárias existem
            expected_columns = {
                "id",
                "email",
                "name",
                "password_hash",
                "is_active",
                "is_verified",
                "totp_secret",
                "totp_enabled",
                "last_login_at",
                "created_at",
                "updated_at",
                "failed_login_attempts",
                "locked_until",
                "reset_token",
                "reset_token_expires",
                "verification_token",
            }

            existing_columns = {col.column_name for col in columns}
            missing_columns = expected_columns - existing_columns
            extra_columns = existing_columns - expected_columns

            if missing_columns:
                print(f"\n❌ Colunas faltantes: {missing_columns}")
            else:
                print("\n✅ Todas as colunas necessárias estão presentes!")

            if extra_columns:
                print(f"\n📄 Colunas extras: {extra_columns}")

            # Testar uma query simples que usa as colunas do modelo
            print("\n🧪 Testando query do modelo User...")
            test_query = text(
                """
                SELECT email, name, password_hash, is_active, is_verified, 
                       totp_secret, totp_enabled, last_login_at, 
                       failed_login_attempts, locked_until, reset_token, 
                       reset_token_expires, verification_token,
                       id, created_at, updated_at
                FROM users 
                WHERE email = :email
                LIMIT 1
            """
            )

            result = await session.execute(
                test_query, {"email": "teste_nao_existe@exemplo.com"}
            )
            print("✅ Query do modelo executada com sucesso!")

            # Verificar RLS status
            rls_query = text(
                """
                SELECT schemaname, tablename, rowsecurity, policies
                FROM pg_tables 
                LEFT JOIN (
                    SELECT schemaname, tablename, 
                           COUNT(*) as policies,
                           bool_or(rowsecurity) as rowsecurity
                    FROM pg_policies 
                    GROUP BY schemaname, tablename
                ) pol USING (schemaname, tablename)
                WHERE tablename = 'users'
            """
            )

            result = await session.execute(rls_query)
            rls_info = result.fetchone()
            if rls_info:
                print("\n🔒 RLS Status:")
                print(
                    f"   - Row Security: {'Enabled' if rls_info.rowsecurity else 'Disabled'}"
                )
                print(f"   - Policies: {rls_info.policies or 0}")

    except Exception as e:
        print(f"\n❌ Erro: {e}")
        return False

    finally:
        await database_manager.disconnect()
        print("\n🔌 Conexão fechada.")

    return True


if __name__ == "__main__":
    print("🚀 Testando schema da tabela users...")
    success = asyncio.run(test_user_schema())

    if success:
        print("\n🎉 Schema verificado com sucesso!")
        print("\n📋 Próximos passos:")
        print("   1. Execute o script add_missing_columns.sql no Supabase")
        print("   2. Execute este script novamente para verificar")
        print("   3. Teste o registro/login do usuário")
    else:
        print("\n💥 Falha na verificação do schema.")

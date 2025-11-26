#!/usr/bin/env python3
"""
Verificar configurações e funções do Supabase que podem estar causando o problema
"""

import asyncio
from infrastructure.database.connection_transaction_mode import transaction_db


async def check_supabase_config():
    """Verificar configurações do Supabase"""

    try:
        await transaction_db.connect()
        print("✅ Conectado ao Supabase")

        # 1. Verificar tabelas existentes
        print("\n📊 TABELAS NO BANCO:")
        tables = await transaction_db.fetch(
            """
            SELECT table_name, table_type 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            ORDER BY table_name
        """
        )

        for table in tables:
            print(f"   • {table['table_name']} ({table['table_type']})")

        # 2. Verificar funções/triggers na tabela users
        print("\n🔧 TRIGGERS NA TABELA USERS:")
        triggers = await transaction_db.fetch(
            """
            SELECT trigger_name, event_manipulation, action_statement
            FROM information_schema.triggers 
            WHERE event_object_table = 'users'
        """
        )

        if triggers:
            for trigger in triggers:
                print(
                    f"   • {trigger['trigger_name']}: {trigger['event_manipulation']}"
                )
                print(f"     Action: {trigger['action_statement'][:100]}...")
        else:
            print("   Nenhum trigger encontrado")

        # 3. Verificar stored procedures/functions
        print("\n⚙️ FUNÇÕES PERSONALIZADAS:")
        functions = await transaction_db.fetch(
            """
            SELECT routine_name, routine_type, routine_definition
            FROM information_schema.routines 
            WHERE routine_schema = 'public'
            AND routine_type = 'FUNCTION'
        """
        )

        if functions:
            for func in functions:
                print(f"   • {func['routine_name']} ({func['routine_type']})")
                if func["routine_definition"]:
                    print(f"     Def: {func['routine_definition'][:100]}...")
        else:
            print("   Nenhuma função personalizada encontrada")

        # 4. Verificar RLS (Row Level Security)
        print("\n🔒 ROW LEVEL SECURITY:")
        rls = await transaction_db.fetch(
            """
            SELECT schemaname, tablename, rowsecurity
            FROM pg_tables 
            WHERE schemaname = 'public'
            AND tablename = 'users'
        """
        )

        if rls:
            for row in rls:
                print(f"   • {row['tablename']}: RLS = {row['rowsecurity']}")

        # 5. Verificar políticas RLS
        print("\n📋 POLÍTICAS RLS:")
        policies = await transaction_db.fetch(
            """
            SELECT pol.polname, pol.polcmd, pol.polpermissive, pol.polroles, pol.polqual
            FROM pg_policy pol
            JOIN pg_class pc ON pol.polrelid = pc.oid
            JOIN pg_namespace pn ON pc.relnamespace = pn.oid
            WHERE pn.nspname = 'public' AND pc.relname = 'users'
        """
        )

        if policies:
            for policy in policies:
                print(f"   • {policy['polname']}: {policy['polcmd']}")
        else:
            print("   Nenhuma política RLS encontrada")

        # 6. Verificar índices na tabela users
        print("\n📇 ÍNDICES NA TABELA USERS:")
        indexes = await transaction_db.fetch(
            """
            SELECT indexname, indexdef
            FROM pg_indexes 
            WHERE tablename = 'users'
            AND schemaname = 'public'
        """
        )

        for idx in indexes:
            print(f"   • {idx['indexname']}")
            print(f"     {idx['indexdef']}")

        # 7. Verificar constraints
        print("\n🔗 CONSTRAINTS NA TABELA USERS:")
        constraints = await transaction_db.fetch(
            """
            SELECT constraint_name, constraint_type
            FROM information_schema.table_constraints 
            WHERE table_name = 'users'
            AND table_schema = 'public'
        """
        )

        for constraint in constraints:
            print(
                f"   • {constraint['constraint_name']}: {constraint['constraint_type']}"
            )

        # 8. Verificar estrutura da tabela users
        print("\n🏗️ ESTRUTURA DA TABELA USERS:")
        columns = await transaction_db.fetch(
            """
            SELECT column_name, data_type, is_nullable, column_default
            FROM information_schema.columns 
            WHERE table_name = 'users'
            AND table_schema = 'public'
            ORDER BY ordinal_position
        """
        )

        for col in columns:
            nullable = "NULL" if col["is_nullable"] == "YES" else "NOT NULL"
            default = (
                f" DEFAULT {col['column_default']}" if col["column_default"] else ""
            )
            print(f"   • {col['column_name']}: {col['data_type']} {nullable}{default}")

        # 9. Testar uma query simples na tabela users
        print("\n🧪 TESTE DE QUERY SIMPLES:")
        try:
            count = await transaction_db.fetchval("SELECT COUNT(*) FROM users")
            print(f"   ✅ Total de usuários: {count}")
        except Exception as e:
            print(f"   ❌ Erro na query: {e}")

        return True

    except Exception as e:
        print(f"❌ Erro: {e}")
        return False

    finally:
        await transaction_db.disconnect()


if __name__ == "__main__":
    print("🔍 Verificando configurações do Supabase...")
    success = asyncio.run(check_supabase_config())

    if success:
        print("\n✅ Verificação concluída!")
    else:
        print("\n⚠️ Erro na verificação")

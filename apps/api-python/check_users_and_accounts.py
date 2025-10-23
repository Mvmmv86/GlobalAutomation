#!/usr/bin/env python3
"""
Script para verificar usuários e exchange accounts no banco de dados
"""
import asyncio
import sys
import os

# Adicionar o diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from infrastructure.database.connection_transaction_mode import transaction_db


async def check_database():
    """Verificar estado do banco de dados"""

    print("\n" + "="*80)
    print("🔍 DIAGNÓSTICO DO BANCO DE DADOS - PRODUÇÃO")
    print("="*80 + "\n")

    # Inicializar conexão com o banco
    await transaction_db.connect()

    try:
        # 1. Verificar usuários
        print("📊 1. VERIFICANDO USUÁRIOS:")
        print("-" * 80)
        users = await transaction_db.fetch("""
            SELECT id, email, is_admin, created_at
            FROM users
            ORDER BY created_at
        """)

        if not users:
            print("❌ PROBLEMA CRÍTICO: Nenhum usuário encontrado!")
            print("   → Backend falha ao criar conta porque não encontra user_id\n")
        else:
            print(f"✅ {len(users)} usuário(s) encontrado(s):\n")
            for i, user in enumerate(users, 1):
                print(f"   [{i}] ID: {user['id']}")
                print(f"       Email: {user['email']}")
                print(f"       Admin: {user['is_admin']}")
                print(f"       Criado em: {user['created_at']}")
                print()

        # 2. Verificar exchange accounts
        print("\n📊 2. VERIFICANDO EXCHANGE ACCOUNTS:")
        print("-" * 80)
        accounts = await transaction_db.fetch("""
            SELECT ea.id, ea.name, ea.exchange, ea.testnet, ea.is_active, ea.is_main,
                   ea.user_id, ea.created_at,
                   u.email as user_email
            FROM exchange_accounts ea
            LEFT JOIN users u ON ea.user_id = u.id
            ORDER BY ea.created_at DESC
        """)

        if not accounts:
            print("⚠️  Nenhuma exchange account encontrada")
            print("   → Normal se ainda não criou nenhuma conta\n")
        else:
            print(f"✅ {len(accounts)} conta(s) encontrada(s):\n")
            for i, acc in enumerate(accounts, 1):
                print(f"   [{i}] ID: {acc['id']}")
                print(f"       Nome: {acc['name']}")
                print(f"       Exchange: {acc['exchange']}")
                print(f"       Testnet: {acc['testnet']}")
                print(f"       Ativa: {acc['is_active']}")
                print(f"       Principal: {acc['is_main']}")
                print(f"       User: {acc['user_email']} (ID: {acc['user_id']})")
                print(f"       Criado em: {acc['created_at']}")
                print()

        # 3. Verificar balances
        print("\n📊 3. VERIFICANDO BALANCES:")
        print("-" * 80)
        balances_count = await transaction_db.fetchval("""
            SELECT COUNT(*) FROM exchange_account_balances
        """)
        print(f"   Total de registros de balance: {balances_count}")

        if balances_count > 0:
            balances_by_account = await transaction_db.fetch("""
                SELECT
                    ea.name as account_name,
                    COUNT(*) as balance_count,
                    SUM(eab.usd_value) as total_usd
                FROM exchange_account_balances eab
                JOIN exchange_accounts ea ON eab.exchange_account_id = ea.id
                GROUP BY ea.id, ea.name
            """)

            print("\n   Por conta:")
            for bal in balances_by_account:
                print(f"   - {bal['account_name']}: {bal['balance_count']} assets (${bal['total_usd']:.2f})")
        print()

        # 4. Verificar posições
        print("\n📊 4. VERIFICANDO POSITIONS:")
        print("-" * 80)
        positions = await transaction_db.fetch("""
            SELECT
                ea.name as account_name,
                p.symbol,
                p.side,
                p.size,
                p.status,
                p.unrealized_pnl
            FROM positions p
            JOIN exchange_accounts ea ON p.exchange_account_id = ea.id
            WHERE p.status = 'open'
            ORDER BY ea.name, p.symbol
        """)

        if not positions:
            print("   ℹ️  Nenhuma posição aberta\n")
        else:
            print(f"   ✅ {len(positions)} posição(ões) aberta(s):\n")
            for pos in positions:
                pnl_str = f"${pos['unrealized_pnl']:.2f}" if pos['unrealized_pnl'] else "N/A"
                print(f"   - {pos['account_name']}: {pos['symbol']} {pos['side'].upper()} x{pos['size']} (P&L: {pnl_str})")
            print()

        # 5. ANÁLISE FINAL
        print("\n" + "="*80)
        print("🎯 ANÁLISE E DIAGNÓSTICO:")
        print("="*80 + "\n")

        if not users:
            print("❌ PROBLEMA ENCONTRADO: SEM USUÁRIOS")
            print("   Solução: Criar usuário com script de criação de admin")
            print()
        elif len(users) == 1:
            print(f"✅ Usuário existente: {users[0]['email']}")
            print(f"   User ID: {users[0]['id']}")
            print("   → Backend vai usar este usuário ao criar exchange account\n")
        else:
            print(f"✅ {len(users)} usuários encontrados")
            print(f"   → Backend vai usar: {users[0]['email']} (primeiro da lista)\n")

        if not accounts:
            print("⚠️  NENHUMA EXCHANGE ACCOUNT CRIADA AINDA")
            print("   → Este é o problema que estamos tentando resolver")
            print("   → Vamos verificar os logs de erro na tentativa de criação\n")
        else:
            print(f"✅ {len(accounts)} exchange account(s) já existente(s)")
            print("   → Sistema consegue criar contas normalmente\n")

        print("\n" + "="*80)
        print("✅ DIAGNÓSTICO COMPLETO")
        print("="*80 + "\n")

    except Exception as e:
        print(f"\n❌ ERRO AO VERIFICAR BANCO: {e}")
        import traceback
        traceback.print_exc()


async def main():
    """Main function"""
    await check_database()


if __name__ == "__main__":
    asyncio.run(main())

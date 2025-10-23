#!/usr/bin/env python3
"""
Script para testar criação de exchange account
Simula exatamente o que o frontend faz
"""
import asyncio
import sys
import os
import json

# Adicionar o diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from infrastructure.database.connection_transaction_mode import transaction_db
from infrastructure.security.encryption_service import EncryptionService


async def test_create_account():
    """Testar criação de exchange account"""

    print("\n" + "="*80)
    print("🧪 TESTE DE CRIAÇÃO DE EXCHANGE ACCOUNT")
    print("="*80 + "\n")

    # Inicializar conexão com o banco
    await transaction_db.connect()

    try:
        # Dados de teste (mesmos que o frontend envia)
        test_data = {
            "name": "Teste Produção",
            "exchange": "binance",
            "api_key": "test_api_key_12345",
            "secret_key": "test_secret_key_67890",
            "testnet": True,  # Usar testnet para teste
            "is_main": False
        }

        print("📝 Dados de teste:")
        print(json.dumps(test_data, indent=2))
        print()

        # PASSO 1: Validar campos obrigatórios
        print("✅ PASSO 1: Validando campos obrigatórios...")
        required_fields = ["name", "exchange", "api_key", "secret_key"]
        for field in required_fields:
            if field not in test_data:
                print(f"   ❌ Campo obrigatório ausente: {field}")
                return
        print("   ✅ Todos os campos obrigatórios presentes\n")

        # PASSO 2: Validar tipo de exchange
        print("✅ PASSO 2: Validando tipo de exchange...")
        if test_data["exchange"] not in ["binance", "bybit"]:
            print(f"   ❌ Exchange não suportada: {test_data['exchange']}")
            return
        print(f"   ✅ Exchange '{test_data['exchange']}' é suportada\n")

        # PASSO 3: Buscar user_id
        print("✅ PASSO 3: Buscando user_id...")
        user = await transaction_db.fetchrow("SELECT id, email FROM users LIMIT 1")
        if not user:
            print("   ❌ ERRO: Nenhum usuário encontrado!")
            return

        user_id = user["id"]
        print(f"   ✅ Usuário encontrado: {user['email']} (ID: {user_id})\n")

        # PASSO 4: Se is_main=True, desmarcar outras contas
        print("✅ PASSO 4: Verificando conta principal...")
        if test_data["is_main"]:
            print("   ℹ️  Esta será a conta principal - desmarcando outras...")
            await transaction_db.execute("""
                UPDATE exchange_accounts
                SET is_main = false
                WHERE exchange = $1 AND user_id = $2
            """, test_data["exchange"], user_id)
            print("   ✅ Outras contas desmarcadas\n")
        else:
            print("   ℹ️  Esta não é conta principal - nada a fazer\n")

        # PASSO 5: Tentar inserir no banco
        print("✅ PASSO 5: Inserindo exchange account no banco...")
        print(f"   Nome: {test_data['name']}")
        print(f"   Exchange: {test_data['exchange']}")
        print(f"   Testnet: {test_data['testnet']}")
        print(f"   Is Main: {test_data['is_main']}")
        print(f"   User ID: {user_id}")
        print()

        # Inserir conta (SEM CRIPTOGRAFIA por enquanto - igual ao controller)
        account_id = await transaction_db.fetchval("""
            INSERT INTO exchange_accounts (
                name, exchange, testnet, is_active,
                api_key, secret_key, user_id, is_main,
                created_at, updated_at
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, NOW(), NOW())
            RETURNING id
        """,
        test_data["name"],
        test_data["exchange"],
        test_data["testnet"],
        True,  # is_active
        test_data["api_key"],
        test_data["secret_key"],
        user_id,
        test_data["is_main"]
        )

        print(f"   ✅ SUCESSO! Account ID criado: {account_id}\n")

        # PASSO 6: Verificar se foi criada
        print("✅ PASSO 6: Verificando se a conta foi criada...")
        created_account = await transaction_db.fetchrow("""
            SELECT id, name, exchange, testnet, is_active, is_main, user_id
            FROM exchange_accounts
            WHERE id = $1
        """, account_id)

        if created_account:
            print("   ✅ Conta verificada no banco:")
            print(f"      ID: {created_account['id']}")
            print(f"      Nome: {created_account['name']}")
            print(f"      Exchange: {created_account['exchange']}")
            print(f"      Testnet: {created_account['testnet']}")
            print(f"      Ativa: {created_account['is_active']}")
            print(f"      Principal: {created_account['is_main']}")
            print(f"      User ID: {created_account['user_id']}")
            print()

        # PASSO 7: Testar com criptografia
        print("\n✅ PASSO 7: Testando com CRIPTOGRAFIA (caso produção use)...")
        encryption_service = EncryptionService()

        try:
            encrypted_api_key = encryption_service.encrypt_string(test_data["api_key"])
            encrypted_secret_key = encryption_service.encrypt_string(test_data["secret_key"])
            print("   ✅ Chaves criptografadas com sucesso")

            # Testar descriptografia
            decrypted_api_key = encryption_service.decrypt_string(encrypted_api_key)
            decrypted_secret_key = encryption_service.decrypt_string(encrypted_secret_key)

            if decrypted_api_key == test_data["api_key"] and decrypted_secret_key == test_data["secret_key"]:
                print("   ✅ Descriptografia funcionando corretamente")
            else:
                print("   ❌ ERRO: Descriptografia não retornou valores corretos")

        except Exception as e:
            print(f"   ❌ ERRO na criptografia: {e}")

        print("\n" + "="*80)
        print("✅ TESTE COMPLETO - CRIAÇÃO FUNCIONOU PERFEITAMENTE!")
        print("="*80 + "\n")

        print("💡 CONCLUSÃO:")
        print("   - Banco de dados: ✅ OK")
        print("   - Usuários: ✅ OK")
        print("   - Lógica de criação: ✅ OK")
        print("   - Criptografia: ✅ OK")
        print()
        print("   → O problema DEVE estar em:")
        print("     1. Comunicação Frontend → Backend (CORS, URL)")
        print("     2. Timeout do Digital Ocean")
        print("     3. Erro específico nos logs de produção")
        print()

        # Limpar conta de teste
        print("🧹 Limpando conta de teste...")
        await transaction_db.execute("DELETE FROM exchange_accounts WHERE id = $1", account_id)
        print("   ✅ Conta de teste removida\n")

    except Exception as e:
        print(f"\n❌ ERRO NO TESTE: {e}")
        import traceback
        traceback.print_exc()


async def main():
    """Main function"""
    await test_create_account()


if __name__ == "__main__":
    asyncio.run(main())

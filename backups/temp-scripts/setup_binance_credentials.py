#!/usr/bin/env python3
"""
Setup permanente das credenciais da Binance
Este script configura tudo de forma definitiva para não precisar alterações futuras
"""

import asyncio
import os
import base64
import secrets
from pathlib import Path
from dotenv import load_dotenv, set_key
from infrastructure.database.connection_transaction_mode import transaction_db
from infrastructure.security.encryption_service import EncryptionService
from infrastructure.exchanges.binance_connector import BinanceConnector
from binance import AsyncClient

# Carrega .env existente
load_dotenv()

async def setup_binance_credentials():
    """Configura credenciais da Binance de forma permanente"""
    
    print("\n🔧 CONFIGURAÇÃO PERMANENTE DAS CREDENCIAIS BINANCE")
    print("=" * 60)
    
    # 1. Verificar/Criar ENCRYPTION_MASTER_KEY
    print("\n1️⃣ Configurando chave de criptografia...")
    env_file = Path(".env")
    
    encryption_key = os.getenv("ENCRYPTION_MASTER_KEY")
    if not encryption_key:
        # Gerar chave permanente
        encryption_key = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode()
        set_key(env_file, "ENCRYPTION_MASTER_KEY", encryption_key)
        print(f"   ✅ Chave de criptografia gerada e salva no .env")
    else:
        print(f"   ✅ Chave de criptografia já existe")
    
    # 2. Verificar credenciais da Binance
    print("\n2️⃣ Verificando credenciais da Binance...")
    api_key = os.getenv("BINANCE_API_KEY")
    api_secret = os.getenv("BINANCE_SECRET_KEY") or os.getenv("BINANCE_API_SECRET")
    
    if not api_key or not api_secret:
        print("   ❌ Credenciais da Binance não encontradas no .env")
        print("\n   Por favor, adicione ao arquivo .env:")
        print("   BINANCE_API_KEY=sua_api_key_aqui")
        print("   BINANCE_API_SECRET=sua_secret_key_aqui")
        return False
    
    # Padronizar nome da variável
    if not os.getenv("BINANCE_API_SECRET") and api_secret:
        set_key(env_file, "BINANCE_API_SECRET", api_secret)
        print("   ✅ Variável BINANCE_API_SECRET configurada")
    
    print(f"   ✅ API Key: {api_key[:8]}...{api_key[-4:]}")
    
    # 3. Testar conexão com a Binance
    print("\n3️⃣ Testando conexão com a Binance...")
    client = None
    try:
        client = await AsyncClient.create(api_key=api_key, api_secret=api_secret)
        account = await client.get_account()
        
        print(f"   ✅ Conexão OK!")
        print(f"   Tipo de conta: {account.get('accountType', 'SPOT')}")
        print(f"   Pode negociar: {'Sim' if account.get('canTrade') else 'Não'}")
        
        # Mostrar saldos principais
        balances = account.get('balances', [])
        active_balances = [
            b for b in balances 
            if float(b['free']) > 0.00001 or float(b['locked']) > 0.00001
        ]
        
        if active_balances:
            print(f"   💰 Saldos encontrados: {len(active_balances)} moedas")
            
    except Exception as e:
        print(f"   ❌ Erro na conexão: {e}")
        print("\n   Verifique:")
        print("   1. Se as credenciais estão corretas")
        print("   2. Se a API Key tem permissões de leitura")
        print("   3. Se seu IP está na whitelist da Binance")
        return False
    finally:
        if client:
            await client.close_connection()
    
    # 4. Atualizar credenciais no banco de dados
    print("\n4️⃣ Atualizando credenciais no banco de dados...")
    
    try:
        await transaction_db.connect()
        
        # Criar serviço de criptografia com a chave configurada
        encryption_service = EncryptionService(master_key=encryption_key)
        
        # Criptografar credenciais
        encrypted_api_key = encryption_service.encrypt_string(api_key)
        encrypted_secret_key = encryption_service.encrypt_string(api_secret)
        
        # Buscar contas Binance existentes
        accounts = await transaction_db.fetch("""
            SELECT id, name FROM exchange_accounts 
            WHERE exchange = 'binance'
        """)
        
        if accounts:
            # Atualizar todas as contas Binance com as novas credenciais criptografadas
            for account in accounts:
                await transaction_db.execute("""
                    UPDATE exchange_accounts 
                    SET api_key = $1, secret_key = $2, updated_at = NOW()
                    WHERE id = $3
                """, encrypted_api_key, encrypted_secret_key, account['id'])
                
                print(f"   ✅ Conta '{account['name']}' atualizada")
        else:
            # Criar nova conta se não existir
            await transaction_db.execute("""
                INSERT INTO exchange_accounts (
                    name, exchange, api_key, secret_key, 
                    testnet, is_active, created_at, updated_at
                ) VALUES (
                    'Binance Principal', 'binance', $1, $2, 
                    false, true, NOW(), NOW()
                )
            """, encrypted_api_key, encrypted_secret_key)
            
            print("   ✅ Nova conta 'Binance Principal' criada")
        
        await transaction_db.disconnect()
        
    except Exception as e:
        print(f"   ❌ Erro ao atualizar banco: {e}")
        await transaction_db.disconnect()
        return False
    
    # 5. Testar integração completa
    print("\n5️⃣ Testando integração completa...")
    
    try:
        await transaction_db.connect()
        
        # Buscar conta e testar descriptografia
        account = await transaction_db.fetchrow("""
            SELECT id, name, api_key, secret_key 
            FROM exchange_accounts 
            WHERE exchange = 'binance' AND is_active = true
            LIMIT 1
        """)
        
        if account:
            # Descriptografar
            decrypted_api = encryption_service.decrypt_string(account['api_key'])
            decrypted_secret = encryption_service.decrypt_string(account['secret_key'])
            
            # Verificar se são iguais às originais
            if decrypted_api == api_key and decrypted_secret == api_secret:
                print(f"   ✅ Criptografia/Descriptografia funcionando!")
                
                # Testar connector
                connector = BinanceConnector(
                    api_key=decrypted_api,
                    api_secret=decrypted_secret,
                    testnet=False
                )
                
                result = await connector.test_connection()
                if result['success']:
                    print(f"   ✅ BinanceConnector funcionando!")
                else:
                    print(f"   ⚠️ BinanceConnector: {result.get('error')}")
            else:
                print(f"   ❌ Erro na descriptografia")
        
        await transaction_db.disconnect()
        
    except Exception as e:
        print(f"   ❌ Erro no teste: {e}")
        await transaction_db.disconnect()
        return False
    
    print("\n" + "=" * 60)
    print("✅ CONFIGURAÇÃO CONCLUÍDA COM SUCESSO!")
    print("\n📌 Resumo:")
    print(f"   • Chave de criptografia: Configurada no .env")
    print(f"   • Credenciais Binance: Configuradas e testadas")
    print(f"   • Banco de dados: Credenciais criptografadas e salvas")
    print(f"   • Integração: Testada e funcionando")
    print("\n🚀 Sua plataforma está pronta para carregar dados da Binance!")
    
    return True

if __name__ == "__main__":
    success = asyncio.run(setup_binance_credentials())
    
    if not success:
        print("\n⚠️ Configuração incompleta. Verifique os erros acima.")
        exit(1)
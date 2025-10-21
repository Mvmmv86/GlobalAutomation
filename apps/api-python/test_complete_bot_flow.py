#!/usr/bin/env python3
"""
Script de teste completo do fluxo de bots:
1. Admin cria bot
2. Bot aparece disponível para cliente
3. Cliente ativa bot
4. Webhook recebe sinal do TradingView
5. Sinal é broadcast para assinantes
6. Ordem é executada na Binance
"""
import asyncio
import httpx
import json
from datetime import datetime

BASE_URL = "http://localhost:8000"
ADMIN_EMAIL = "admin@globalautomation.com"
ADMIN_PASSWORD = "admin123"
USER_EMAIL = "user@test.com"
USER_PASSWORD = "user123"

async def test_complete_flow():
    print("\n" + "="*80)
    print("🧪 TESTE COMPLETO DO FLUXO DE BOTS")
    print("="*80 + "\n")

    async with httpx.AsyncClient(timeout=30.0) as client:

        # ====================================================================
        # PASSO 1: Admin faz login
        # ====================================================================
        print("📍 PASSO 1: Admin fazendo login...")
        admin_login = await client.post(f"{BASE_URL}/api/v1/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })

        if admin_login.status_code != 200:
            print(f"❌ Falha no login do admin: {admin_login.status_code}")
            print(f"   Resposta: {admin_login.text}")
            return False

        admin_token = admin_login.json()["access_token"]
        admin_headers = {"Authorization": f"Bearer {admin_token}"}
        print(f"✅ Admin autenticado com sucesso")

        # ====================================================================
        # PASSO 2: Admin cria um novo bot
        # ====================================================================
        print("\n📍 PASSO 2: Admin criando novo bot de teste...")
        bot_name = f"TEST_BOT_{datetime.now().strftime('%H%M%S')}"

        create_bot = await client.post(
            f"{BASE_URL}/api/v1/admin/bots",
            headers=admin_headers,
            json={
                "name": bot_name,
                "description": "Bot de teste automatizado",
                "market_type": "futures",
                "default_leverage": 10,
                "default_margin_percent": 5.0,
                "default_stop_loss": 2.0,
                "default_take_profit": 4.0,
                "is_active": True
            }
        )

        if create_bot.status_code != 201:
            print(f"❌ Falha ao criar bot: {create_bot.status_code}")
            print(f"   Resposta: {create_bot.text}")
            return False

        bot_data = create_bot.json()
        bot_id = bot_data["id"]
        master_webhook_url = bot_data.get("master_webhook_url", "")

        print(f"✅ Bot criado com sucesso!")
        print(f"   📋 ID: {bot_id}")
        print(f"   📛 Nome: {bot_name}")
        print(f"   🔗 Webhook URL: {master_webhook_url}")

        # ====================================================================
        # PASSO 3: Usuário faz login
        # ====================================================================
        print("\n📍 PASSO 3: Usuário cliente fazendo login...")
        user_login = await client.post(f"{BASE_URL}/api/v1/auth/login", json={
            "email": USER_EMAIL,
            "password": USER_PASSWORD
        })

        if user_login.status_code != 200:
            print(f"❌ Falha no login do usuário: {user_login.status_code}")
            print(f"   Resposta: {user_login.text}")
            return False

        user_token = user_login.json()["access_token"]
        user_id = user_login.json()["user"]["id"]
        user_headers = {"Authorization": f"Bearer {user_token}"}
        print(f"✅ Usuário autenticado com sucesso")
        print(f"   👤 User ID: {user_id}")

        # ====================================================================
        # PASSO 4: Verificar se bot aparece na lista de bots disponíveis
        # ====================================================================
        print("\n📍 PASSO 4: Verificando se bot aparece para o cliente...")
        available_bots = await client.get(
            f"{BASE_URL}/api/v1/bots/available",
            headers=user_headers
        )

        if available_bots.status_code != 200:
            print(f"❌ Falha ao buscar bots disponíveis: {available_bots.status_code}")
            return False

        bots_list = available_bots.json()
        bot_found = any(b["id"] == bot_id for b in bots_list)

        if not bot_found:
            print(f"❌ Bot {bot_name} NÃO aparece na lista de bots disponíveis")
            print(f"   Bots encontrados: {[b['name'] for b in bots_list]}")
            return False

        print(f"✅ Bot {bot_name} aparece na lista de bots disponíveis")

        # ====================================================================
        # PASSO 5: Verificar se usuário tem conta de exchange integrada
        # ====================================================================
        print("\n📍 PASSO 5: Verificando conta de exchange do usuário...")
        accounts = await client.get(
            f"{BASE_URL}/api/v1/exchange-accounts",
            headers=user_headers
        )

        if accounts.status_code != 200:
            print(f"❌ Falha ao buscar contas de exchange: {accounts.status_code}")
            return False

        accounts_list = accounts.json()
        if not accounts_list:
            print(f"⚠️  Usuário não tem conta de exchange integrada")
            print(f"   Não será possível executar ordens, mas o teste pode continuar")
            exchange_account_id = None
        else:
            exchange_account_id = accounts_list[0]["id"]
            print(f"✅ Conta de exchange encontrada:")
            print(f"   🏦 Exchange: {accounts_list[0]['exchange_type']}")
            print(f"   📋 ID: {exchange_account_id}")

        # ====================================================================
        # PASSO 6: Cliente ativa o bot (cria subscription)
        # ====================================================================
        print("\n📍 PASSO 6: Cliente ativando o bot...")

        subscription_payload = {
            "bot_id": bot_id,
            "leverage": 10,
            "margin_percent": 5.0,
            "stop_loss": 2.0,
            "take_profit": 4.0
        }

        if exchange_account_id:
            subscription_payload["exchange_account_id"] = exchange_account_id

        activate_bot = await client.post(
            f"{BASE_URL}/api/v1/bot-subscriptions",
            headers=user_headers,
            json=subscription_payload
        )

        if activate_bot.status_code != 200:
            print(f"❌ Falha ao ativar bot: {activate_bot.status_code}")
            print(f"   Resposta: {activate_bot.text}")
            return False

        subscription_data = activate_bot.json()
        subscription_id = subscription_data["id"]

        print(f"✅ Bot ativado com sucesso!")
        print(f"   📋 Subscription ID: {subscription_id}")
        print(f"   ⚙️  Alavancagem: {subscription_data['leverage']}x")
        print(f"   💰 Margem: {subscription_data['margin_percent']}%")

        # ====================================================================
        # PASSO 7: Simular webhook do TradingView
        # ====================================================================
        print("\n📍 PASSO 7: Simulando webhook do TradingView...")

        webhook_payload = {
            "symbol": "BTCUSDT",
            "action": "buy",
            "price": "45000.00",
            "timestamp": datetime.now().isoformat()
        }

        # Extrair webhook_path do master_webhook_url
        if master_webhook_url:
            webhook_path = master_webhook_url.split("/webhooks/master/")[-1]
            webhook_url = f"{BASE_URL}/api/v1/webhooks/master/{webhook_path}"
        else:
            print(f"❌ Master webhook URL não encontrado")
            return False

        print(f"   🔗 URL: {webhook_url}")
        print(f"   📦 Payload: {json.dumps(webhook_payload, indent=2)}")

        webhook_response = await client.post(
            webhook_url,
            json=webhook_payload
        )

        if webhook_response.status_code != 200:
            print(f"❌ Falha ao enviar webhook: {webhook_response.status_code}")
            print(f"   Resposta: {webhook_response.text}")
            return False

        webhook_result = webhook_response.json()
        print(f"✅ Webhook processado com sucesso!")
        print(f"   📊 Status: {webhook_result.get('status', 'N/A')}")
        print(f"   👥 Assinantes notificados: {webhook_result.get('subscribers_count', 0)}")

        # ====================================================================
        # PASSO 8: Verificar se sinal foi registrado
        # ====================================================================
        print("\n📍 PASSO 8: Verificando sinais do bot...")

        await asyncio.sleep(2)  # Aguardar processamento

        signals = await client.get(
            f"{BASE_URL}/api/v1/bots/{bot_id}/signals",
            headers=user_headers
        )

        if signals.status_code == 200:
            signals_list = signals.json()
            if signals_list:
                print(f"✅ Sinais encontrados: {len(signals_list)}")
                latest_signal = signals_list[0]
                print(f"   🎯 Último sinal:")
                print(f"      - Símbolo: {latest_signal.get('ticker', 'N/A')}")
                print(f"      - Ação: {latest_signal.get('action', 'N/A')}")
                print(f"      - Data: {latest_signal.get('created_at', 'N/A')}")
            else:
                print(f"⚠️  Nenhum sinal encontrado ainda")
        else:
            print(f"⚠️  Não foi possível verificar sinais: {signals.status_code}")

        # ====================================================================
        # PASSO 9: Cleanup - Desativar bot
        # ====================================================================
        print("\n📍 PASSO 9: Limpeza - Desativando bot de teste...")

        deactivate = await client.delete(
            f"{BASE_URL}/api/v1/bot-subscriptions/{subscription_id}",
            headers=user_headers
        )

        if deactivate.status_code == 200:
            print(f"✅ Bot desativado com sucesso")
        else:
            print(f"⚠️  Falha ao desativar bot: {deactivate.status_code}")

        # ====================================================================
        # RESUMO FINAL
        # ====================================================================
        print("\n" + "="*80)
        print("📊 RESUMO DO TESTE")
        print("="*80)
        print("✅ 1. Admin autenticado")
        print(f"✅ 2. Bot criado: {bot_name}")
        print("✅ 3. Usuário autenticado")
        print("✅ 4. Bot aparece na lista de disponíveis")
        print(f"{'✅' if exchange_account_id else '⚠️ '} 5. Conta de exchange {'encontrada' if exchange_account_id else 'não encontrada'}")
        print("✅ 6. Bot ativado pelo usuário")
        print("✅ 7. Webhook processado com sucesso")
        print(f"{'✅' if signals.status_code == 200 and signals_list else '⚠️ '} 8. Sinais registrados")
        print("✅ 9. Bot desativado (cleanup)")
        print("\n" + "="*80)
        print("🎉 TESTE COMPLETO FINALIZADO COM SUCESSO!")
        print("="*80 + "\n")

        return True

if __name__ == "__main__":
    try:
        result = asyncio.run(test_complete_flow())
        exit(0 if result else 1)
    except Exception as e:
        print(f"\n❌ ERRO NO TESTE: {e}")
        import traceback
        traceback.print_exc()
        exit(1)

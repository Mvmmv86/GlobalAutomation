#!/usr/bin/env python3
"""Script to check webhooks and deliveries in the database"""

import asyncio
import asyncpg
import os
import json
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(__file__))

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

async def check_webhooks():
    """Check webhooks configuration and deliveries"""

    # Get database URL
    db_url = os.getenv('TRANSACTION_POOLER_URL') or os.getenv('DATABASE_URL')
    if not db_url:
        print("❌ DATABASE_URL não configurado no .env")
        return

    # Parse asyncpg URL (remove +asyncpg if present)
    db_url = db_url.replace('postgresql+asyncpg://', 'postgresql://')

    try:
        # Connect to database
        print("🔌 Conectando ao banco de dados...")
        conn = await asyncpg.connect(db_url, ssl='prefer')
        print("✅ Conectado ao banco de dados Supabase\n")

        # ========================================
        # CHECK 1: Webhooks cadastrados
        # ========================================
        webhooks = await conn.fetch("""
            SELECT id, name, url_path, status, total_deliveries,
                   successful_deliveries, failed_deliveries, created_at,
                   secret
            FROM webhooks
            ORDER BY created_at DESC
            LIMIT 10
        """)

        print("=" * 80)
        print("📋 WEBHOOKS CADASTRADOS NO BANCO:")
        print("=" * 80)

        if webhooks:
            for webhook in webhooks:
                success_rate = 0
                if webhook['total_deliveries'] > 0:
                    success_rate = (webhook['successful_deliveries'] / webhook['total_deliveries']) * 100

                print(f"\n🔗 Webhook: {webhook['name']}")
                print(f"   ID: {webhook['id']}")
                print(f"   URL Path: {webhook['url_path']}")
                print(f"   Status: {webhook['status']}")
                print(f"   Secret: {webhook['secret'][:20]}..." if webhook['secret'] else "   Secret: N/A")
                print(f"   Total Deliveries: {webhook['total_deliveries']}")
                print(f"   Sucessos: {webhook['successful_deliveries']}")
                print(f"   Falhas: {webhook['failed_deliveries']}")
                print(f"   Taxa de Sucesso: {success_rate:.1f}%")
                print(f"   Criado em: {webhook['created_at']}")
                print(f"\n   📍 URL Completa: http://localhost:8000/api/v1/webhooks/tradingview/{webhook['url_path']}")
        else:
            print("\n⚠️  Nenhum webhook cadastrado ainda!")
            print("   Use o frontend (http://localhost:3000/webhooks) para criar um webhook.")

        # ========================================
        # CHECK 2: Webhook Deliveries
        # ========================================
        print("\n" + "=" * 80)
        print("📨 ÚLTIMAS REQUISIÇÕES RECEBIDAS (webhook_deliveries):")
        print("=" * 80)

        deliveries = await conn.fetch("""
            SELECT wd.id, wd.webhook_id, w.name as webhook_name, w.url_path,
                   wd.payload, wd.status, wd.response_status_code,
                   wd.created_at, wd.processed_at, wd.error_message,
                   wd.ip_address, wd.user_agent
            FROM webhook_deliveries wd
            LEFT JOIN webhooks w ON w.id = wd.webhook_id
            ORDER BY wd.created_at DESC
            LIMIT 10
        """)

        if deliveries:
            for i, delivery in enumerate(deliveries, 1):
                status_emoji = "✅" if delivery['status'] == 'success' else "❌"
                print(f"\n{status_emoji} [{i}] Delivery ID: {delivery['id']}")
                print(f"   Webhook: {delivery['webhook_name'] or 'N/A'} ({delivery['url_path']})")
                print(f"   Status: {delivery['status']}")
                print(f"   HTTP Status: {delivery['response_status_code']}")
                print(f"   IP: {delivery['ip_address']}")
                print(f"   User Agent: {delivery['user_agent'][:50]}..." if delivery['user_agent'] else "   User Agent: N/A")
                print(f"   Recebido em: {delivery['created_at']}")
                print(f"   Processado em: {delivery['processed_at'] or 'Processando...'}")

                if delivery['error_message']:
                    print(f"   ❌ Erro: {delivery['error_message'][:100]}...")

                if delivery['payload']:
                    try:
                        payload = json.loads(delivery['payload']) if isinstance(delivery['payload'], str) else delivery['payload']
                        print(f"   📦 Payload:")
                        print(f"      Action: {payload.get('action', 'N/A')}")
                        print(f"      Symbol: {payload.get('symbol', payload.get('ticker', 'N/A'))}")
                        print(f"      Quantity: {payload.get('quantity', 'N/A')}")
                        print(f"      Price: {payload.get('price', 'N/A')}")
                    except:
                        print(f"   📦 Payload: {str(delivery['payload'])[:100]}...")
        else:
            print("\n⚠️  Nenhuma requisição recebida ainda!")
            print("   O TradingView ainda não enviou nenhum sinal para esta URL.")
            print("   Verifique:")
            print("   1. Se o bot do TradingView está ativo")
            print("   2. Se a URL do webhook está correta no TradingView")
            print("   3. Se o backend está rodando (porta 8000)")

        # ========================================
        # CHECK 3: Trading Orders
        # ========================================
        print("\n" + "=" * 80)
        print("🏦 ORDENS CRIADAS A PARTIR DE WEBHOOKS:")
        print("=" * 80)

        orders = await conn.fetch("""
            SELECT o.id, o.symbol, o.side, o.quantity, o.status,
                   o.exchange_order_id, o.created_at, o.webhook_delivery_id,
                   o.average_price, o.filled_quantity
            FROM trading_orders o
            WHERE o.webhook_delivery_id IS NOT NULL
            ORDER BY o.created_at DESC
            LIMIT 10
        """)

        if orders:
            for i, order in enumerate(orders, 1):
                print(f"\n📊 [{i}] Ordem #{order['id']}")
                print(f"   Símbolo: {order['symbol']}")
                print(f"   Lado: {order['side'].upper()}")
                print(f"   Quantidade: {order['quantity']}")
                print(f"   Preenchido: {order['filled_quantity']}")
                print(f"   Preço Médio: {order['average_price']}")
                print(f"   Status: {order['status']}")
                print(f"   Exchange Order ID: {order['exchange_order_id']}")
                print(f"   Webhook Delivery ID: {order['webhook_delivery_id']}")
                print(f"   Criado em: {order['created_at']}")
        else:
            print("\n⚠️  Nenhuma ordem foi criada a partir de webhooks ainda!")
            print("   Isso significa que:")
            print("   - Os webhooks não estão recebendo requisições, OU")
            print("   - O processamento das ordens está falhando")

        # ========================================
        # CHECK 4: Backend Status
        # ========================================
        print("\n" + "=" * 80)
        print("🔍 STATUS DO SISTEMA:")
        print("=" * 80)

        # Check if backend is running
        import subprocess
        try:
            result = subprocess.run(
                ["lsof", "-i", ":8000"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.stdout:
                print("\n✅ Backend está RODANDO na porta 8000")
            else:
                print("\n❌ Backend NÃO está rodando na porta 8000")
                print("   Execute: cd /home/globalauto/global/apps/api-python && python3 main.py")
        except:
            print("\n⚠️  Não foi possível verificar o status do backend")

        await conn.close()
        print("\n" + "=" * 80)
        print("✅ Verificação concluída!")
        print("=" * 80)

    except Exception as e:
        print(f"\n❌ Erro ao conectar no banco: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(check_webhooks())

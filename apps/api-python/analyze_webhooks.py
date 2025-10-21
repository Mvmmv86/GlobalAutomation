#!/usr/bin/env python3
"""Analyze TradingView webhooks configuration and recent alerts"""

import asyncio
import asyncpg
from datetime import datetime
import json

async def check_webhooks():
    try:
        # Conectar ao banco
        conn = await asyncpg.connect(
            host='aws-0-us-east-1.pooler.supabase.com',
            port=6543,
            user='postgres.bvhtwnqgjnnlevzevpzy',
            password='GlobalAuto2024!',
            database='postgres'
        )

        print('=' * 80)
        print('ANÁLISE DE WEBHOOKS DO TRADINGVIEW')
        print('=' * 80)

        # Buscar todos os webhooks
        webhooks = await conn.fetch('''
            SELECT
                id, name, url_path, status, is_active,
                market_type, default_margin_usd, default_leverage,
                default_stop_loss_pct, default_take_profit_pct,
                total_deliveries, successful_deliveries, failed_deliveries,
                last_delivery_at, last_success_at,
                created_at, user_id
            FROM webhooks
            ORDER BY created_at DESC
        ''')

        if not webhooks:
            print('\n⚠️  Nenhum webhook encontrado no banco de dados')
            await conn.close()
            return

        print(f'\n📊 Total de webhooks encontrados: {len(webhooks)}')

        for i, webhook in enumerate(webhooks, 1):
            print(f'\n{"="*80}')
            print(f'WEBHOOK #{i}: {webhook["name"]}')
            print(f'{"="*80}')
            print(f'\n📍 ID: {webhook["id"]}')
            print(f'🔗 URL Path: /webhooks/tv/{webhook["url_path"]}')
            print(f'📡 URL Completa: http://localhost:8000/webhooks/tv/{webhook["url_path"]}')
            print(f'✅ Status: {webhook["status"]} (Ativo: {"Sim" if webhook["is_active"] else "Não"})')

            print(f'\n💰 PARÂMETROS DE TRADING:')
            print(f'   - Tipo de Mercado: {webhook["market_type"]}')
            print(f'   - Margem Padrão: ${webhook["default_margin_usd"]} USD')
            print(f'   - Alavancagem: {webhook["default_leverage"]}x')
            print(f'   - Stop Loss: {webhook["default_stop_loss_pct"]}%')
            print(f'   - Take Profit: {webhook["default_take_profit_pct"]}%')

            print(f'\n📈 ESTATÍSTICAS:')
            print(f'   - Total de Entregas: {webhook["total_deliveries"]}')
            print(f'   - Sucessos: {webhook["successful_deliveries"]}')
            print(f'   - Falhas: {webhook["failed_deliveries"]}')

            if webhook["total_deliveries"] > 0:
                success_rate = (webhook["successful_deliveries"] / webhook["total_deliveries"]) * 100
                print(f'   - Taxa de Sucesso: {success_rate:.1f}%')

            if webhook["last_delivery_at"]:
                print(f'   - Última Entrega: {webhook["last_delivery_at"]}')
            if webhook["last_success_at"]:
                print(f'   - Último Sucesso: {webhook["last_success_at"]}')

            # Buscar últimas 10 entregas deste webhook
            deliveries = await conn.fetch('''
                SELECT
                    id, status, created_at, processing_started_at,
                    processing_completed_at, processing_duration_ms,
                    payload, orders_created, orders_executed, orders_failed,
                    error_message, source_ip
                FROM webhook_deliveries
                WHERE webhook_id = $1
                ORDER BY created_at DESC
                LIMIT 10
            ''', webhook['id'])

            if deliveries:
                print(f'\n📨 ÚLTIMOS {len(deliveries)} ALERTAS RECEBIDOS:')
                for j, delivery in enumerate(deliveries, 1):
                    print(f'\n   Alerta #{j}:')
                    print(f'   - Horário: {delivery["created_at"]}')
                    print(f'   - Status: {delivery["status"]}')

                    if delivery['payload']:
                        payload = delivery['payload']
                        print(f'   - Payload completo: {json.dumps(payload, indent=6)}')
                        print(f'   - Símbolo: {payload.get("ticker") or payload.get("symbol", "N/A")}')
                        print(f'   - Ação: {payload.get("action", "N/A")}')
                        if 'price' in payload:
                            print(f'   - Preço: {payload.get("price")}')

                    print(f'   - Ordens Criadas: {delivery["orders_created"]}')
                    print(f'   - Ordens Executadas: {delivery["orders_executed"]}')
                    print(f'   - Ordens Falhadas: {delivery["orders_failed"]}')

                    if delivery['processing_duration_ms']:
                        print(f'   - Tempo de Processamento: {delivery["processing_duration_ms"]}ms')

                    if delivery['error_message']:
                        print(f'   - ⚠️ Erro: {delivery["error_message"]}')

                    if delivery['source_ip']:
                        print(f'   - IP Origem: {delivery["source_ip"]}')
            else:
                print(f'\n⚠️  Nenhum alerta recebido ainda para este webhook')

        # Resumo geral
        print(f'\n{"="*80}')
        print('RESUMO GERAL')
        print(f'{"="*80}')

        total_deliveries = sum(w['total_deliveries'] for w in webhooks)
        total_success = sum(w['successful_deliveries'] for w in webhooks)
        total_failed = sum(w['failed_deliveries'] for w in webhooks)

        print(f'\n📊 Total de alertas processados: {total_deliveries}')
        print(f'✅ Sucessos: {total_success}')
        print(f'❌ Falhas: {total_failed}')

        if total_deliveries > 0:
            overall_rate = (total_success / total_deliveries) * 100
            print(f'📈 Taxa de sucesso geral: {overall_rate:.1f}%')

        await conn.close()

    except Exception as e:
        print(f'❌ Erro ao conectar ao banco: {e}')
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(check_webhooks())

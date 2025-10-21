#!/usr/bin/env python3
"""Check webhooks using DI container"""

import asyncio
import sys
from pathlib import Path
import json
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

async def main():
    try:
        from infrastructure.di.container import get_container

        print('=' * 80)
        print('ANÁLISE DE WEBHOOKS DO TRADINGVIEW')
        print('=' * 80)

        # Get DI container
        container = await get_container()
        webhook_repo = container.get("webhook_repository")
        webhook_delivery_repo = container.get("webhook_delivery_repository")

        # Get all webhooks
        from infrastructure.database.models.webhook import WebhookStatus

        # Buscar todos os webhooks através do repository
        webhooks = await webhook_repo.get_multi(filters={}, limit=100, order_by="-created_at")

        if not webhooks:
            print('\n⚠️  Nenhum webhook encontrado no banco de dados')
            return

        print(f'\n📊 Total de webhooks encontrados: {len(webhooks)}')

        for i, webhook in enumerate(webhooks, 1):
            print(f'\n{"="*80}')
            print(f'WEBHOOK #{i}: {webhook.name}')
            print(f'{"="*80}')
            print(f'\n📍 ID: {webhook.id}')
            print(f'🔗 URL Path: /webhooks/tv/{webhook.url_path}')
            print(f'📡 URL Completa: http://localhost:8000/webhooks/tv/{webhook.url_path}')
            print(f'✅ Status: {webhook.status.value} (Ativo: {"Sim" if webhook.is_active() else "Não"})')

            print(f'\n💰 PARÂMETROS DE TRADING:')
            print(f'   - Tipo de Mercado: {webhook.market_type or "futures"}')
            print(f'   - Margem Padrão: ${webhook.default_margin_usd} USD')
            print(f'   - Alavancagem: {webhook.default_leverage}x')
            print(f'   - Stop Loss: {webhook.default_stop_loss_pct}%')
            print(f'   - Take Profit: {webhook.default_take_profit_pct}%')

            print(f'\n📈 ESTATÍSTICAS:')
            print(f'   - Total de Entregas: {webhook.total_deliveries}')
            print(f'   - Sucessos: {webhook.successful_deliveries}')
            print(f'   - Falhas: {webhook.failed_deliveries}')

            if webhook.total_deliveries > 0:
                success_rate = webhook.get_success_rate()
                print(f'   - Taxa de Sucesso: {success_rate:.1f}%')

            if webhook.last_delivery_at:
                print(f'   - Última Entrega: {webhook.last_delivery_at}')
            if webhook.last_success_at:
                print(f'   - Último Sucesso: {webhook.last_success_at}')

            # Buscar últimas 10 entregas deste webhook
            deliveries = await webhook_delivery_repo.get_webhook_deliveries(
                webhook_id=webhook.id,
                skip=0,
                limit=10
            )

            if deliveries:
                print(f'\n📨 ÚLTIMOS {len(deliveries)} ALERTAS RECEBIDOS:')
                for j, delivery in enumerate(deliveries, 1):
                    print(f'\n   Alerta #{j}:')
                    print(f'   - ID: {delivery.id}')
                    print(f'   - Horário: {delivery.created_at}')
                    print(f'   - Status: {delivery.status.value}')

                    if delivery.payload:
                        print(f'   - Payload completo:')
                        print(f'      {json.dumps(delivery.payload, indent=6)}')
                        print(f'   - Símbolo: {delivery.payload.get("ticker") or delivery.payload.get("symbol", "N/A")}')
                        print(f'   - Ação: {delivery.payload.get("action", "N/A")}')
                        if 'price' in delivery.payload:
                            print(f'   - Preço: {delivery.payload.get("price")}')

                    print(f'   - Ordens Criadas: {delivery.orders_created}')
                    print(f'   - Ordens Executadas: {delivery.orders_executed}')
                    print(f'   - Ordens Falhadas: {delivery.orders_failed}')

                    if delivery.processing_duration_ms:
                        print(f'   - Tempo de Processamento: {delivery.processing_duration_ms}ms')

                    if delivery.error_message:
                        print(f'   - ⚠️ Erro: {delivery.error_message}')

                    if delivery.source_ip:
                        print(f'   - IP Origem: {delivery.source_ip}')
            else:
                print(f'\n⚠️  Nenhum alerta recebido ainda para este webhook')

        # Resumo geral
        print(f'\n{"="*80}')
        print('RESUMO GERAL')
        print(f'{"="*80}')

        total_deliveries = sum(w.total_deliveries for w in webhooks)
        total_success = sum(w.successful_deliveries for w in webhooks)
        total_failed = sum(w.failed_deliveries for w in webhooks)

        print(f'\n📊 Total de alertas processados: {total_deliveries}')
        print(f'✅ Sucessos: {total_success}')
        print(f'❌ Falhas: {total_failed}')

        if total_deliveries > 0:
            overall_rate = (total_success / total_deliveries) * 100
            print(f'📈 Taxa de sucesso geral: {overall_rate:.1f}%')

        print(f'\n{"="*80}')

    except Exception as e:
        print(f'❌ Erro: {e}')
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())

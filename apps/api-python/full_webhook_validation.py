#!/usr/bin/env python3
"""Full webhook validation - check everything in detail"""

import asyncio
import sys
from pathlib import Path
import json
from datetime import datetime, timedelta

sys.path.insert(0, str(Path(__file__).parent))

async def main():
    try:
        from infrastructure.di.container import get_container

        print('=' * 80)
        print('VALIDAÇÃO COMPLETA - WEBHOOKS E ALERTAS DO TRADINGVIEW')
        print('=' * 80)

        container = await get_container()
        webhook_repo = container.get("webhook_repository")
        webhook_delivery_repo = container.get("webhook_delivery_repository")

        # Buscar todos os webhooks
        webhooks = await webhook_repo.get_multi(filters={}, limit=100, order_by="-created_at")

        if not webhooks:
            print('\n⚠️  Nenhum webhook encontrado')
            return

        print(f'\n📊 Total de webhooks: {len(webhooks)}')

        # Buscar TODAS as deliveries das últimas 24 horas
        from datetime import timezone
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=24)

        print(f'\n🕐 Buscando alertas desde: {cutoff_time}')

        all_deliveries = []

        for webhook in webhooks:
            print(f'\n{"="*80}')
            print(f'WEBHOOK: {webhook.name}')
            print(f'{"="*80}')
            print(f'ID: {webhook.id}')
            print(f'URL: /webhooks/tv/{webhook.url_path}')
            print(f'Status: {webhook.status.value} ({"ATIVO" if webhook.is_active() else "INATIVO"})')

            # Parâmetros
            print(f'\n💰 Configuração de Trading:')
            print(f'   Mercado: {webhook.market_type}')
            print(f'   Margem: ${webhook.default_margin_usd} USD')
            print(f'   Alavancagem: {webhook.default_leverage}x')
            print(f'   Stop Loss: {webhook.default_stop_loss_pct}%')
            print(f'   Take Profit: {webhook.default_take_profit_pct}%')

            # Estatísticas
            print(f'\n📊 Estatísticas:')
            print(f'   Total Entregas: {webhook.total_deliveries}')
            print(f'   Sucessos: {webhook.successful_deliveries}')
            print(f'   Falhas: {webhook.failed_deliveries}')
            if webhook.total_deliveries > 0:
                print(f'   Taxa Sucesso: {webhook.get_success_rate():.1f}%')

            if webhook.last_delivery_at:
                time_diff = datetime.now(timezone.utc) - webhook.last_delivery_at
                hours = time_diff.total_seconds() / 3600
                print(f'   Última Entrega: {webhook.last_delivery_at} (há {hours:.1f} horas)')

            # Buscar TODAS deliveries recentes deste webhook
            deliveries = await webhook_delivery_repo.get_webhook_deliveries(
                webhook_id=webhook.id,
                skip=0,
                limit=50  # Aumentar limite
            )

            # Filtrar deliveries das últimas 24h
            recent_deliveries = [d for d in deliveries if d.created_at >= cutoff_time]

            if recent_deliveries:
                print(f'\n📨 ALERTAS RECENTES ({len(recent_deliveries)} nas últimas 24h):')

                for i, delivery in enumerate(recent_deliveries, 1):
                    time_ago = datetime.now(timezone.utc) - delivery.created_at
                    minutes_ago = time_ago.total_seconds() / 60

                    print(f'\n   ═══ Alerta #{i} (há {minutes_ago:.0f} min) ═══')
                    print(f'   ID: {delivery.id}')
                    print(f'   Horário: {delivery.created_at}')
                    print(f'   Status: {delivery.status.value}')

                    if delivery.payload:
                        ticker = delivery.payload.get("ticker") or delivery.payload.get("symbol", "N/A")
                        action = delivery.payload.get("action", "N/A")
                        price = delivery.payload.get("price", "N/A")

                        print(f'   📈 Símbolo: {ticker}')
                        print(f'   📊 Ação: {action}')
                        print(f'   💰 Preço: {price}')
                        print(f'   📦 Payload completo:')
                        for key, value in delivery.payload.items():
                            print(f'      - {key}: {value}')

                    print(f'   ✅ Ordens Criadas: {delivery.orders_created}')
                    print(f'   🚀 Ordens Executadas: {delivery.orders_executed}')
                    print(f'   ❌ Ordens Falhadas: {delivery.orders_failed}')

                    if delivery.processing_duration_ms:
                        print(f'   ⏱️  Tempo: {delivery.processing_duration_ms}ms')

                    if delivery.error_message:
                        print(f'   ⚠️  ERRO: {delivery.error_message}')
                        if delivery.error_details:
                            print(f'   📋 Detalhes: {delivery.error_details}')

                    if delivery.source_ip:
                        print(f'   🌐 IP: {delivery.source_ip}')

                    all_deliveries.append({
                        'webhook': webhook.name,
                        'delivery': delivery
                    })
            else:
                print(f'\n⚠️  Nenhum alerta nas últimas 24 horas')

        # Resumo Final
        print(f'\n{"="*80}')
        print('📊 RESUMO FINAL - ÚLTIMAS 24 HORAS')
        print(f'{"="*80}')

        total_alerts = len(all_deliveries)
        print(f'\n🔔 Total de Alertas Recebidos: {total_alerts}')

        if total_alerts > 0:
            # Agrupar por webhook
            by_webhook = {}
            for item in all_deliveries:
                name = item['webhook']
                by_webhook[name] = by_webhook.get(name, 0) + 1

            print(f'\n📊 Distribuição por Webhook:')
            for webhook_name, count in sorted(by_webhook.items(), key=lambda x: x[1], reverse=True):
                print(f'   {webhook_name}: {count} alertas')

            # Agrupar por status
            by_status = {}
            for item in all_deliveries:
                status = item['delivery'].status.value
                by_status[status] = by_status.get(status, 0) + 1

            print(f'\n✅ Status dos Alertas:')
            for status, count in sorted(by_status.items()):
                emoji = "✅" if status == "success" else "❌" if status == "failed" else "⏳"
                print(f'   {emoji} {status}: {count}')

            # Alertas com erro
            failed = [item for item in all_deliveries if item['delivery'].error_message]
            if failed:
                print(f'\n⚠️  Alertas com Erro ({len(failed)}):')
                for item in failed:
                    d = item['delivery']
                    print(f'   - {item["webhook"]}: {d.error_message}')
        else:
            print('\n⚠️  NENHUM alerta recebido nas últimas 24 horas')
            print('\n🔍 Possíveis causas:')
            print('   1. TradingView não disparou alertas (condições não atingidas)')
            print('   2. URLs no TradingView estão incorretas')
            print('   3. ngrok/backend parou e reiniciou (URLs mudaram)')
            print('   4. Webhooks estão pausados/desativados no TradingView')

        # Verificar se backend está acessível
        print(f'\n{"="*80}')
        print('🔌 VERIFICAÇÃO DE CONECTIVIDADE')
        print(f'{"="*80}')

        import subprocess
        import socket

        # Verificar localhost:8000
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            result = sock.connect_ex(('127.0.0.1', 8000))
            sock.close()

            if result == 0:
                print('\n✅ Backend rodando em localhost:8000')
            else:
                print('\n❌ Backend NÃO está rodando em localhost:8000')
        except Exception as e:
            print(f'\n❌ Erro ao verificar backend: {e}')

        # Verificar ngrok
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            result = sock.connect_ex(('127.0.0.1', 4040))
            sock.close()

            if result == 0:
                print('✅ ngrok dashboard em localhost:4040')
                print('   Acesse http://localhost:4040 para ver a URL pública')
            else:
                print('❌ ngrok NÃO está rodando (porta 4040 fechada)')
        except Exception as e:
            print(f'❌ Erro ao verificar ngrok: {e}')

        print(f'\n{"="*80}')

    except Exception as e:
        print(f'❌ Erro: {e}')
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())

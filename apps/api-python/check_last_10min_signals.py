#!/usr/bin/env python3
"""
Verifica sinais recebidos nos últimos 10 minutos
"""
import asyncio
import asyncpg
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta

load_dotenv()

async def check_recent_signals():
    db_url = os.getenv('DATABASE_URL').replace('postgresql+asyncpg://', 'postgresql://')
    conn = await asyncpg.connect(db_url)

    # Get TPO_NDR bot
    bot = await conn.fetchrow("SELECT id, name FROM bots WHERE name = 'TPO_NDR'")

    if not bot:
        print("❌ Bot TPO_NDR não encontrado!")
        return

    # Get signals from last 10 minutes
    ten_min_ago = datetime.utcnow() - timedelta(minutes=10)

    signals = await conn.fetch("""
        SELECT
            id,
            ticker,
            action,
            source_ip,
            created_at,
            payload,
            successful_executions,
            failed_executions,
            total_subscribers
        FROM bot_signals
        WHERE bot_id = $1 AND created_at >= $2
        ORDER BY created_at DESC
    """, bot['id'], ten_min_ago)

    print()
    print("=" * 80)
    print(f"🔍 SINAIS RECEBIDOS NOS ÚLTIMOS 10 MINUTOS - BOT: {bot['name']}")
    print("=" * 80)
    print()

    if not signals:
        print("❌ NENHUM sinal recebido nos últimos 10 minutos!")
        print()
        print("💡 Possíveis causas:")
        print("   1. O alerta ainda não foi disparado no TradingView")
        print("   2. A condição do alerta não foi atingida")
        print("   3. A URL do webhook está incorreta")
        print()
        print("🔍 Verifique:")
        print("   • O alerta está ATIVO no TradingView?")
        print("   • A condição já foi atingida?")
        print("   • O gráfico está em DRIFTUSDT.P?")
        print()
    else:
        print(f"✅ TOTAL: {len(signals)} sinal(is) recebido(s)")
        print()

        for i, signal in enumerate(signals, 1):
            now = datetime.utcnow()
            created = signal['created_at']
            diff = (now - created).total_seconds()
            minutes_ago = int(diff / 60)
            seconds_ago = int(diff % 60)

            # Determine if it's from TradingView or test
            is_real = signal['source_ip'] != '127.0.0.1'
            source_label = "🌐 TRADINGVIEW" if is_real else "🧪 TESTE LOCAL"

            print(f"{'🔥' if is_real else '🧪'} SINAL #{i} - {source_label}")
            print(f"   ⏰ Recebido há: {minutes_ago}min {seconds_ago}s atrás")
            print(f"   📅 Data/Hora: {created.strftime('%d/%m/%Y %H:%M:%S')} UTC")
            print(f"   📈 ATIVO: {signal['ticker']}")
            print(f"   🎯 Ação: {signal['action'].upper()}")
            print(f"   🌐 IP: {signal['source_ip']}")
            print(f"   👥 Assinantes: {signal['total_subscribers']}")
            print(f"   ✅ Executados: {signal['successful_executions']} | ❌ Falhas: {signal['failed_executions']}")

            if signal['payload']:
                import json
                try:
                    payload_data = signal['payload'] if isinstance(signal['payload'], dict) else json.loads(signal['payload'])
                    print(f"   📦 Payload: {json.dumps(payload_data, indent=6)}")
                except:
                    print(f"   📦 Payload: {signal['payload']}")

            print()
            print("   " + "─" * 76)
            print()

    await conn.close()

asyncio.run(check_recent_signals())

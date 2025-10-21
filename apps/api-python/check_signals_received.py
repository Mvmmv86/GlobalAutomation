#!/usr/bin/env python3
import asyncio
import asyncpg
import os
from dotenv import load_dotenv
import json

load_dotenv()

async def check_signals():
    """Check all signals received today"""
    database_url = os.getenv("DATABASE_URL")

    if database_url.startswith("postgresql+asyncpg://"):
        database_url = database_url.replace("postgresql+asyncpg://", "postgresql://")

    conn = await asyncpg.connect(database_url)

    try:
        # Get all signals from today
        signals = await conn.fetch("""
            SELECT
                bs.id,
                bs.bot_id,
                b.name as bot_name,
                bs.ticker,
                bs.action,
                bs.source_ip,
                bs.payload,
                bs.created_at,
                bs.successful_executions,
                bs.failed_executions,
                bs.total_subscribers
            FROM bot_signals bs
            JOIN bots b ON b.id = bs.bot_id
            WHERE bs.created_at >= NOW() - INTERVAL '24 hours'
            ORDER BY bs.created_at DESC
            LIMIT 50
        """)

        print()
        print("=" * 80)
        print(f"📊 SINAIS RECEBIDOS (últimas 24h): {len(signals)} sinais")
        print("=" * 80)
        print()

        if not signals:
            print("❌ Nenhum sinal recebido ainda.")
            print()
            print("💡 Verifique:")
            print("   1. A URL do webhook está correta no TradingView?")
            print("   2. O ngrok está rodando e expondo a porta 8000?")
            print("   3. O alerta está ativo no TradingView?")
            print()
            return

        for i, signal in enumerate(signals, 1):
            timestamp = signal['created_at'].strftime("%d/%m/%Y %H:%M:%S")
            print(f"🔔 Sinal #{i}")
            print(f"   ⏰ Data/Hora: {timestamp}")
            print(f"   🤖 Bot: {signal['bot_name']}")
            print(f"   📈 Ativo: {signal['ticker']}")
            print(f"   🎯 Ação: {signal['action'].upper()}")
            print(f"   🌐 IP Origem: {signal['source_ip']}")
            print(f"   👥 Assinantes: {signal['total_subscribers']}")
            print(f"   ✅ Sucesso: {signal['successful_executions']} | ❌ Falha: {signal['failed_executions']}")

            if signal['payload']:
                try:
                    payload = json.loads(signal['payload']) if isinstance(signal['payload'], str) else signal['payload']
                    print(f"   📦 Payload: {json.dumps(payload, indent=6)}")
                except:
                    print(f"   📦 Payload: {signal['payload']}")

            print("   " + "-" * 76)
            print()

    except Exception as e:
        print(f"❌ Erro: {e}")
        raise
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(check_signals())

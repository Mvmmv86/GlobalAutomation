#!/usr/bin/env python3
"""
Monitora APENAS sinais novos do TradingView (ignora localhost)
"""
import asyncio
import asyncpg
import os
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

async def watch_signals():
    """Watch for new TradingView signals"""
    database_url = os.getenv("DATABASE_URL")

    if database_url.startswith("postgresql+asyncpg://"):
        database_url = database_url.replace("postgresql+asyncpg://", "postgresql://")

    conn = await asyncpg.connect(database_url)

    print()
    print("=" * 80)
    print("🎯 AGUARDANDO SINAIS DO TRADINGVIEW...")
    print("=" * 80)
    print()
    print("✅ Webhook conectado e funcionando!")
    print("⏳ Esperando próximo alerta do TradingView...")
    print()
    print("(Pressione Ctrl+C para sair)")
    print()
    print("━" * 80)
    print()

    last_check_time = datetime.utcnow()

    try:
        while True:
            # Get signals newer than last check, excluding localhost
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
                WHERE bs.created_at > $1
                  AND bs.source_ip != '127.0.0.1'
                ORDER BY bs.created_at ASC
            """, last_check_time)

            if signals:
                for signal in signals:
                    timestamp = signal['created_at'].strftime("%H:%M:%S")

                    print(f"🚨 NOVO SINAL RECEBIDO DO TRADINGVIEW!")
                    print(f"   ⏰ Hora: {timestamp}")
                    print(f"   🤖 Bot: {signal['bot_name']}")
                    print(f"   📈 ATIVO: {signal['ticker']}")
                    print(f"   🎯 Ação: {signal['action'].upper()}")
                    print(f"   🌐 IP: {signal['source_ip']}")
                    print(f"   👥 Assinantes: {signal['total_subscribers']}")
                    print(f"   ✅ Executados: {signal['successful_executions']} | ❌ Falhas: {signal['failed_executions']}")
                    print()
                    print("   " + "─" * 76)
                    print()

                last_check_time = signals[-1]['created_at']

            await asyncio.sleep(2)  # Check every 2 seconds

    except KeyboardInterrupt:
        print()
        print("🛑 Monitor encerrado")
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(watch_signals())

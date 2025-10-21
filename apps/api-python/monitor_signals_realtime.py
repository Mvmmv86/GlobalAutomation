#!/usr/bin/env python3
"""
Monitor de Sinais em Tempo Real
Mostra todos os webhooks recebidos do TradingView
"""
import asyncio
import asyncpg
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta
import time

load_dotenv()

async def monitor_signals():
    """Monitor signals in real-time"""
    database_url = os.getenv("DATABASE_URL")

    if database_url.startswith("postgresql+asyncpg://"):
        database_url = database_url.replace("postgresql+asyncpg://", "postgresql://")

    conn = await asyncpg.connect(database_url)

    print("=" * 80)
    print("🔴 MONITOR DE SINAIS DO TRADINGVIEW - TEMPO REAL")
    print("=" * 80)
    print()

    # Get all active bots
    bots = await conn.fetch("""
        SELECT id, name, master_webhook_path, status
        FROM bots
        WHERE status = 'active'
        ORDER BY created_at DESC
    """)

    print(f"📊 Bots Ativos Monitorados: {len(bots)}")
    print()
    for bot in bots:
        print(f"   🤖 {bot['name']}")
        print(f"      Webhook: /api/v1/bots/webhook/master/{bot['master_webhook_path']}")
    print()
    print("━" * 80)
    print()

    last_signal_id = None

    try:
        while True:
            # Get latest signal
            query = """
                SELECT
                    bs.id,
                    bs.bot_id,
                    b.name as bot_name,
                    bs.ticker,
                    bs.action,
                    bs.created_at,
                    bs.successful_executions,
                    bs.failed_executions,
                    bs.total_subscribers
                FROM bot_signals bs
                JOIN bots b ON b.id = bs.bot_id
                ORDER BY bs.created_at DESC
                LIMIT 1
            """

            signal = await conn.fetchrow(query)

            if signal and (last_signal_id is None or signal['id'] != last_signal_id):
                last_signal_id = signal['id']

                timestamp = signal['created_at'].strftime("%H:%M:%S")
                ticker = signal['ticker']
                action = signal['action'].upper()
                bot_name = signal['bot_name']

                # Color code actions
                if action == 'BUY':
                    action_display = f"🟢 {action} (LONG)"
                elif action == 'SELL':
                    action_display = f"🔴 {action} (SHORT)"
                elif action in ['CLOSE', 'CLOSE_ALL']:
                    action_display = f"⚪ {action}"
                else:
                    action_display = f"🟡 {action}"

                print(f"⚡ [{timestamp}] NOVO SINAL RECEBIDO!")
                print(f"   🤖 Bot: {bot_name}")
                print(f"   📈 Ativo: {ticker}")
                print(f"   {action_display}")
                print(f"   👥 Assinantes: {signal['total_subscribers']}")
                print(f"   ✅ Sucesso: {signal['successful_executions']} | ❌ Falha: {signal['failed_executions']}")
                print("   " + "─" * 76)
                print()

            await asyncio.sleep(1)  # Check every second

    except KeyboardInterrupt:
        print()
        print("🛑 Monitor encerrado pelo usuário")
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(monitor_signals())

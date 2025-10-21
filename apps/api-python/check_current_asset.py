#!/usr/bin/env python3
import asyncio
import asyncpg
import os
from dotenv import load_dotenv

load_dotenv()

async def check():
    db_url = os.getenv('DATABASE_URL').replace('postgresql+asyncpg://', 'postgresql://')
    conn = await asyncpg.connect(db_url)

    # Get ALL signals (including localhost for now)
    all_signals = await conn.fetch("""
        SELECT
            bs.ticker,
            bs.action,
            bs.source_ip,
            bs.created_at,
            b.name as bot_name
        FROM bot_signals bs
        JOIN bots b ON b.id = bs.bot_id
        ORDER BY bs.created_at DESC
        LIMIT 10
    """)

    # Get signals excluding localhost
    real_signals = await conn.fetch("""
        SELECT
            bs.ticker,
            bs.action,
            bs.source_ip,
            bs.created_at,
            b.name as bot_name
        FROM bot_signals bs
        JOIN bots b ON b.id = bs.bot_id
        WHERE bs.source_ip != '127.0.0.1'
        ORDER BY bs.created_at DESC
        LIMIT 10
    """)

    print()
    print("=" * 80)
    print("📊 ATIVOS QUE O BOT ESTÁ RECEBENDO DO TRADINGVIEW")
    print("=" * 80)
    print()

    if not real_signals:
        print("❌ NENHUM sinal REAL do TradingView ainda!")
        print("   (Apenas sinais de teste com IP 127.0.0.1)")
        print()
        print("📋 Últimos sinais (incluindo testes):")
        for s in all_signals[:3]:
            print(f"   ⏰ {s['created_at'].strftime('%H:%M:%S')} | 📈 {s['ticker']} | 🎯 {s['action'].upper()} | IP: {s['source_ip']}")
        print()
        print("💡 O TradingView ainda não disparou nenhum alerta real.")
        print("   Aguardando próximo sinal...")
    else:
        print("✅ SINAIS REAIS DO TRADINGVIEW:")
        print()
        for s in real_signals:
            print(f"⏰ {s['created_at'].strftime('%d/%m %H:%M:%S')}")
            print(f"   🤖 Bot: {s['bot_name']}")
            print(f"   📈 ATIVO: {s['ticker']}")
            print(f"   🎯 Ação: {s['action'].upper()}")
            print(f"   🌐 IP: {s['source_ip']}")
            print()

    await conn.close()

asyncio.run(check())

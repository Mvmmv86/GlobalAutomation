#!/usr/bin/env python3
import asyncio
import asyncpg
import os
from dotenv import load_dotenv

load_dotenv()

async def check():
    db_url = os.getenv('DATABASE_URL').replace('postgresql+asyncpg://', 'postgresql://')
    conn = await asyncpg.connect(db_url)

    # Get TPO_NDR bot
    bot = await conn.fetchrow("SELECT id, name FROM bots WHERE name = 'TPO_NDR'")

    if not bot:
        print("Bot não encontrado!")
        return

    # Get ALL signals for this bot
    all_signals = await conn.fetch("""
        SELECT ticker, action, source_ip, created_at
        FROM bot_signals
        WHERE bot_id = $1
        ORDER BY created_at DESC
    """, bot['id'])

    # Separate real signals from test signals
    real_signals = [s for s in all_signals if s['source_ip'] != '127.0.0.1']
    test_signals = [s for s in all_signals if s['source_ip'] == '127.0.0.1']

    print()
    print("=" * 80)
    print(f"📊 ANÁLISE DE SINAIS DO BOT: {bot['name']}")
    print("=" * 80)
    print()

    print(f"📋 Total de sinais: {len(all_signals)}")
    print(f"   🧪 Sinais de teste (127.0.0.1): {len(test_signals)}")
    print(f"   ✅ Sinais REAIS do TradingView: {len(real_signals)}")
    print()

    if real_signals:
        print("🎯 SINAIS REAIS DO TRADINGVIEW:")
        print("━" * 80)
        for s in real_signals[:10]:
            print(f"   ⏰ {s['created_at'].strftime('%d/%m %H:%M:%S')} | 📈 {s['ticker']} | 🎯 {s['action'].upper()} | IP: {s['source_ip']}")
        print()
    else:
        print("❌ NENHUM sinal REAL do TradingView ainda!")
        print()
        print("📝 Todos os sinais são de TESTES (IP 127.0.0.1)")
        print()
        print("💡 Para descobrir qual ativo está configurado no TradingView:")
        print("   1. Abra o TradingView")
        print("   2. Clique no sino (alertas)")
        print("   3. Encontre o alerta conectado ao bot TPO_NDR")
        print("   4. Olhe qual par está no código JSON")
        print("   5. Exemplo: {\"ticker\": \"{{ticker}}\"} vai enviar o ativo do gráfico")
        print()
        print("🔔 OU force um alerta de teste no TradingView agora!")
        print()

    await conn.close()

asyncio.run(check())

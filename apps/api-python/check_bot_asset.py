#!/usr/bin/env python3
"""
Verifica qual ativo está conectado no bot TPO_NDR
"""
import asyncio
import asyncpg
import os
from dotenv import load_dotenv

load_dotenv()

async def check_bot_asset():
    db_url = os.getenv('DATABASE_URL').replace('postgresql+asyncpg://', 'postgresql://')
    conn = await asyncpg.connect(db_url)

    # Get the TPO_NDR bot info
    bot = await conn.fetchrow("""
        SELECT id, name, master_webhook_path, status, created_at
        FROM bots
        WHERE name = 'TPO_NDR'
    """)

    if not bot:
        print("❌ Bot TPO_NDR não encontrado!")
        await conn.close()
        return

    print()
    print("=" * 80)
    print(f"🤖 BOT: {bot['name']}")
    print("=" * 80)
    print()
    print(f"   📍 Webhook Path: {bot['master_webhook_path']}")
    print(f"   🔗 URL Completa: http://seu-ngrok/api/v1/bots/webhook/master/{bot['master_webhook_path']}")
    print(f"   📅 Criado em: {bot['created_at'].strftime('%d/%m/%Y %H:%M:%S')}")
    print()
    print("━" * 80)
    print()

    # Get all signals for this bot
    signals = await conn.fetch("""
        SELECT
            ticker,
            action,
            source_ip,
            created_at,
            successful_executions,
            failed_executions,
            total_subscribers
        FROM bot_signals
        WHERE bot_id = $1
        ORDER BY created_at DESC
    """, bot['id'])

    if not signals:
        print("❌ NENHUM SINAL RECEBIDO AINDA PARA ESTE BOT!")
        print()
        print("💡 Possíveis causas:")
        print("   1. O alerta ainda não foi disparado no TradingView")
        print("   2. A URL do webhook não está correta no TradingView")
        print("   3. O ngrok não está expondo a porta 8000")
        print()
        print("🔍 Verifique no TradingView:")
        print("   • Alerta está ATIVO?")
        print("   • URL do webhook está correta?")
        print("   • Qual {{ticker}} está configurado no JSON do alerta?")
    else:
        # Group signals by ticker
        tickers = {}
        for s in signals:
            ticker = s['ticker']
            if ticker not in tickers:
                tickers[ticker] = {
                    'count': 0,
                    'buy': 0,
                    'sell': 0,
                    'close': 0,
                    'last_signal': None
                }
            tickers[ticker]['count'] += 1
            if s['action'].lower() == 'buy':
                tickers[ticker]['buy'] += 1
            elif s['action'].lower() == 'sell':
                tickers[ticker]['sell'] += 1
            elif s['action'].lower() in ['close', 'close_all']:
                tickers[ticker]['close'] += 1
            tickers[ticker]['last_signal'] = s['created_at']

        print(f"✅ TOTAL DE SINAIS RECEBIDOS: {len(signals)}")
        print()
        print("📈 ATIVOS DETECTADOS:")
        print()

        for ticker, stats in tickers.items():
            print(f"   🎯 {ticker}")
            print(f"      Total de sinais: {stats['count']}")
            print(f"      🟢 BUY: {stats['buy']} | 🔴 SELL: {stats['sell']} | ⚪ CLOSE: {stats['close']}")
            print(f"      ⏰ Último sinal: {stats['last_signal'].strftime('%d/%m/%Y %H:%M:%S')}")
            print()

        print("━" * 80)
        print()
        print(f"🎯 O TradingView está enviando sinais para: {', '.join(tickers.keys())}")

    await conn.close()

asyncio.run(check_bot_asset())

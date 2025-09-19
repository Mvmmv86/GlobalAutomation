#!/usr/bin/env python3
"""Testar dados da Binance"""

import asyncio
from binance import AsyncClient
from datetime import datetime
import json

async def test_binance_data():
    print("\n🚀 TESTANDO CONEXÃO E DADOS DA BINANCE")
    print("=" * 60)
    
    client = None
    try:
        # Criar cliente sem credenciais (acesso público)
        client = await AsyncClient.create()
        
        # 1. Testar ping
        print("\n📡 1. Testando conectividade...")
        await client.ping()
        print("✅ Conectado com sucesso!")
        
        # 2. Obter informações do servidor
        print("\n⏰ 2. Horário do servidor Binance:")
        server_time = await client.get_server_time()
        server_datetime = datetime.fromtimestamp(server_time['serverTime'] / 1000)
        print(f"   Server time: {server_datetime}")
        print(f"   Local time:  {datetime.now()}")
        
        # 3. Obter preços atuais
        print("\n💰 3. Preços atuais (SPOT):")
        symbols = ["BTCUSDT", "ETHUSDT", "BNBUSDT"]
        for symbol in symbols:
            ticker = await client.get_symbol_ticker(symbol=symbol)
            print(f"   {symbol}: ${float(ticker['price']):,.2f}")
        
        # 4. Obter estatísticas 24h
        print("\n📊 4. Estatísticas 24h BTC/USDT:")
        stats = await client.get_ticker(symbol="BTCUSDT")
        print(f"   Preço atual: ${float(stats['lastPrice']):,.2f}")
        print(f"   Abertura 24h: ${float(stats['openPrice']):,.2f}")
        print(f"   Alta 24h: ${float(stats['highPrice']):,.2f}")
        print(f"   Baixa 24h: ${float(stats['lowPrice']):,.2f}")
        print(f"   Volume 24h: {float(stats['volume']):,.2f} BTC")
        print(f"   Volume USDT: ${float(stats['quoteVolume']):,.2f}")
        change = float(stats['priceChangePercent'])
        print(f"   Variação 24h: {'+' if change > 0 else ''}{change:.2f}%")
        
        # 5. Order Book
        print("\n📖 5. Order Book BTC/USDT (Top 5):")
        depth = await client.get_order_book(symbol="BTCUSDT", limit=5)
        
        print("   COMPRA (Bids):")
        for i, bid in enumerate(depth['bids'][:5], 1):
            price = float(bid[0])
            amount = float(bid[1])
            total = price * amount
            print(f"     {i}. ${price:,.2f} x {amount:.8f} = ${total:,.2f}")
        
        print("   VENDA (Asks):")
        for i, ask in enumerate(depth['asks'][:5], 1):
            price = float(ask[0])
            amount = float(ask[1])
            total = price * amount
            print(f"     {i}. ${price:,.2f} x {amount:.8f} = ${total:,.2f}")
        
        # 6. Últimas trades
        print("\n💱 6. Últimas 5 trades BTC/USDT:")
        trades = await client.get_recent_trades(symbol="BTCUSDT", limit=5)
        for i, trade in enumerate(trades, 1):
            price = float(trade['price'])
            qty = float(trade['qty'])
            time = datetime.fromtimestamp(trade['time'] / 1000)
            side = "COMPRA" if trade['isBuyerMaker'] else "VENDA"
            print(f"   {i}. {time.strftime('%H:%M:%S')} | {side} | ${price:,.2f} x {qty:.8f}")
        
        # 7. Informações de mercado
        print("\n🏪 7. Informações do par BTC/USDT:")
        info = await client.get_symbol_info('BTCUSDT')
        print(f"   Status: {info['status']}")
        print(f"   Base Asset: {info['baseAsset']}")
        print(f"   Quote Asset: {info['quoteAsset']}")
        
        # Filtros importantes
        for filter in info['filters']:
            if filter['filterType'] == 'LOT_SIZE':
                print(f"   Min Qty: {filter['minQty']}")
                print(f"   Max Qty: {filter['maxQty']}")
                print(f"   Step Size: {filter['stepSize']}")
            elif filter['filterType'] == 'PRICE_FILTER':
                print(f"   Min Price: {filter['minPrice']}")
                print(f"   Max Price: {filter['maxPrice']}")
                print(f"   Tick Size: {filter['tickSize']}")
        
        print("\n✅ TODOS OS DADOS FORAM RECUPERADOS COM SUCESSO!")
        return True
        
    except Exception as e:
        print(f"\n❌ Erro ao buscar dados: {e}")
        return False
    finally:
        if client:
            await client.close_connection()

if __name__ == "__main__":
    asyncio.run(test_binance_data())
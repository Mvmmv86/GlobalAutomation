#!/usr/bin/env python3
"""Test all webhook configurations and parameters"""

import asyncio
import asyncpg
import json
from typing import List, Dict, Any

# Database configuration
DB_URL = "postgresql://postgres.slbhnqqioeuvrdwkdjgv:Global2024!@aws-0-us-east-1.pooler.supabase.com:6543/postgres"

async def get_webhooks() -> List[Dict[str, Any]]:
    """Fetch all active webhooks with their parameters"""
    conn = await asyncpg.connect(DB_URL)

    try:
        rows = await conn.fetch("""
            SELECT
                id,
                name,
                market_type,
                default_margin_usd,
                default_leverage,
                default_stop_loss_pct,
                default_take_profit_pct,
                status,
                created_at
            FROM webhooks
            WHERE status = 'active'
            ORDER BY name
        """)

        webhooks = []
        for row in rows:
            webhooks.append({
                'id': str(row['id']),
                'name': row['name'],
                'market_type': row['market_type'],
                'margin_usd': float(row['default_margin_usd']) if row['default_margin_usd'] else None,
                'leverage': int(row['default_leverage']) if row['default_leverage'] else None,
                'stop_loss_pct': float(row['default_stop_loss_pct']) if row['default_stop_loss_pct'] else None,
                'take_profit_pct': float(row['default_take_profit_pct']) if row['default_take_profit_pct'] else None,
                'status': row['status'],
                'created_at': row['created_at'].isoformat() if row['created_at'] else None
            })

        return webhooks

    finally:
        await conn.close()

async def test_webhook_calculation(webhook: Dict[str, Any], test_price: float = 100.0):
    """Test quantity calculation for a webhook"""

    if not webhook['margin_usd'] or not webhook['leverage']:
        return {
            'error': 'Missing margin_usd or leverage',
            'calculated_quantity': None
        }

    # Calculate quantity
    quantity = (webhook['margin_usd'] * webhook['leverage']) / test_price

    # Calculate position size in USDT
    position_size_usdt = quantity * test_price

    return {
        'calculated_quantity': quantity,
        'position_size_usdt': position_size_usdt,
        'effective_leverage': position_size_usdt / webhook['margin_usd']
    }

async def main():
    print("=" * 80)
    print("🔍 VERIFICAÇÃO DE WEBHOOKS E PARÂMETROS")
    print("=" * 80)
    print()

    webhooks = await get_webhooks()

    if not webhooks:
        print("❌ Nenhum webhook ativo encontrado!")
        return

    print(f"📊 Total de webhooks ativos: {len(webhooks)}\n")

    for i, webhook in enumerate(webhooks, 1):
        print(f"{'─' * 80}")
        print(f"Webhook #{i}: {webhook['name']}")
        print(f"{'─' * 80}")
        print(f"🆔 ID: {webhook['id']}")
        print(f"📈 Market Type: {webhook['market_type'].upper()}")
        print(f"💰 Margin: ${webhook['margin_usd']}" if webhook['margin_usd'] else "💰 Margin: ❌ NÃO CONFIGURADO")
        print(f"⚡ Leverage: {webhook['leverage']}x" if webhook['leverage'] else "⚡ Leverage: ❌ NÃO CONFIGURADO")
        print(f"🛡️  Stop Loss: {webhook['stop_loss_pct']}%" if webhook['stop_loss_pct'] else "🛡️  Stop Loss: ⚠️ Não configurado")
        print(f"🎯 Take Profit: {webhook['take_profit_pct']}%" if webhook['take_profit_pct'] else "🎯 Take Profit: ⚠️ Não configurado")
        print(f"📅 Criado em: {webhook['created_at']}")

        # Test calculation with sample prices
        print(f"\n🧮 TESTE DE CÁLCULO (preço de exemplo):")

        for test_price in [100.0, 50.0, 200.0]:
            calc = await test_webhook_calculation(webhook, test_price)

            if 'error' in calc:
                print(f"   ❌ Preço ${test_price}: {calc['error']}")
            else:
                print(f"   ✅ Preço ${test_price}:")
                print(f"      • Quantity: {calc['calculated_quantity']:.4f}")
                print(f"      • Position Size: ${calc['position_size_usdt']:.2f} USDT")
                print(f"      • Leverage Efetivo: {calc['effective_leverage']:.1f}x")

        # Generate webhook URL
        print(f"\n📎 URL do Webhook:")
        print(f"   https://fa07391f9d44.ngrok-free.app/api/v1/webhooks/tradingview/{webhook['id']}")
        print()

    print("=" * 80)
    print("✅ Verificação completa!")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(main())

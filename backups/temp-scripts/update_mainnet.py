#!/usr/bin/env python3
"""Update exchange account to use mainnet instead of testnet"""

import asyncio
from infrastructure.database.connection_transaction_mode import transaction_db

async def update_to_mainnet():
    """Update the Binance account to use mainnet"""
    try:
        # Update the account to use mainnet
        result = await transaction_db.execute("""
            UPDATE exchange_accounts 
            SET testnet = false 
            WHERE id = '78e6b4fa-9a71-4360-b808-f1cd7c98dcbe'
        """)
        
        print(f"✅ Account updated to mainnet. Rows affected: {result}")
        
        # Verify the update
        account = await transaction_db.fetchrow("""
            SELECT name, exchange, testnet, is_active
            FROM exchange_accounts 
            WHERE id = '78e6b4fa-9a71-4360-b808-f1cd7c98dcbe'
        """)
        
        if account:
            print(f"📊 Account details:")
            print(f"   Name: {account['name']}")
            print(f"   Exchange: {account['exchange']}")
            print(f"   Testnet: {account['testnet']}")
            print(f"   Active: {account['is_active']}")
        
    except Exception as e:
        print(f"❌ Error updating account: {e}")

if __name__ == "__main__":
    asyncio.run(update_to_mainnet())
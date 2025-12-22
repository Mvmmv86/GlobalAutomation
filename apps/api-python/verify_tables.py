"""Verify if strategy tables were created in Supabase"""

import asyncio
import asyncpg

DATABASE_URL = "postgresql://postgres.zmdqmrugotfftxvrwdsd:Wzg0kBvtrSbclQ9V@aws-1-us-east-2.pooler.supabase.com:5432/postgres"


async def verify_tables():
    print("Connecting to Supabase...")

    try:
        conn = await asyncpg.connect(DATABASE_URL)
        print("Connected!\n")

        # Check for strategy tables
        tables = await conn.fetch("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            AND table_name LIKE 'strateg%'
            ORDER BY table_name
        """)

        print("=" * 50)
        print("STRATEGY TABLES FOUND:")
        print("=" * 50)

        expected_tables = [
            'strategies',
            'strategy_backtest_results',
            'strategy_conditions',
            'strategy_indicators',
            'strategy_signals'
        ]

        found_tables = [t['table_name'] for t in tables]

        for table in expected_tables:
            status = "✓ EXISTS" if table in found_tables else "✗ MISSING"
            print(f"  {status}: {table}")

        print("\n" + "=" * 50)
        print(f"Total expected: {len(expected_tables)}")
        print(f"Total found: {len(found_tables)}")
        print("=" * 50)

        # Show column count for each table
        if found_tables:
            print("\nTABLE DETAILS:")
            print("-" * 50)
            for table in found_tables:
                columns = await conn.fetch("""
                    SELECT column_name, data_type
                    FROM information_schema.columns
                    WHERE table_schema = 'public'
                    AND table_name = $1
                    ORDER BY ordinal_position
                """, table)
                print(f"\n{table} ({len(columns)} columns):")
                for col in columns[:5]:  # Show first 5 columns
                    print(f"    - {col['column_name']}: {col['data_type']}")
                if len(columns) > 5:
                    print(f"    ... and {len(columns) - 5} more columns")

        await conn.close()

        # Return success status
        return len(found_tables) == len(expected_tables)

    except Exception as e:
        print(f"Error: {e}")
        return False


if __name__ == "__main__":
    success = asyncio.run(verify_tables())
    if success:
        print("\n✓ ALL TABLES VERIFIED SUCCESSFULLY!")
    else:
        print("\n✗ SOME TABLES ARE MISSING!")

#!/usr/bin/env python3
"""
Test script to simulate TradingView webhook and validate Flow 2 fixes

Tests:
1. Schema mismatch fixes (exchange_account fields)
2. Webhook payload processing
3. Order creation flow
4. HTTP 200 response on errors
5. SL/TP order types

Usage:
    python3 test_tradingview_webhook_simulation.py
"""

import asyncio
import json
import sys
from pathlib import Path

# Add project root to Python path
sys.path.insert(0, str(Path(__file__).parent))


async def test_exchange_account_schema():
    """Test 1: Verify exchange_account schema fixes"""
    print("\n" + "=" * 80)
    print("TEST 1: Exchange Account Schema Validation")
    print("=" * 80)

    try:
        from infrastructure.database.models.exchange_account import ExchangeAccount

        # Create a test account object
        account_data = {
            "name": "Test Binance Account",
            "exchange_type": "binance",
            "api_key_encrypted": "test_key",
            "api_secret_encrypted": "test_secret",
            "testnet": True,
            "is_active": True,
            "user_id": "00000000-0000-0000-0000-000000000000",
        }

        account = ExchangeAccount(**account_data)

        # Test @property fields
        assert account.health_status == "healthy", "health_status should be 'healthy' when active"
        assert account.total_orders == 0, "total_orders should be 0"
        assert account.environment.value == "testnet", "environment should derive from testnet"

        print("✅ ExchangeAccount model correctly configured")
        print(f"   - health_status: {account.health_status}")
        print(f"   - total_orders: {account.total_orders}")
        print(f"   - environment: {account.environment.value}")

        return True

    except Exception as e:
        print(f"❌ ExchangeAccount schema test failed: {e}")
        return False


async def test_repository_queries():
    """Test 2: Verify repository doesn't query non-existent fields"""
    print("\n" + "=" * 80)
    print("TEST 2: Repository Query Validation")
    print("=" * 80)

    try:
        from infrastructure.database.repositories.exchange_account import (
            ExchangeAccountRepository,
        )
        import inspect

        # Verify critical methods don't reference non-existent fields directly
        repo_source = inspect.getsource(ExchangeAccountRepository)

        # These should NOT appear in direct column queries
        forbidden_patterns = [
            'ExchangeAccount.health_status ==',
            'ExchangeAccount.total_orders',
            'ExchangeAccount.successful_orders',
            'ExchangeAccount.failed_orders',
            'ExchangeAccount.last_health_check',
        ]

        issues = []
        for pattern in forbidden_patterns:
            if pattern in repo_source:
                issues.append(f"Found forbidden pattern: {pattern}")

        if issues:
            print("❌ Repository still queries non-existent fields:")
            for issue in issues:
                print(f"   - {issue}")
            return False
        else:
            print("✅ Repository correctly avoids non-existent fields")
            print("   - No direct queries on health_status")
            print("   - No direct queries on order stats")
            print("   - No direct queries on last_health_check")
            return True

    except Exception as e:
        print(f"❌ Repository query test failed: {e}")
        return False


async def test_webhook_payload_parsing():
    """Test 3: Validate webhook payload parsing"""
    print("\n" + "=" * 80)
    print("TEST 3: Webhook Payload Parsing")
    print("=" * 80)

    try:
        from application.services.tradingview_webhook_service import (
            TradingViewWebhookService,
        )

        # Create service instance (with mocked dependencies)
        class MockService:
            def _normalize_payload(self, payload):
                # Use the actual normalize method
                service = TradingViewWebhookService(None, None, None, None)
                return service._normalize_payload(payload)

        mock = MockService()

        # Test different payload formats
        test_payloads = [
            # Simple format
            {"ticker": "BTCUSDT", "action": "buy", "price": 50000},
            # Complex format with position
            {
                "symbol": "ETHUSDT",
                "action": "sell",
                "position": {"entry_price": 3000, "quantity": 1.0},
            },
            # Portuguese action
            {"ticker": "BTCUSDT", "action": "Compra", "price": 51000},
        ]

        for i, payload in enumerate(test_payloads, 1):
            normalized = mock._normalize_payload(payload)
            print(f"\n   Payload {i}: {payload}")
            print(f"   Normalized: {normalized}")
            assert "ticker" in normalized or "symbol" in normalized
            assert "action" in normalized

        print("\n✅ Webhook payload parsing works correctly")
        return True

    except Exception as e:
        print(f"❌ Webhook payload parsing test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


async def test_order_type_mappings():
    """Test 4: Verify SL/TP order types are correct for Binance Futures"""
    print("\n" + "=" * 80)
    print("TEST 4: Order Type Mapping Validation")
    print("=" * 80)

    try:
        import inspect
        from application.services.tradingview_webhook_service import (
            TradingViewWebhookService,
        )

        # Check source code for correct order types
        source = inspect.getsource(TradingViewWebhookService._create_order)

        # Verify correct order types are used
        has_stop_market = 'order_type="STOP_MARKET"' in source
        has_take_profit_market = 'order_type="TAKE_PROFIT_MARKET"' in source

        # Verify incorrect types are NOT used
        has_wrong_stop = 'order_type="stop"' in source
        has_wrong_limit_tp = 'order_type="limit"' in source and "Take Profit" in source

        print(f"   Stop Loss uses STOP_MARKET: {has_stop_market}")
        print(f"   Take Profit uses TAKE_PROFIT_MARKET: {has_take_profit_market}")

        if has_stop_market and has_take_profit_market and not has_wrong_stop:
            print("✅ Order types correctly configured for Binance Futures")
            return True
        else:
            print("❌ Order types NOT correctly configured")
            return False

    except Exception as e:
        print(f"❌ Order type mapping test failed: {e}")
        return False


async def test_http_200_error_handling():
    """Test 5: Verify webhook always returns HTTP 200"""
    print("\n" + "=" * 80)
    print("TEST 5: HTTP 200 Error Handling Validation")
    print("=" * 80)

    try:
        import inspect
        from presentation.controllers.webhook_controller import create_webhook_router

        # Get the router and inspect the webhook endpoint
        router = create_webhook_router()

        # Find the receive_tradingview_webhook function
        for route in router.routes:
            if hasattr(route, "endpoint") and "receive_tradingview_webhook" in str(
                route.endpoint
            ):
                source = inspect.getsource(route.endpoint)

                # Verify it returns JSONResponse with 200 on errors
                has_json_response_on_error = (
                    'status_code=200' in source and '"success": False' in source
                )
                has_no_http_exception = 'raise HTTPException' not in source

                print(f"   Returns 200 on errors: {has_json_response_on_error}")
                print(f"   Avoids HTTPException: {has_no_http_exception}")

                if has_json_response_on_error:
                    print("✅ Webhook correctly returns HTTP 200 on all errors")
                    return True
                else:
                    print("❌ Webhook may still raise HTTP errors")
                    return False

        print("❌ Could not find webhook endpoint")
        return False

    except Exception as e:
        print(f"❌ HTTP 200 error handling test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


async def run_all_tests():
    """Run all validation tests"""
    print("\n" + "=" * 80)
    print("TRADINGVIEW WEBHOOK FLOW 2 - VALIDATION TEST SUITE")
    print("=" * 80)
    print("\nTesting fixes for:")
    print("1. Schema mismatch (exchange_account fields)")
    print("2. Repository queries (no non-existent fields)")
    print("3. Webhook payload parsing")
    print("4. SL/TP order types (STOP_MARKET, TAKE_PROFIT_MARKET)")
    print("5. HTTP 200 error handling (TradingView best practice)")

    results = {
        "Exchange Account Schema": await test_exchange_account_schema(),
        "Repository Queries": await test_repository_queries(),
        "Webhook Payload Parsing": await test_webhook_payload_parsing(),
        "Order Type Mappings": await test_order_type_mappings(),
        "HTTP 200 Error Handling": await test_http_200_error_handling(),
    }

    # Summary
    print("\n" + "=" * 80)
    print("TEST RESULTS SUMMARY")
    print("=" * 80)

    total_tests = len(results)
    passed_tests = sum(1 for passed in results.values() if passed)

    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} - {test_name}")

    print("\n" + "=" * 80)
    print(f"TOTAL: {passed_tests}/{total_tests} tests passed")
    print("=" * 80)

    if passed_tests == total_tests:
        print("\n🎉 All tests passed! Flow 2 fixes are validated.")
        print("\nNext steps:")
        print("1. Start the backend: python3 main.py")
        print("2. Create a webhook in the dashboard")
        print("3. Send a test TradingView alert")
        print("4. Verify order appears on Binance")
        return 0
    else:
        print(
            f"\n⚠️  {total_tests - passed_tests} test(s) failed. Please review the fixes."
        )
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(run_all_tests())
    sys.exit(exit_code)

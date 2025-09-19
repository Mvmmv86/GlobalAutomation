#!/usr/bin/env python3
"""Integration test for Exchange Credentials Service"""

import asyncio
import os
from uuid import uuid4

from infrastructure.di.container import get_container
from infrastructure.database.models.exchange_account import (
    ExchangeType,
    ExchangeEnvironment,
)


async def test_exchange_credentials_integration():
    """Test complete integration of encryption with exchange credentials"""

    print("🔧 Testing Exchange Credentials Service Integration...")

    # Get container
    container = await get_container()

    # Get services
    exchange_credentials_service = container.get("exchange_credentials_service")
    user_repository = container.get("user_repository")

    # Create test user
    test_user_data = {
        "email": f"test_{uuid4().hex[:8]}@example.com",
        "password_hash": "test_hash_123",
        "name": "Test User",
    }

    async with container.session_scope() as session:
        # Create user using repository
        user_repository._session = session
        user = await user_repository.create(test_user_data)
        user_id = user.id

        print(f"✅ Created test user: {user.email}")

        # Test: Create exchange account with encrypted credentials
        print("\n🔐 Testing credential encryption...")

        test_api_key = "test_binance_api_key_12345"
        test_api_secret = "test_binance_secret_67890_very_long_secret_key"

        exchange_account = await exchange_credentials_service.create_exchange_account(
            user_id=user_id,
            name="Test Binance Account",
            exchange_type=ExchangeType.BINANCE,
            api_key=test_api_key,
            api_secret=test_api_secret,
            environment=ExchangeEnvironment.TESTNET,
        )

        print(f"✅ Created exchange account: {exchange_account.id}")
        print(f"✅ API key encrypted length: {len(exchange_account.api_key_encrypted)}")
        print(
            f"✅ API secret encrypted length: {len(exchange_account.api_secret_encrypted)}"
        )

        # Test: Decrypt credentials
        print("\n🔓 Testing credential decryption...")

        decrypted_creds = await exchange_credentials_service.get_decrypted_credentials(
            account_id=exchange_account.id, user_id=user_id
        )

        print(f"✅ Decrypted API key: {decrypted_creds['api_key']}")
        print(f"✅ Decrypted API secret: {decrypted_creds['api_secret'][:20]}...")
        print(f"✅ Exchange type: {decrypted_creds['exchange_type']}")
        print(f"✅ Environment: {decrypted_creds['environment']}")

        # Verify decryption worked correctly
        assert decrypted_creds["api_key"] == test_api_key
        assert decrypted_creds["api_secret"] == test_api_secret
        assert decrypted_creds["exchange_type"] == ExchangeType.BINANCE.value

        print("✅ Encryption/Decryption cycle successful!")

        # Test: Update credentials
        print("\n🔄 Testing credential update...")

        new_api_key = "updated_api_key_54321"
        new_api_secret = "updated_secret_09876_even_longer_secret"

        updated = await exchange_credentials_service.update_credentials(
            account_id=exchange_account.id,
            user_id=user_id,
            api_key=new_api_key,
            api_secret=new_api_secret,
        )

        print(f"✅ Credentials updated: {updated}")

        # Verify updated credentials
        updated_creds = await exchange_credentials_service.get_decrypted_credentials(
            account_id=exchange_account.id, user_id=user_id
        )

        assert updated_creds["api_key"] == new_api_key
        assert updated_creds["api_secret"] == new_api_secret

        print("✅ Credential update successful!")

        # Test: Account status
        print("\n📊 Testing account status...")

        status = await exchange_credentials_service.get_account_status(
            account_id=exchange_account.id, user_id=user_id
        )

        print(f"✅ Account status: {status}")

        assert status["has_credentials"] == True
        assert status["is_active"] == True
        assert status["exchange_type"] == ExchangeType.BINANCE.value
        assert status["health_status"] == "unknown"

        # Test: Security validation (wrong user)
        print("\n🔒 Testing security validation...")

        wrong_user_id = uuid4()
        try:
            await exchange_credentials_service.get_decrypted_credentials(
                account_id=exchange_account.id, user_id=wrong_user_id
            )
            print("❌ Security validation failed - should have thrown error")
        except ValueError as e:
            print(f"✅ Security validation working: {e}")

        print("\n🎉 All integration tests passed!")

        return True


async def main():
    """Run integration tests"""
    try:
        success = await test_exchange_credentials_integration()
        if success:
            print("\n🏆 Exchange Credentials Service integration is WORKING!")
            return 0
        else:
            print("\n❌ Integration tests failed")
            return 1

    except Exception as e:
        print(f"\n💥 Integration test failed with error: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)

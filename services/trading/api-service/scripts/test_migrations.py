#!/usr/bin/env python3
"""Test script for validating migrations structure"""

import os
import sys
import importlib.util
from pathlib import Path

# Add parent directory to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_migration_structure():
    """Test migration file structure"""
    print("🧪 Testing migration structure...")

    # Check if migration file exists
    migration_file = Path("migrations/versions/001_initial_schema.py")
    assert migration_file.exists(), "❌ Migration file not found"
    print("✅ Migration file exists")

    # Check if alembic.ini exists
    alembic_ini = Path("alembic.ini")
    assert alembic_ini.exists(), "❌ alembic.ini not found"
    print("✅ alembic.ini exists")

    # Check if env.py exists
    env_py = Path("migrations/env.py")
    assert env_py.exists(), "❌ migrations/env.py not found"
    print("✅ migrations/env.py exists")

    return True


def test_migration_content():
    """Test migration content"""
    print("\n🧪 Testing migration content...")

    # Load migration file
    spec = importlib.util.spec_from_file_location(
        "initial_migration", "migrations/versions/001_initial_schema.py"
    )
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)

    # Check revision info
    assert hasattr(migration, "revision"), "❌ Missing revision"
    assert hasattr(migration, "down_revision"), "❌ Missing down_revision"
    assert hasattr(migration, "upgrade"), "❌ Missing upgrade function"
    assert hasattr(migration, "downgrade"), "❌ Missing downgrade function"
    print("✅ Migration has required attributes")

    # Check revision values
    assert migration.revision == "001", "❌ Incorrect revision"
    assert migration.down_revision is None, "❌ Incorrect down_revision"
    print("✅ Migration revision values correct")

    return True


def test_model_imports():
    """Test if all models can be imported"""
    print("\n🧪 Testing model imports...")

    try:
        from infrastructure.database.models.base import Base
        from infrastructure.database.models.user import User, APIKey
        from infrastructure.database.models.exchange_account import ExchangeAccount
        from infrastructure.database.models.webhook import Webhook, WebhookDelivery
        from infrastructure.database.models.order import Order
        from infrastructure.database.models.position import Position

        print("✅ All models imported successfully")

        # Test model metadata
        tables = Base.metadata.tables
        expected_tables = {
            "users",
            "api_keys",
            "exchange_accounts",
            "webhooks",
            "webhook_deliveries",
            "orders",
            "positions",
        }

        assert expected_tables.issubset(
            set(tables.keys())
        ), "❌ Missing tables in metadata"
        print(f"✅ All {len(expected_tables)} tables found in metadata")

        return True

    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False


def test_seed_script():
    """Test seed script structure"""
    print("\n🧪 Testing seed script...")

    seed_file = Path("scripts/seed_data.py")
    assert seed_file.exists(), "❌ Seed script not found"
    print("✅ Seed script exists")

    # Check if script is executable
    assert os.access(seed_file, os.X_OK), "❌ Seed script not executable"
    print("✅ Seed script is executable")

    return True


def test_alembic_config():
    """Test alembic configuration"""
    print("\n🧪 Testing alembic configuration...")

    # Read alembic.ini
    with open("alembic.ini", "r") as f:
        config_content = f.read()

    # Check for required sections
    required_sections = ["[alembic]", "[dev]", "[test]", "[prod]"]
    for section in required_sections:
        assert section in config_content, f"❌ Missing section {section}"
    print("✅ All required sections found in alembic.ini")

    # Check for migrations directory
    assert (
        "script_location = migrations" in config_content
    ), "❌ Incorrect script location"
    print("✅ Script location configured correctly")

    return True


def main():
    """Run all tests"""
    print("🚀 Running migration tests...\n")

    tests = [
        test_migration_structure,
        test_migration_content,
        test_model_imports,
        test_seed_script,
        test_alembic_config,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"❌ Test {test.__name__} failed: {e}")
            failed += 1

    print("\n📊 Test Results:")
    print(f"   ✅ Passed: {passed}")
    print(f"   ❌ Failed: {failed}")

    if failed == 0:
        print("\n🎉 All migration tests passed!")
        print("✅ Migration system is ready for use")
        return True
    else:
        print(f"\n💥 {failed} test(s) failed")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

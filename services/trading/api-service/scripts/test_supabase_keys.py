#!/usr/bin/env python3
"""Test different Supabase API key formats"""

import asyncio
import httpx

# Configuration
SUPABASE_URL = "https://zmdqmrugotfftxvrwdsd.supabase.co"
SERVICE_KEY = "sbp_v0_8f824c4d953ec4b1a907219a0f389a071934f0d8"


async def test_key_formats():
    """Test different API key authentication methods"""

    print("🔑 Testing Supabase API key formats...")

    # Test configurations
    test_configs = [
        {
            "name": "Service Key in Authorization header",
            "headers": {
                "Authorization": f"Bearer {SERVICE_KEY}",
                "Content-Type": "application/json",
            },
        },
        {
            "name": "Service Key in apikey header",
            "headers": {"apikey": SERVICE_KEY, "Content-Type": "application/json"},
        },
        {
            "name": "Both Authorization and apikey headers",
            "headers": {
                "Authorization": f"Bearer {SERVICE_KEY}",
                "apikey": SERVICE_KEY,
                "Content-Type": "application/json",
            },
        },
    ]

    async with httpx.AsyncClient() as client:
        for config in test_configs:
            try:
                print(f"\n🧪 Testing: {config['name']}")

                # Test basic connection
                response = await client.get(
                    f"{SUPABASE_URL}/rest/v1/", headers=config["headers"], timeout=10.0
                )

                print(f"   Status: {response.status_code}")

                if response.status_code == 200:
                    print("   ✅ SUCCESS!")

                    # Try to get schema info
                    schema_response = await client.get(
                        f"{SUPABASE_URL}/rest/v1/?select=*", headers=config["headers"]
                    )
                    print(f"   Schema query: {schema_response.status_code}")

                    return config["headers"]

                elif response.status_code == 401:
                    print("   ❌ Unauthorized")
                elif response.status_code == 404:
                    print("   ❌ Not Found")
                else:
                    print(f"   ❌ Error: {response.text[:100]}")

            except Exception as e:
                print(f"   ❌ Exception: {e}")

    print("\n❌ No working authentication method found")
    print("\n🔍 Please verify:")
    print("1. Service key is correct")
    print("2. Key has admin privileges")
    print("3. Project URL is correct")

    return None


async def test_public_endpoints():
    """Test if we can access any public endpoints"""
    print("\n🌐 Testing public endpoints...")

    async with httpx.AsyncClient() as client:
        try:
            # Test public health endpoint
            response = await client.get(f"{SUPABASE_URL}/rest/v1/", timeout=10.0)
            print(f"Public endpoint status: {response.status_code}")

            if response.status_code == 200:
                print("✅ Supabase is reachable")
            else:
                print(f"Response: {response.text[:200]}")

        except Exception as e:
            print(f"❌ Cannot reach Supabase: {e}")


async def main():
    """Main test function"""
    print("🚀 SUPABASE API KEY TESTING")
    print("=" * 40)

    await test_public_endpoints()
    working_headers = await test_key_formats()

    if working_headers:
        print("\n🎉 Found working authentication!")
        print("Headers to use:", working_headers)
    else:
        print("\n💡 Suggestions:")
        print("1. Check if service key starts with 'eyJ' (JWT format)")
        print("2. Go to Settings > API in Supabase dashboard")
        print("3. Copy the 'service_role' key (not anon key)")
        print("4. Make sure RLS is disabled for testing")


if __name__ == "__main__":
    asyncio.run(main())

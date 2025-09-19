#!/usr/bin/env python3
"""Focused Rate Limiting Test"""

import requests
import time
import json
from datetime import datetime

BASE_URL = "http://localhost:8000"

def clear_rate_limit():
    """Wait for rate limiting to clear"""
    print("🕐 Waiting for rate limits to clear...")
    time.sleep(10)  # Wait 10 seconds for rate limits to reset

def test_rate_limiting_detailed():
    """Test rate limiting with detailed analysis"""
    print("🔍 DETAILED RATE LIMITING TEST")
    print("=" * 60)
    
    # Clear any existing rate limits first
    clear_rate_limit()
    
    url = f"{BASE_URL}/api/v1/auth/login"
    
    print(f"Testing endpoint: {url}")
    print(f"Expected limit: 10 requests per 60 seconds")
    print(f"Expected behavior: Block after 10 attempts with 429 status")
    
    results = []
    
    # Make 15 requests to test the limit (10 allowed + 5 blocked)
    for i in range(1, 16):
        print(f"\n--- Attempt {i} ---")
        
        payload = {
            "email": f"ratelimit{i}@example.com",
            "password": "wrongpassword123"
        }
        
        start_time = time.time()
        try:
            response = requests.post(url, json=payload, timeout=10)
            end_time = time.time()
            response_time = round((end_time - start_time) * 1000, 2)
            
            result = {
                'attempt': i,
                'status_code': response.status_code,
                'response_time_ms': response_time,
                'timestamp': datetime.now().strftime('%H:%M:%S'),
                'headers': {}
            }
            
            # Capture rate limiting headers
            rate_headers = [
                'x-ratelimit-remaining',
                'x-ratelimit-reset', 
                'x-ratelimit-tokens',
                'x-ratelimit-error',
                'retry-after'
            ]
            
            for header in rate_headers:
                if header in response.headers:
                    result['headers'][header] = response.headers[header]
            
            # Parse response
            try:
                result['response'] = response.json()
            except:
                result['response'] = response.text[:100]
            
            results.append(result)
            
            # Display result
            print(f"  Status: {response.status_code}")
            print(f"  Time: {response_time}ms")
            
            if response.status_code == 401:
                print("  📝 Expected: Invalid credentials (401)")
                remaining = response.headers.get('x-ratelimit-remaining', 'N/A')
                print(f"  🔢 Remaining requests: {remaining}")
                
            elif response.status_code == 429:
                print("  🚫 RATE LIMITED! (429)")
                retry_after = response.headers.get('retry-after', 'N/A')
                error_msg = response.json().get('message', 'No message')
                print(f"  ⏰ Retry after: {retry_after}s")
                print(f"  💬 Message: {error_msg}")
                
                # This is what we expect after hitting the limit
                if i >= 10:  # Should be rate limited after 10 attempts
                    print("  ✅ Rate limiting working as expected!")
                else:
                    print("  ⚠️ Rate limited earlier than expected")
                break
                
            elif response.status_code == 500:
                print("  ❌ Server error - check logs")
                print(f"  Response: {result['response']}")
            
            else:
                print(f"  ❓ Unexpected status: {response.status_code}")
            
        except requests.exceptions.Timeout:
            print(f"  ⏰ Request timeout after 10s")
            break
        except Exception as e:
            print(f"  ❌ Request failed: {e}")
            break
        
        # Small delay between requests
        time.sleep(0.2)
    
    # Analysis
    print("\n" + "=" * 60)
    print("📊 RATE LIMITING ANALYSIS")
    print("=" * 60)
    
    successful_requests = [r for r in results if r['status_code'] == 401]
    blocked_requests = [r for r in results if r['status_code'] == 429]
    error_requests = [r for r in results if r['status_code'] == 500]
    
    print(f"✅ Successful requests (401 - expected): {len(successful_requests)}")
    print(f"🚫 Rate limited requests (429): {len(blocked_requests)}")
    print(f"❌ Error requests (500): {len(error_requests)}")
    
    if len(successful_requests) >= 5 and len(blocked_requests) >= 1:
        print("\n🎉 RATE LIMITING IS WORKING CORRECTLY!")
        print(f"   - Allowed {len(successful_requests)} requests before blocking")
        print(f"   - Correctly blocked with 429 status")
        return True
    else:
        print("\n⚠️ RATE LIMITING NEEDS ADJUSTMENT")
        if len(error_requests) > 0:
            print("   - Check server logs for 500 errors")
        if len(blocked_requests) == 0:
            print("   - Rate limiting not triggered")
        return False

def test_rate_limit_headers():
    """Test that rate limiting headers are present"""
    print("\n🔍 TESTING RATE LIMIT HEADERS")
    print("=" * 50)
    
    # Make a single request to check headers
    response = requests.post(f"{BASE_URL}/api/v1/auth/login", json={
        "email": "headertest@example.com",
        "password": "wrong"
    })
    
    expected_headers = [
        'x-ratelimit-remaining',
        'x-ratelimit-reset'
    ]
    
    found_headers = 0
    for header in expected_headers:
        if header in response.headers:
            print(f"  ✅ {header}: {response.headers[header]}")
            found_headers += 1
        else:
            print(f"  ❌ {header}: Missing")
    
    return found_headers > 0

def main():
    """Run focused rate limiting tests"""
    print("🛡️ FOCUSED RATE LIMITING TEST SUITE")
    print("=" * 60)
    print(f"Target URL: {BASE_URL}")
    print(f"Test started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Test 1: Rate limiting functionality
    rate_limit_works = test_rate_limiting_detailed()
    
    # Test 2: Rate limiting headers
    headers_present = test_rate_limit_headers()
    
    # Final summary
    print("\n" + "=" * 60)
    print("🏁 FINAL SUMMARY")
    print("=" * 60)
    
    if rate_limit_works:
        print("✅ Rate limiting mechanism: WORKING")
    else:
        print("❌ Rate limiting mechanism: NEEDS FIX")
    
    if headers_present:
        print("✅ Rate limiting headers: PRESENT")
    else:
        print("❌ Rate limiting headers: MISSING")
    
    overall_success = rate_limit_works and headers_present
    
    if overall_success:
        print("\n🎉 RATE LIMITING FULLY FUNCTIONAL!")
    else:
        print("\n⚠️ RATE LIMITING NEEDS ATTENTION")
    
    return overall_success

if __name__ == "__main__":
    main()
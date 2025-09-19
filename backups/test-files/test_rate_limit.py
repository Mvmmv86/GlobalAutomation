#!/usr/bin/env python3
"""Test rate limiting functionality"""

import requests
import time

def test_rate_limiting():
    """Test login endpoint rate limiting"""
    url = "http://localhost:8000/api/v1/auth/login"
    headers = {"Content-Type": "application/json"}
    
    print("🔍 Testing Rate Limiting on /api/v1/auth/login")
    print("=" * 50)
    
    # Test with invalid credentials to trigger rate limiting
    for i in range(1, 8):
        payload = {"email": "hacker@test.com", "password": "wrong"}
        
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=5)
            print(f"Attempt {i}: Status {response.status_code}")
            
            if response.status_code == 429:
                print(f"  ✅ Rate limit activated!")
                print(f"  Message: {response.json().get('message', '')}")
                if 'retry-after' in response.headers:
                    print(f"  Retry-After: {response.headers['retry-after']} seconds")
                break
            elif response.status_code == 401:
                print(f"  ❌ Invalid credentials (expected)")
                # Check rate limit headers
                if 'x-ratelimit-remaining' in response.headers:
                    print(f"  Remaining: {response.headers['x-ratelimit-remaining']}")
            
        except Exception as e:
            print(f"Attempt {i}: Error - {e}")
        
        time.sleep(0.1)  # Small delay between requests
    
    print("\n" + "=" * 50)
    print("✅ Rate limiting test complete")

if __name__ == "__main__":
    test_rate_limiting()
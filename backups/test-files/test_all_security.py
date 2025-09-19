#!/usr/bin/env python3
"""Complete security features test suite"""

import requests
import time
import json

BASE_URL = "http://localhost:8000"

def test_feature(name, test_func):
    """Helper to run and report test results"""
    print(f"\n{'='*60}")
    print(f"🔍 Testing: {name}")
    print('='*60)
    try:
        result = test_func()
        if result:
            print(f"✅ {name} - PASSED")
        else:
            print(f"❌ {name} - FAILED")
        return result
    except Exception as e:
        print(f"❌ {name} - ERROR: {e}")
        return False

def test_security_headers():
    """Test security headers are present"""
    response = requests.get(f"{BASE_URL}/api/v1/orders")
    headers = response.headers
    
    required_headers = [
        'content-security-policy',
        'x-content-type-options',
        'x-frame-options',
        'x-xss-protection',
        'referrer-policy',
        'permissions-policy'
    ]
    
    for header in required_headers:
        if header in headers:
            print(f"  ✓ {header}: {headers[header][:50]}...")
        else:
            print(f"  ✗ {header}: MISSING")
            return False
    
    return True

def test_rate_limiting():
    """Test rate limiting on login endpoint"""
    url = f"{BASE_URL}/api/v1/auth/login"
    
    # Clear any existing rate limits by waiting
    time.sleep(1)
    
    for i in range(7):
        response = requests.post(url, json={
            "email": f"ratelimit{i}@test.com",
            "password": "wrong"
        })
        
        if response.status_code == 429:
            print(f"  ✓ Rate limit triggered after {i} attempts")
            print(f"  ✓ Message: {response.json().get('message', '')}")
            return True
        
        if 'x-ratelimit-remaining' in response.headers:
            remaining = response.headers['x-ratelimit-remaining']
            print(f"  Attempt {i+1}: Remaining: {remaining}")
    
    return False

def test_jwt_refresh_token():
    """Test JWT refresh token rotation"""
    # First login to get tokens
    login_response = requests.post(f"{BASE_URL}/api/v1/auth/login", json={
        "email": "test@test.com",
        "password": "123456"
    })
    
    if login_response.status_code != 200:
        print(f"  ✗ Login failed: {login_response.status_code}")
        return False
    
    tokens = login_response.json()
    refresh_token = tokens.get('refresh_token')
    
    if not refresh_token:
        print("  ✗ No refresh token received")
        return False
    
    print(f"  ✓ Initial login successful")
    print(f"  ✓ Access token expires in: {tokens.get('expires_in')} seconds")
    
    # Test refresh
    refresh_response = requests.post(f"{BASE_URL}/api/v1/auth/refresh", json={
        "refresh_token": refresh_token
    })
    
    if refresh_response.status_code == 200:
        new_tokens = refresh_response.json()
        new_refresh = new_tokens.get('refresh_token')
        
        if new_refresh and new_refresh != refresh_token:
            print(f"  ✓ Token rotation successful - new refresh token issued")
            return True
        else:
            print(f"  ✗ Token rotation failed - same token returned")
            return False
    else:
        print(f"  ✗ Refresh failed: {refresh_response.status_code}")
        return False

def test_input_validation():
    """Test input validation and SQL injection protection"""
    # Test SQL injection attempt
    malicious_payloads = [
        {"email": "admin' OR '1'='1", "password": "password"},
        {"email": "test@test.com", "password": "'; DROP TABLE users; --"},
        {"email": "<script>alert('xss')</script>", "password": "test"}
    ]
    
    for payload in malicious_payloads:
        response = requests.post(f"{BASE_URL}/api/v1/auth/login", json=payload)
        
        if response.status_code in [400, 401]:
            print(f"  ✓ Blocked malicious input: {payload['email'][:30]}...")
        else:
            print(f"  ✗ Accepted dangerous input: {payload['email']}")
            return False
    
    return True

def test_logout():
    """Test logout functionality"""
    # First login
    login_response = requests.post(f"{BASE_URL}/api/v1/auth/login", json={
        "email": "test@test.com",
        "password": "123456"
    })
    
    if login_response.status_code != 200:
        print(f"  ✗ Login failed")
        return False
    
    tokens = login_response.json()
    access_token = tokens.get('access_token')
    
    # Test logout
    logout_response = requests.post(
        f"{BASE_URL}/api/v1/auth/logout",
        headers={"Authorization": f"Bearer {access_token}"},
        json={"refresh_token": tokens.get('refresh_token')}
    )
    
    if logout_response.status_code == 200:
        print(f"  ✓ Logout successful")
        return True
    else:
        print(f"  ✗ Logout failed: {logout_response.status_code}")
        return False

def test_auth_me_endpoint():
    """Test /auth/me endpoint with JWT validation"""
    # Login first
    login_response = requests.post(f"{BASE_URL}/api/v1/auth/login", json={
        "email": "test@test.com",
        "password": "123456"
    })
    
    if login_response.status_code != 200:
        print(f"  ✗ Login failed")
        return False
    
    access_token = login_response.json().get('access_token')
    
    # Test /auth/me
    me_response = requests.get(
        f"{BASE_URL}/api/v1/auth/me",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    
    if me_response.status_code == 200:
        user_data = me_response.json()
        print(f"  ✓ User data retrieved: {user_data.get('email')}")
        return True
    else:
        print(f"  ✗ Failed to get user data: {me_response.status_code}")
        return False

def main():
    """Run all security tests"""
    print("\n" + "="*60)
    print("🛡️  COMPLETE SECURITY TEST SUITE")
    print("="*60)
    
    tests = [
        ("Security Headers", test_security_headers),
        ("Rate Limiting", test_rate_limiting),
        ("JWT Refresh Token Rotation", test_jwt_refresh_token),
        ("Input Validation & SQL Protection", test_input_validation),
        ("Logout Functionality", test_logout),
        ("JWT Authentication (/auth/me)", test_auth_me_endpoint),
    ]
    
    results = []
    for name, test_func in tests:
        results.append(test_feature(name, test_func))
        time.sleep(0.5)  # Small delay between tests
    
    # Summary
    print("\n" + "="*60)
    print("📊 TEST SUMMARY")
    print("="*60)
    
    passed = sum(results)
    total = len(results)
    
    for i, (name, _) in enumerate(tests):
        status = "✅ PASSED" if results[i] else "❌ FAILED"
        print(f"  {name}: {status}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 ALL SECURITY FEATURES WORKING CORRECTLY!")
    else:
        print(f"\n⚠️ {total - passed} tests failed. Review implementation.")

if __name__ == "__main__":
    main()
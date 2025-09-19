#!/usr/bin/env python3
"""Individual security component tests"""

import requests
import time
import json

BASE_URL = "http://localhost:8000"

def test_security_headers():
    """Test security headers are present"""
    print("🔍 Testing Security Headers")
    print("=" * 50)
    
    response = requests.get(f"{BASE_URL}/api/v1/orders")
    headers = response.headers
    
    required_headers = {
        'content-security-policy': 'CSP header',
        'x-content-type-options': 'Content type protection',
        'x-frame-options': 'Frame protection',
        'x-xss-protection': 'XSS protection',
        'referrer-policy': 'Referrer policy',
        'permissions-policy': 'Permissions policy'
    }
    
    all_present = True
    for header, description in required_headers.items():
        if header in headers:
            print(f"  ✅ {description}: Present")
        else:
            print(f"  ❌ {description}: Missing")
            all_present = False
    
    return all_present

def test_login_with_correct_credentials():
    """Test login with correct credentials"""
    print("\n🔍 Testing Login with Correct Credentials")
    print("=" * 50)
    
    # Wait for any rate limiting to clear
    time.sleep(2)
    
    response = requests.post(f"{BASE_URL}/api/v1/auth/login", json={
        "email": "test@test.com",
        "password": "123456"
    })
    
    if response.status_code == 200:
        print("  ✅ Login successful")
        data = response.json()
        if 'access_token' in data and 'refresh_token' in data:
            print(f"  ✅ Received access token (expires in {data.get('expires_in', 'unknown')}s)")
            print("  ✅ Received refresh token")
            return True, data
        else:
            print("  ❌ Missing tokens in response")
    elif response.status_code == 429:
        print("  ⚠️ Rate limited - this is expected behavior")
        return None, None
    else:
        print(f"  ❌ Login failed with status {response.status_code}")
        try:
            print(f"  Error: {response.json()}")
        except:
            print(f"  Raw response: {response.text}")
    
    return False, None

def test_jwt_me_endpoint(access_token):
    """Test /auth/me endpoint with valid token"""
    print("\n🔍 Testing JWT Authentication (/auth/me)")
    print("=" * 50)
    
    if not access_token:
        print("  ⚠️ No access token available")
        return False
    
    response = requests.get(
        f"{BASE_URL}/api/v1/auth/me",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    
    if response.status_code == 200:
        print("  ✅ JWT authentication working")
        user_data = response.json()
        print(f"  ✅ User data: {user_data.get('email', 'unknown')}")
        return True
    else:
        print(f"  ❌ JWT auth failed: {response.status_code}")
        return False

def test_refresh_token(refresh_token):
    """Test refresh token functionality"""
    print("\n🔍 Testing Refresh Token")
    print("=" * 50)
    
    if not refresh_token:
        print("  ⚠️ No refresh token available")
        return False
    
    response = requests.post(f"{BASE_URL}/api/v1/auth/refresh", json={
        "refresh_token": refresh_token
    })
    
    if response.status_code == 200:
        print("  ✅ Refresh token working")
        data = response.json()
        new_access = data.get('access_token')
        new_refresh = data.get('refresh_token')
        
        if new_access and new_refresh and new_refresh != refresh_token:
            print("  ✅ Token rotation successful")
            return True
        else:
            print("  ❌ Token rotation failed")
            return False
    else:
        print(f"  ❌ Refresh failed: {response.status_code}")
        return False

def test_password_validation():
    """Test password validation component"""
    print("\n🔍 Testing Password Validation")
    print("=" * 50)
    
    try:
        import sys
        sys.path.append('.')
        from infrastructure.security.password_validator import password_validator
        
        test_passwords = [
            ("123456", False, "Common password"),
            ("password", False, "Common password"),
            ("Test@1234", True, "Good password"),
            ("MyS3cur3P@ssw0rd!", True, "Strong password")
        ]
        
        all_passed = True
        for password, expected_valid, description in test_passwords:
            result = password_validator.validate_password(password)
            passed = result.is_valid == expected_valid
            
            status = "✅" if passed else "❌"
            print(f"  {status} {description}: {result.strength.name} (Score: {result.score}/10)")
            
            if not passed:
                all_passed = False
        
        return all_passed
        
    except Exception as e:
        print(f"  ❌ Password validation test failed: {e}")
        return False

def main():
    """Run individual security tests"""
    print("🛡️ INDIVIDUAL SECURITY COMPONENT TESTS")
    print("=" * 60)
    
    results = {}
    
    # Test 1: Security Headers
    results['headers'] = test_security_headers()
    
    # Test 2: Login
    login_success, login_data = test_login_with_correct_credentials()
    results['login'] = login_success
    
    access_token = None
    refresh_token = None
    if login_data:
        access_token = login_data.get('access_token')
        refresh_token = login_data.get('refresh_token')
    
    # Test 3: JWT /auth/me (only if login successful)
    if access_token:
        results['jwt_auth'] = test_jwt_me_endpoint(access_token)
    else:
        results['jwt_auth'] = None
    
    # Test 4: Refresh Token (only if available)
    if refresh_token:
        results['refresh'] = test_refresh_token(refresh_token)
    else:
        results['refresh'] = None
    
    # Test 5: Password Validation
    results['password_validation'] = test_password_validation()
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 INDIVIDUAL TEST RESULTS")
    print("=" * 60)
    
    for test_name, result in results.items():
        if result is True:
            print(f"  ✅ {test_name.replace('_', ' ').title()}: PASSED")
        elif result is False:
            print(f"  ❌ {test_name.replace('_', ' ').title()}: FAILED")
        else:
            print(f"  ⚠️ {test_name.replace('_', ' ').title()}: SKIPPED")
    
    passed = sum(1 for r in results.values() if r is True)
    total = len([r for r in results.values() if r is not None])
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tested components are working!")
    else:
        print(f"\n⚠️ Some components need attention")

if __name__ == "__main__":
    main()
#!/usr/bin/env python3
"""Test account lockout functionality"""

import requests
import time

def test_account_lockout():
    """Test account lockout after failed login attempts"""
    url = "http://localhost:8000/api/v1/auth/login"
    headers = {"Content-Type": "application/json"}
    
    print("🔍 Testing Account Lockout")
    print("=" * 60)
    
    # Use the real test account to test lockout
    email = "test@test.com"
    
    # First, make 5 failed login attempts
    print(f"Testing lockout for account: {email}")
    print("\nPhase 1: Making failed login attempts...")
    
    for i in range(1, 6):
        payload = {"email": email, "password": "wrongpassword"}
        
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=5)
            print(f"  Attempt {i}: Status {response.status_code}")
            
            if response.status_code == 423:
                print(f"    ✅ Account locked!")
                data = response.json()
                print(f"    Message: {data.get('detail', '')}")
                break
            elif response.status_code == 401:
                print(f"    ❌ Invalid password (attempt {i}/5)")
            
        except Exception as e:
            print(f"  Attempt {i}: Error - {e}")
        
        time.sleep(0.1)
    
    # Try one more login to confirm lockout
    print("\nPhase 2: Confirming account is locked...")
    time.sleep(1)
    
    payload = {"email": email, "password": "123456"}  # Correct password
    response = requests.post(url, json=payload, headers=headers, timeout=5)
    
    if response.status_code == 423:
        print("  ✅ Account is locked even with correct password!")
        print(f"  Message: {response.json().get('detail', '')}")
    elif response.status_code == 200:
        print("  ⚠️ Account not locked - login succeeded")
    else:
        print(f"  Status: {response.status_code}")
    
    print("\n" + "=" * 60)
    print("✅ Account lockout test complete")
    print("\nNote: Account will remain locked for 30 minutes")
    print("To unlock: UPDATE users SET failed_login_attempts = 0, locked_until = NULL WHERE email = 'test@test.com';")

if __name__ == "__main__":
    test_account_lockout()
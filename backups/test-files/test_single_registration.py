#!/usr/bin/env python3
"""Single registration test"""

import requests
import time
import json

BASE_URL = "http://localhost:8000"

def test_one_registration():
    """Test single registration to avoid rate limiting"""
    
    print("⏳ Waiting for rate limits to clear...")
    time.sleep(10)
    
    print("🔍 Testing password validation with one example...")
    
    # Test weak password first
    print("\n1. Testing WEAK password: '123456'")
    response = requests.post(f"{BASE_URL}/api/v1/auth/register", json={
        "email": "weak@example.com",
        "password": "123456",
        "full_name": "Weak Password User"
    })
    
    print(f"Status: {response.status_code}")
    if response.status_code == 400:
        data = response.json()
        print(f"✅ Correctly rejected weak password")
        print(f"   Reason: {data.get('detail', '')}")
        if 'requirements' in data:
            print(f"   Shows requirements: ✅")
    else:
        print(f"❌ Unexpected response: {response.json()}")
        return
    
    # Wait a bit
    time.sleep(2)
    
    # Test strong password
    print("\n2. Testing STRONG password: 'MySecure@Password123!'")
    response = requests.post(f"{BASE_URL}/api/v1/auth/register", json={
        "email": "strong@example.com",
        "password": "MySecure@Password123!",
        "full_name": "Strong Password User"
    })
    
    print(f"Status: {response.status_code}")
    if response.status_code in [200, 201]:
        data = response.json()
        print(f"✅ Strong password accepted!")
        print(f"   Message: {data.get('message', '')}")
        if 'password_security' in data:
            security = data['password_security']
            print(f"   Strength: {security.get('strength', '')}")
            print(f"   Score: {security.get('score', '')}")
    elif response.status_code == 409:
        print(f"✅ Email already exists (that's OK)")
    else:
        print(f"❌ Unexpected response: {response.json()}")

if __name__ == "__main__":
    test_one_registration()
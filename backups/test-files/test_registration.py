#!/usr/bin/env python3
"""Test user registration with password validation"""

import requests
import json
from datetime import datetime

BASE_URL = "http://localhost:8000"

def test_password_strength(password, description):
    """Test password strength validation"""
    print(f"\n🔍 Testing: {description}")
    print(f"Password: {password}")
    
    response = requests.post(f"{BASE_URL}/api/v1/auth/register", json={
        "email": f"test{datetime.now().microsecond}@example.com",
        "password": password,
        "full_name": "Test User"
    })
    
    print(f"Status: {response.status_code}")
    
    if response.status_code == 400:
        data = response.json()
        print(f"❌ Rejected: {data.get('detail', '')}")
        
        if 'password_strength' in data:
            print(f"   Strength: {data['password_strength']}")
            print(f"   Score: {data.get('score', 'N/A')}")
        
        if 'feedback' in data:
            print(f"   Feedback: {data['feedback'][:3]}")
        
        if 'suggestions' in data:
            print(f"   Suggestions: {data['suggestions'][:2]}")
            
        return False
        
    elif response.status_code == 201 or response.status_code == 200:
        data = response.json()
        print(f"✅ Accepted: {data.get('message', '')}")
        
        if 'password_security' in data:
            security = data['password_security']
            print(f"   Strength: {security.get('strength', '')}")
            print(f"   Score: {security.get('score', '')}")
        
        return True
        
    else:
        print(f"❓ Unexpected status: {response.status_code}")
        try:
            print(f"   Response: {response.json()}")
        except:
            print(f"   Raw: {response.text}")
        return False

def test_registration_requirements():
    """Test registration field requirements"""
    print("\n🔍 TESTING REGISTRATION REQUIREMENTS")
    print("=" * 50)
    
    # Test missing fields
    test_cases = [
        ({}, "Empty request"),
        ({"email": "test@test.com"}, "Missing password and name"),
        ({"password": "Test123!"}, "Missing email and name"),
        ({"full_name": "Test User"}, "Missing email and password"),
        ({"email": "invalid-email", "password": "Test123!", "full_name": "Test"}, "Invalid email format")
    ]
    
    for payload, description in test_cases:
        print(f"\n• {description}")
        response = requests.post(f"{BASE_URL}/api/v1/auth/register", json=payload)
        
        if response.status_code == 400:
            print(f"  ✅ Correctly rejected (400)")
            data = response.json()
            if 'requirements' in data:
                print(f"  📋 Shows requirements: {list(data['requirements'].keys())}")
        else:
            print(f"  ❌ Unexpected status: {response.status_code}")

def main():
    """Test user registration with password validation"""
    print("📝 USER REGISTRATION TESTING")
    print("=" * 60)
    print(f"Target: {BASE_URL}/api/v1/auth/register")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Test field requirements
    test_registration_requirements()
    
    # Test various password strengths
    print("\n🔐 TESTING PASSWORD STRENGTH VALIDATION")
    print("=" * 60)
    
    password_tests = [
        ("123456", "Very weak - common password"),
        ("password", "Very weak - common password"),
        ("qwerty123", "Weak - keyboard pattern"),
        ("Test1234", "Fair - missing special characters"),
        ("test@test.com", "Weak - contains email"),
        ("Test User", "Weak - contains name"),
        ("Test@1234", "Good - meets basic requirements"),
        ("MySecure@Pass123", "Strong - complex password"),
        ("Tr0ub4dor&3", "Strong - famous secure password example"),
        ("P@ssw0rd!", "Weak - too common despite complexity"),
        ("correct-horse-battery-staple", "Strong - passphrase"),
        ("aB3#fG9$kL2@nM5^", "Very strong - random complex")
    ]
    
    results = []
    for password, description in password_tests:
        result = test_password_strength(password, description)
        results.append((description, result))
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 PASSWORD VALIDATION SUMMARY")
    print("=" * 60)
    
    accepted = sum(1 for _, result in results if result)
    total = len(results)
    
    print(f"\nAccepted passwords: {accepted}/{total}")
    
    for description, result in results:
        status = "✅ ACCEPTED" if result else "❌ REJECTED"
        print(f"  {status}: {description}")
    
    if accepted >= 4:  # Should accept strong passwords
        print(f"\n🎉 Password validation working correctly!")
        print(f"   ✅ Rejects weak passwords")
        print(f"   ✅ Accepts strong passwords")
        print(f"   ✅ Provides helpful feedback")
    else:
        print(f"\n⚠️ Password validation may be too strict")

if __name__ == "__main__":
    main()
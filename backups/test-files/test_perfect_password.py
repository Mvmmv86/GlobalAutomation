#!/usr/bin/env python3
"""Test with a really strong password"""

import requests
import time

BASE_URL = "http://localhost:8000"

def test_strong_password():
    """Test with a very strong password"""
    
    print("Testing with an excellent password...")
    time.sleep(2)
    
    response = requests.post(f"{BASE_URL}/api/v1/auth/register", json={
        "email": "excellent@example.com",
        "password": "K8$mN3@qR7*vL9&zX4#", 
        "full_name": "Excellent Password User"
    })
    
    print(f"Status: {response.status_code}")
    data = response.json()
    
    if response.status_code in [200, 201]:
        print("✅ Strong password accepted!")
        print(f"Message: {data.get('message', '')}")
        if 'password_security' in data:
            security = data['password_security']
            print(f"Strength: {security.get('strength', '')}")
            print(f"Score: {security.get('score', '')}")
    else:
        print("Password validation details:")
        print(f"Strength: {data.get('password_strength', '')}")
        print(f"Score: {data.get('score', '')}")
        print(f"Feedback: {data.get('feedback', [])}")
        print(f"Requirements: {data.get('requirements', {})}")

if __name__ == "__main__":
    test_strong_password()
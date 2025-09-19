#!/usr/bin/env python3
"""Test with truly strong password"""

import requests

BASE_URL = "http://localhost:8000"

def test_super_strong():
    """Test with a really strong password"""
    
    print("🔐 Testando senha SUPER FORTE...")
    
    # Using a very strong, random password
    response = requests.post(f"{BASE_URL}/api/v1/auth/register", json={
        "email": "superforte@test.com",
        "password": "Kx9#mP7$vL2&zR8!",  # No sequences, truly random
        "name": "Super Usuario"
    })
    
    print(f"Status: {response.status_code}")
    data = response.json()
    
    if response.status_code in [200, 201]:
        print(f"✅ SUCESSO! Conta criada!")
        print(f"   Email: {data.get('user', {}).get('email', 'N/A')}")
        print(f"   Força: {data.get('password_security', {}).get('strength', 'N/A')}")
        print(f"   Score: {data.get('password_security', {}).get('score', 'N/A')}")
    elif response.status_code == 409:
        print(f"✅ Email já existe (isso é OK)")
    else:
        print(f"Status: {response.status_code}")
        print(f"Força: {data.get('password_strength', 'N/A')}")
        print(f"Score: {data.get('score', 'N/A')}")
        if 'feedback' in data:
            print(f"Feedback: {data['feedback'][:3]}")

if __name__ == "__main__":
    test_super_strong()
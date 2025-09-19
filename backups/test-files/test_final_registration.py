#!/usr/bin/env python3
"""Final registration test"""

import requests
import time

BASE_URL = "http://localhost:8000"

def test_final_registration():
    """Test final registration functionality"""
    
    print("🧪 TESTE FINAL DE REGISTRO")
    print("=" * 50)
    
    # Test 1: Weak password
    print("\n1️⃣ Testando senha FRACA...")
    response = requests.post(f"{BASE_URL}/api/v1/auth/register", json={
        "email": "fraca@test.com",
        "password": "123456",
        "name": "Usuario Fraco"
    })
    
    print(f"Status: {response.status_code}")
    if response.status_code == 400:
        data = response.json()
        print(f"✅ Rejeitado corretamente: {data.get('password_strength', 'N/A')}")
        print(f"   Score: {data.get('score', 'N/A')}")
    else:
        print(f"❌ Resposta inesperada: {response.json()}")
    
    # Wait a bit
    time.sleep(1)
    
    # Test 2: Strong password
    print("\n2️⃣ Testando senha FORTE...")
    response = requests.post(f"{BASE_URL}/api/v1/auth/register", json={
        "email": "forte@test.com",
        "password": "SenhaForte123!#$",
        "name": "Usuario Forte"
    })
    
    print(f"Status: {response.status_code}")
    if response.status_code in [200, 201]:
        data = response.json()
        print(f"✅ Aceito com sucesso!")
        print(f"   Usuário criado: {data.get('user', {}).get('email', 'N/A')}")
        print(f"   Força da senha: {data.get('password_security', {}).get('strength', 'N/A')}")
        print(f"   Score: {data.get('password_security', {}).get('score', 'N/A')}")
    elif response.status_code == 409:
        print(f"✅ Email já existe (OK)")
    else:
        print(f"❌ Falha: {response.status_code}")
        try:
            print(f"   Erro: {response.json()}")
        except:
            print(f"   Resposta: {response.text}")
    
    print("\n" + "=" * 50)
    print("✅ TESTE CONCLUÍDO!")

if __name__ == "__main__":
    test_final_registration()
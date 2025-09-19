#!/usr/bin/env python3
"""Teste direto do JWT"""

import sys
import os
sys.path.insert(0, '/workspace/apps/api-python')

from dotenv import load_dotenv
load_dotenv()

try:
    from infrastructure.security.jwt_manager import jwt_manager
    
    print("✅ JWT Manager importado com sucesso!")
    print(f"   Secret key existe: {bool(jwt_manager.secret_key)}")
    print(f"   Tamanho da secret key: {len(jwt_manager.secret_key) if jwt_manager.secret_key else 0}")
    
    # Tentar criar um token
    token_pair = jwt_manager.create_token_pair(
        user_id="test-user-id",
        user_email="test@example.com",
        additional_claims={"test": True}
    )
    
    print("\n✅ Token criado com sucesso!")
    print(f"   Access token: {token_pair.access_token[:50]}...")
    print(f"   Refresh token: {token_pair.refresh_token[:50]}...")
    
except Exception as e:
    print(f"❌ Erro ao testar JWT: {e}")
    import traceback
    traceback.print_exc()
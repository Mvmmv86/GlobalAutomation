#!/usr/bin/env python3
"""
Script para criar usuário administrador
"""

import asyncio
import bcrypt
from infrastructure.database.connection_transaction_mode import transaction_db

async def create_admin_user():
    """Criar usuário administrador se não existir"""
    
    print("🔐 CRIANDO USUÁRIO ADMINISTRADOR")
    print("=" * 50)
    
    try:
        await transaction_db.connect()
        
        # Verificar se usuário admin já existe
        admin_user = await transaction_db.fetchrow(
            "SELECT id, email FROM users WHERE email = $1",
            "admin@example.com"
        )
        
        if admin_user:
            print(f"✅ Usuário admin já existe: {admin_user['email']}")
            print(f"   ID: {admin_user['id']}")
        else:
            # Criar usuário admin
            password = "admin123"
            salt = bcrypt.gensalt()
            password_hash = bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')
            
            admin_id = await transaction_db.fetchval("""
                INSERT INTO users (email, password_hash, name, is_active, created_at)
                VALUES ($1, $2, $3, $4, NOW())
                RETURNING id
            """, "admin@example.com", password_hash, "Administrator", True)
            
            print(f"✅ Usuário admin criado com sucesso!")
            print(f"   Email: admin@example.com")
            print(f"   Senha: admin123")
            print(f"   ID: {admin_id}")
        
        # Verificar se a tabela está funcionando
        users_count = await transaction_db.fetchval("SELECT COUNT(*) FROM users")
        print(f"\n📊 Total de usuários na base: {users_count}")
        
        await transaction_db.disconnect()
        return True
        
    except Exception as e:
        print(f"❌ Erro: {e}")
        await transaction_db.disconnect()
        return False

if __name__ == "__main__":
    success = asyncio.run(create_admin_user())
    
    if success:
        print("\n🎯 Agora você pode fazer login com:")
        print("   Email: admin@example.com")
        print("   Senha: admin123")
    else:
        print("\n⚠️ Falha na criação do usuário")
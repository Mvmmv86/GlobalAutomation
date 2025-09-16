#!/usr/bin/env python3
"""
Script para criar/resetar usuário de teste para login
"""
import asyncio
import os
from dotenv import load_dotenv
from passlib.context import CryptContext
from datetime import datetime

# Forçar reload do .env
load_dotenv(override=True)

# Resetar settings singleton
from infrastructure.config import settings as settings_module
settings_module._settings = None

from infrastructure.database.connection import database_manager
from sqlalchemy import text

# Password hasher
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

async def setup_test_user():
    """Criar ou resetar usuário de teste"""
    try:
        await database_manager.connect()
        session = database_manager.get_session()
        
        async with session:
            # Dados do usuário de teste
            email = "demo@tradingplatform.com"
            name = "Demo User"
            password = "Demo123!@#"
            hashed_password = pwd_context.hash(password)
            
            # Verificar se usuário existe
            result = await session.execute(text(
                "SELECT id, email, name FROM users WHERE email = :email"
            ), {"email": email})
            existing_user = result.fetchone()
            
            if existing_user:
                # Atualizar senha
                await session.execute(text("""
                    UPDATE users 
                    SET password_hash = :password_hash,
                        is_active = true,
                        is_verified = true,
                        updated_at = :updated_at,
                        failed_login_attempts = 0,
                        locked_until = NULL
                    WHERE email = :email
                """), {
                    "password_hash": hashed_password,
                    "updated_at": datetime.utcnow(),
                    "email": email
                })
                print(f"✅ Senha do usuário '{email}' atualizada!")
            else:
                # Criar novo usuário
                import uuid
                await session.execute(text("""
                    INSERT INTO users (id, email, name, password_hash, is_active, is_verified, 
                                     totp_enabled, created_at, updated_at, failed_login_attempts)
                    VALUES (:id, :email, :name, :password_hash, true, true, 
                           false, :created_at, :updated_at, 0)
                """), {
                    "id": str(uuid.uuid4()),
                    "email": email,
                    "name": name,
                    "password_hash": hashed_password,
                    "created_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow()
                })
                print(f"✅ Usuário '{email}' criado com sucesso!")
            
            await session.commit()
            
            print("\n🔐 Credenciais para login:")
            print("="*40)
            print(f"📧 Email: {email}")
            print(f"🔑 Senha: {password}")
            print("="*40)
            print("\n🌐 URL do Frontend: http://localhost:3000")
            print("🚀 API Backend: http://localhost:8000")
            
        await database_manager.disconnect()
        
    except Exception as e:
        print(f"❌ Erro: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(setup_test_user())
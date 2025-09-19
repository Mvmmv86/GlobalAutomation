#!/usr/bin/env python3
"""Teste de endpoint de login simplificado"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn
import bcrypt
import jwt
from datetime import datetime, timedelta

app = FastAPI()

class LoginRequest(BaseModel):
    email: str
    password: str

@app.post("/test-login")
async def test_login(request: LoginRequest):
    """Endpoint de teste simplificado"""
    
    # Credenciais fixas para teste
    if request.email == "admin@tradingplatform.com" and request.password == "Admin123!@#":
        # Criar token simples
        token_payload = {
            "user_id": "550e8400-e29b-41d4-a716-446655440003",
            "email": request.email,
            "exp": datetime.utcnow() + timedelta(hours=1)
        }
        
        token = jwt.encode(token_payload, "test-secret-key", algorithm="HS256")
        
        return {
            "access_token": token,
            "token_type": "bearer",
            "user": {
                "id": "550e8400-e29b-41d4-a716-446655440003",
                "email": request.email,
                "name": "Platform Admin"
            }
        }
    else:
        raise HTTPException(status_code=401, detail="Invalid credentials")

@app.get("/health")
async def health():
    return {"status": "ok"}

if __name__ == "__main__":
    print("🚀 Iniciando servidor de teste na porta 8001...")
    uvicorn.run(app, host="0.0.0.0", port=8001)
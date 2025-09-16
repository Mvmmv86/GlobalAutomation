#!/usr/bin/env python3
"""
Teste direto de conexão Supabase sem SQLAlchemy
"""
import asyncio
import asyncpg
import ssl
import os
from dotenv import load_dotenv

load_dotenv()

async def test_direct_connection():
    """Testar conexão direta com asyncpg"""
    
    # Parse da URL do banco
    database_url = os.getenv('DATABASE_URL', '')
    if not database_url:
        print("❌ DATABASE_URL não configurada")
        return
    
    # Extrair componentes da URL
    # postgresql+asyncpg://postgres.zmdqmrugotfftxvrwdsd:MFCuJT0Jn04PtCTL@aws-1-us-east-2.pooler.supabase.com:6543/postgres
    import re
    match = re.match(r'postgresql\+asyncpg://([^:]+):([^@]+)@([^:]+):(\d+)/(.+)', database_url)
    if not match:
        print(f"❌ Formato de URL inválido: {database_url}")
        return
    
    user, password, host, port, dbname = match.groups()
    
    print(f"🔗 Conectando ao Supabase:")
    print(f"   Host: {host}")
    print(f"   Port: {port}")
    print(f"   Database: {dbname}")
    print(f"   User: {user}")
    
    try:
        # SSL context
        ssl_ctx = ssl.create_default_context()
        ssl_ctx.check_hostname = False
        ssl_ctx.verify_mode = ssl.CERT_NONE
        
        # Conectar com asyncpg diretamente
        conn = await asyncpg.connect(
            user=user,
            password=password,
            database=dbname,
            host=host,
            port=int(port),
            ssl=ssl_ctx,
            command_timeout=60,
            # CRÍTICO para pgBouncer: desabilitar prepared statements
            statement_cache_size=0
        )
        
        print("✅ Conexão estabelecida com sucesso!")
        
        # Testar algumas queries
        version = await conn.fetchval('SELECT version();')
        print(f"📊 Versão PostgreSQL: {version}")
        
        # Listar tabelas
        tables = await conn.fetch("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            ORDER BY table_name
            LIMIT 10;
        """)
        
        if tables:
            print("📋 Tabelas encontradas:")
            for table in tables:
                print(f"   - {table['table_name']}")
        else:
            print("📋 Nenhuma tabela encontrada no schema public")
            
        # Testar schema auth (Supabase)
        auth_tables = await conn.fetch("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'auth'
            ORDER BY table_name
            LIMIT 5;
        """)
        
        if auth_tables:
            print("🔐 Tabelas do auth schema (Supabase):")
            for table in auth_tables:
                print(f"   - {table['table_name']}")
        
        await conn.close()
        print("🔌 Conexão fechada")
        return True
        
    except Exception as e:
        print(f"❌ Erro: {e}")
        return False

if __name__ == "__main__":
    asyncio.run(test_direct_connection())
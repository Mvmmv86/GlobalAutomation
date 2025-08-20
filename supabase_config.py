# supabase_config.py
"""
Configuração completa para integração Supabase com projeto existente
"""
import os
from typing import Optional
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from supabase import create_client, Client
import logging

logger = logging.getLogger(__name__)

class SupabaseConfig:
    """Configuração centralizada para Supabase"""
    
    def __init__(self):
        # Configurações Supabase
        self.supabase_url = os.getenv("SUPABASE_URL")
        self.supabase_anon_key = os.getenv("SUPABASE_ANON_KEY")
        self.supabase_service_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        
        # Validar configurações obrigatórias
        if not all([self.supabase_url, self.supabase_anon_key]):
            raise ValueError("SUPABASE_URL e SUPABASE_ANON_KEY são obrigatórios")
        
        # Configuração SQLAlchemy para Supabase PostgreSQL
        self.database_url = os.getenv(
            "DATABASE_URL",
            self._build_database_url()
        )
        
        # Engine SQLAlchemy
        self.engine = create_async_engine(
            self.database_url,
            echo=os.getenv("DATABASE_ECHO", "false").lower() == "true",
            pool_size=int(os.getenv("DATABASE_POOL_SIZE", "10")),
            max_overflow=int(os.getenv("DATABASE_MAX_OVERFLOW", "20")),
            pool_pre_ping=True,
            pool_recycle=3600,
        )
        
        # Clientes Supabase
        self.supabase_client: Client = create_client(
            self.supabase_url, 
            self.supabase_anon_key
        )
        
        # Cliente administrativo (se service key disponível)
        self.supabase_admin: Optional[Client] = None
        if self.supabase_service_key:
            self.supabase_admin = create_client(
                self.supabase_url, 
                self.supabase_service_key
            )
        
        # Session factory
        self.async_session = sessionmaker(
            self.engine, 
            class_=AsyncSession, 
            expire_on_commit=False
        )
        
        logger.info("Configuração Supabase inicializada com sucesso")
    
    def _build_database_url(self) -> str:
        """Construir URL do banco a partir das configurações Supabase"""
        if not self.supabase_url:
            raise ValueError("SUPABASE_URL é obrigatório")
        
        # Extrair project ID da URL do Supabase
        project_id = self.supabase_url.split("//")[1].split(".")[0]
        password = os.getenv("DB_PASSWORD", "")
        
        if not password:
            raise ValueError("DB_PASSWORD é obrigatório para conexão com banco")
        
        return f"postgresql+asyncpg://postgres:{password}@db.{project_id}.supabase.co:5432/postgres"
    
    async def get_session(self) -> AsyncSession:
        """Obter sessão SQLAlchemy assíncrona"""
        async with self.async_session() as session:
            try:
                yield session
            finally:
                await session.close()
    
    async def test_connection(self) -> bool:
        """Testar conexão com Supabase"""
        try:
            # Testar SQLAlchemy
            async with self.engine.begin() as conn:
                result = await conn.execute("SELECT 1")
                assert result.fetchone()[0] == 1
            
            # Testar cliente Supabase
            response = self.supabase_client.table('users').select('count').limit(1).execute()
            
            logger.info("Conexão Supabase testada com sucesso")
            return True
            
        except Exception as e:
            logger.error(f"Erro ao testar conexão Supabase: {e}")
            return False
    
    async def close(self):
        """Fechar conexões"""
        await self.engine.dispose()
        logger.info("Conexões Supabase fechadas")

# Instância global (singleton)
_supabase_config: Optional[SupabaseConfig] = None

def get_supabase_config() -> SupabaseConfig:
    """Obter instância singleton da configuração Supabase"""
    global _supabase_config
    if _supabase_config is None:
        _supabase_config = SupabaseConfig()
    return _supabase_config

# Dependency para FastAPI
async def get_db_session():
    """Dependency para obter sessão de banco de dados"""
    config = get_supabase_config()
    async with config.async_session() as session:
        try:
            yield session
        finally:
            await session.close()

def get_supabase_client() -> Client:
    """Obter cliente Supabase"""
    config = get_supabase_config()
    return config.supabase_client

def get_supabase_admin() -> Optional[Client]:
    """Obter cliente administrativo Supabase"""
    config = get_supabase_config()
    return config.supabase_admin


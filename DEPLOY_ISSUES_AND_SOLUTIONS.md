# 🚨 Problemas Potenciais de Deploy e Soluções

**Baseado em análise completa do código**
**Data**: 21/10/2025

---

## ⚠️ PROBLEMAS CRÍTICOS IDENTIFICADOS

### 🔴 **PROBLEMA 1: Redis Comentado no Código**

**Localização**: `main.py` linha 89-91

```python
# Initialize Redis (temporarily disabled for integration testing)
# await redis_manager.connect()
logger.info("Redis connection skipped for integration testing")
```

**Impacto**: ALTO - Sistema não vai funcionar sem Redis em produção

**Sintomas**:
- Cache não funcionará
- Celery não funcionará
- Background tasks podem falhar

**Solução ANTES do Deploy**:
```python
# Descomentar no main.py
await redis_manager.connect()
logger.info("Redis connected successfully")
```

**OU configurar para funcionar sem Redis** (não recomendado):
- Desabilitar Celery
- Desabilitar cache
- Usar apenas banco de dados

**Ação Recomendada**: ✅ **DESCOMENTAR antes do deploy**

---

### 🟡 **PROBLEMA 2: Imports de Controladores Removidos**

**Localização**: `main.py` linha 44

```python
# from presentation.controllers.auth_controller import create_auth_router  # Removido - problema DI
```

**Impacto**: MÉDIO - Auth pode não funcionar se depender deste router

**Verificação Necessária**:
```bash
# Verificar se auth_router está sendo usado
grep -r "auth_router" apps/api-python/main.py
```

**Se auth está funcionando**: OK, provavelmente usando outro controller
**Se auth NÃO funciona**: Descomentar e corrigir problema de DI

---

### 🔴 **PROBLEMA 3: Porta Hardcoded**

**Localização**: Final do `main.py` (preciso verificar)

**Problema Potencial**: Digital Ocean usa variável `PORT` dinâmica

**Solução Correta**:
```python
import os

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))  # Digital Ocean define PORT
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=False,  # NUNCA usar reload em produção
        workers=1  # ou mais dependendo da instância
    )
```

---

### 🟡 **PROBLEMA 4: Database Pool Size**

**Localização**: `settings.py` e variáveis de ambiente

**Problema**: Supabase Free Tier tem limite baixo de conexões (20-30)

**Configuração Atual**:
```python
db_pool_size: int = Field(default=10, env="DB_POOL_SIZE")
db_max_overflow: int = Field(default=20, env="DB_MAX_OVERFLOW")
```

**Total**: 10 + 20 = **30 conexões** (pode exceder limite)

**Solução para Deploy**:
```bash
DB_POOL_SIZE=3
DB_MAX_OVERFLOW=7
```

**Total**: 3 + 7 = **10 conexões** (seguro para Free Tier)

---

### 🔴 **PROBLEMA 5: Background Tasks Sem Tratamento de Erro**

**Localização**: `main.py` lifespan

```python
asyncio.create_task(start_cache_cleanup_task())
asyncio.create_task(start_candles_cache_cleanup())
```

**Problema**: Se task falhar, pode crashear app silenciosamente

**Solução Melhorada**:
```python
async def safe_task(coro, task_name):
    try:
        await coro
    except Exception as e:
        logger.error(f"{task_name} failed", error=str(e))

asyncio.create_task(safe_task(start_cache_cleanup_task(), "Cache cleanup"))
asyncio.create_task(safe_task(start_candles_cache_cleanup(), "Candles cleanup"))
```

---

### 🟡 **PROBLEMA 6: CORS Origins Hardcoded**

**Localização**: `settings.py` linha 41-43

```python
cors_origins: List[str] = Field(
    default=["http://localhost:3000", "http://localhost:3001", "http://localhost:3002"],
    env="CORS_ORIGINS"
)
```

**Problema**: Valores default são localhost

**Solução**: SEMPRE definir `CORS_ORIGINS` nas variáveis de ambiente

```bash
CORS_ORIGINS=["https://app.globalautomation.com","https://admin.globalautomation.com"]
```

**NUNCA** deixar defaults em produção!

---

### 🔴 **PROBLEMA 7: Binance API Keys Fallback**

**Localização**: Vários arquivos usando `os.getenv('BINANCE_API_KEY')`

**Risco**: Se não houver chaves no banco E não houver fallback, sistema falha

**Arquivos Afetados**:
- `main.py:367-368`
- `dashboard_controller.py:288-289`
- `webhooks_crud_controller.py:504-505`
- `sync_scheduler.py:128-129`
- `binance_connector.py:33-35`

**Código**:
```python
api_key = account['api_key'] or os.getenv('BINANCE_API_KEY')
secret_key = account['secret_key'] or os.getenv('BINANCE_SECRET_KEY')
```

**Solução**:

**Opção 1** - Fornecer chaves globais (menos seguro):
```bash
BINANCE_API_KEY=your-global-key
BINANCE_API_SECRET=your-global-secret
```

**Opção 2** - Forçar erro se não houver chaves (mais seguro):
```python
if not api_key or not secret_key:
    raise HTTPException(
        status_code=400,
        detail="Binance API keys not configured. Please add your exchange account."
    )
```

---

### 🟡 **PROBLEMA 8: Encryption Service Cria Key Automaticamente**

**Localização**: `encryption_service.py:48`

```python
os.environ["ENCRYPTION_MASTER_KEY"] = key
```

**Problema**: Se não houver key, cria automaticamente e salva em ENV

**Risco**: Key gerada dinamicamente será perdida quando app reiniciar

**Solução**: SEMPRE definir `ENCRYPTION_MASTER_KEY` ANTES do primeiro deploy

**Comando**:
```bash
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

**SALVAR** esta key em local seguro ANTES de usar!

---

### 🔴 **PROBLEMA 9: Webhook URL Geração Depende de ENV VAR**

**Localização**: `bots_controller.py:224`

```python
base_url = os.getenv("VITE_WEBHOOK_PUBLIC_URL") or os.getenv("API_BASE_URL")
```

**Problema**: Se não houver estas variáveis, webhooks não funcionarão

**Solução OBRIGATÓRIA**:
```bash
API_BASE_URL=https://your-app.ondigitalocean.app
VITE_WEBHOOK_PUBLIC_URL=https://your-app.ondigitalocean.app
```

**Teste**:
```bash
curl https://your-app.ondigitalocean.app/health
# Deve retornar 200 OK
```

---

### 🟡 **PROBLEMA 10: Async Context Manager Cleanup**

**Localização**: `main.py` lifespan shutdown

**Problema Potencial**: Se shutdown falhar, pode deixar conexões abertas

**Verificação Necessária**: Garantir que shutdown está tratado corretamente

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup...
    yield
    # Shutdown
    try:
        await sync_scheduler.stop()
        await transaction_db.disconnect()
        # await redis_manager.disconnect()  # Se Redis estiver habilitado
        await cleanup_container()
        logger.info("Application shutdown complete")
    except Exception as e:
        logger.error("Error during shutdown", error=str(e))
```

---

## 📋 CHECKLIST FINAL PRÉ-DEPLOY

### **Código**
- [ ] Redis DESCOMENTADO em `main.py`
- [ ] Porta usando `os.getenv("PORT", 8000)`
- [ ] Background tasks com error handling
- [ ] Shutdown cleanup implementado

### **Variáveis de Ambiente**
- [ ] `ENCRYPTION_MASTER_KEY` gerada E salva em vault
- [ ] `SECRET_KEY` gerado (32+ chars)
- [ ] `DATABASE_URL` configurada (Supabase)
- [ ] `REDIS_URL` configurada
- [ ] `CORS_ORIGINS` com domínio real
- [ ] `API_BASE_URL` com domínio Digital Ocean
- [ ] `DB_POOL_SIZE=3` e `DB_MAX_OVERFLOW=7` (para Free Tier)

### **Infraestrutura**
- [ ] Redis database criado (Digital Ocean ou Upstash)
- [ ] Supabase migrations executadas
- [ ] Admin user criado no banco
- [ ] Bots system criado no banco

### **Testes Locais ANTES do Deploy**
```bash
# 1. Teste com env vars de produção localmente
export ENV=production
export DEBUG=false
export DATABASE_URL="postgresql+asyncpg://..."
export REDIS_URL="redis://..."
python3 main.py

# 2. Teste endpoints
curl http://localhost:8000/health
curl http://localhost:8000/api/v1/bots/available

# 3. Teste webhook
curl -X POST http://localhost:8000/api/v1/webhooks/master/test-path \
  -H "Content-Type: application/json" \
  -d '{"ticker":"BTCUSDT","action":"buy"}'
```

---

## 🔧 CORREÇÕES RECOMENDADAS ANTES DO DEPLOY

### **1. Habilitar Redis**

**Arquivo**: `apps/api-python/main.py`

```python
# LINHA 89-91 MUDAR DE:
# await redis_manager.connect()
logger.info("Redis connection skipped for integration testing")

# PARA:
await redis_manager.connect()
logger.info("Redis connected successfully")
```

### **2. Ajustar Pool de Conexões**

**Arquivo**: `apps/api-python/.env` ou variáveis Digital Ocean

```bash
DB_POOL_SIZE=3
DB_MAX_OVERFLOW=7
DB_POOL_TIMEOUT=30
DB_POOL_RECYCLE=1800
```

### **3. Adicionar Health Check Robusto**

**Arquivo**: `apps/api-python/presentation/controllers/health_controller.py`

Garantir que health check verifica:
- Database connectivity
- Redis connectivity
- Disk space
- Memory usage

### **4. Configurar Logging para Produção**

**Arquivo**: `apps/api-python/main.py`

```python
import logging

if settings.environment == "production":
    logging.basicConfig(level=logging.INFO)
else:
    logging.basicConfig(level=logging.DEBUG)
```

---

## 🚀 ORDEM DE DEPLOY SEGURA

1. **Preparação Local**
   ```bash
   # Gerar todos os secrets
   python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
   # Salvar em vault/1Password
   ```

2. **Criar Redis**
   - Digital Ocean → Databases → Create → Redis
   - Copiar connection string

3. **Configurar Variáveis**
   - Digital Ocean App → Settings → Environment Variables
   - Adicionar TODAS as variáveis do arquivo `DIGITAL_OCEAN_ENV_VARS.txt`

4. **Deploy Inicial**
   - Push para GitHub
   - Digital Ocean faz build automático

5. **Verificar Logs**
   - Digital Ocean → Runtime Logs
   - Procurar por erros

6. **Testar Endpoints**
   ```bash
   curl https://your-app.ondigitalocean.app/health
   ```

7. **Configurar Domínio** (opcional)
   - Digital Ocean → Settings → Domains
   - Adicionar CNAME/A record

---

## 📊 MONITORAMENTO PÓS-DEPLOY

### **Logs Críticos para Observar**

```bash
# 1. Database connection
grep "Database connected" logs

# 2. Redis connection
grep "Redis connected" logs

# 3. Background tasks
grep "Starting background" logs

# 4. Errors
grep -E "error|exception|failed" logs | grep -v "test"
```

### **Métricas para Monitorar**

- **Response Time**: < 500ms
- **Error Rate**: < 1%
- **Database Connections**: < 10
- **Memory Usage**: < 512MB
- **CPU Usage**: < 50%

---

**✅ Documento completo de troubleshooting para deploy**
**📅 Última atualização**: 21/10/2025

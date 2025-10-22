# 🚀 Guia Completo de Deploy na Digital Ocean

**Projeto**: Global Automation Trading Platform
**Data**: 21/10/2025
**Ambiente**: Production

---

## 📋 VARIÁVEIS DE AMBIENTE OBRIGATÓRIAS

### 🔐 **1. SEGURANÇA E AUTENTICAÇÃO** (CRÍTICAS)

```bash
# Secret Key para JWT (GERAR NOVO EM PRODUÇÃO)
SECRET_KEY=your-super-secret-key-change-this-in-production-min-32-chars

# TradingView Webhook Secret
TV_WEBHOOK_SECRET=your-tradingview-webhook-secret-min-16-chars

# Encryption Key (CRÍTICO - 32 bytes para AES)
ENCRYPTION_KEY=your-32-byte-encryption-key-change-this

# Master Encryption Key (CRÍTICO - Fernet format 44 chars)
# Gerar com: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
ENCRYPTION_MASTER_KEY=your-fernet-key-here-change-this-44-chars
```

**⚠️ ATENÇÃO**:
- `ENCRYPTION_MASTER_KEY` é usada para criptografar segredos de bots no banco
- Se perder esta chave, **TODOS OS DADOS CRIPTOGRAFADOS SERÃO IRRECUPERÁVEIS**
- Faça backup desta chave em local seguro (vault, 1Password, etc)

---

### 🗄️ **2. DATABASE** (CRÍTICO)

```bash
# URL do Banco Supabase (formato asyncpg para FastAPI)
DATABASE_URL=postgresql+asyncpg://user:password@host:5432/database

# Pool de Conexões
DB_POOL_SIZE=10
DB_MAX_OVERFLOW=20
DB_POOL_TIMEOUT=30
DB_POOL_RECYCLE=3600
DATABASE_ECHO=false
```

**⚠️ IMPORTANTE**:
- Supabase usa **pooler mode** - DEVE usar porta correta:
  - **Transaction Mode**: porta 6543
  - **Session Mode**: porta 5432
- URL correta: `postgresql+asyncpg://postgres.PROJECT:PASSWORD@aws-0-REGION.pooler.supabase.com:5432/postgres`

---

### 🔴 **3. REDIS** (CRÍTICO para Cache)

```bash
# URL do Redis (Digital Ocean Managed Redis ou externo)
REDIS_URL=redis://default:password@host:25061
REDIS_MAX_CONNECTIONS=10

# Celery (usa o mesmo Redis)
CELERY_BROKER_URL=redis://default:password@host:25061/1
CELERY_RESULT_BACKEND=redis://default:password@host:25061/1
```

**⚠️ Digital Ocean Redis**:
- Managed Redis vem com senha obrigatória
- Formato: `redis://default:PASSWORD@HOST:PORT`
- Porta padrão: `25061` (não 6379)

---

### 🌐 **4. APLICAÇÃO E AMBIENTE**

```bash
# Environment
ENV=production
DEBUG=false
PORT=8000
VERSION=1.0.0

# JWT Config
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

---

### 🔒 **5. CORS E SEGURANÇA**

```bash
# CORS Origins (AJUSTAR PARA SEU DOMÍNIO)
CORS_ORIGINS=["https://your-frontend-domain.com","https://www.your-frontend-domain.com"]

# Allowed Hosts
ALLOWED_HOSTS=["your-backend-domain.com","your-app-name.ondigitalocean.app"]

# Rate Limiting
RATE_LIMIT_PER_MINUTE=100
WEBHOOK_RATE_LIMIT_PER_MINUTE=200
AUTH_RATE_LIMIT_PER_MINUTE=500
```

**⚠️ IMPORTANTE**:
- `CORS_ORIGINS` deve incluir o domínio do frontend
- `ALLOWED_HOSTS` deve incluir o domínio do backend na Digital Ocean
- Formato: `["https://domain.com"]` (JSON array)

---

### 💹 **6. BINANCE API** (OPCIONAL - Fallback Global)

```bash
# API Keys da Binance (OPCIONAL - usado como fallback)
# Usuários devem cadastrar suas próprias chaves na plataforma
BINANCE_API_KEY=your-binance-api-key-optional
BINANCE_API_SECRET=your-binance-secret-key-optional
```

**ℹ️ NOTA**:
- Estas chaves são **opcionais**
- Sistema usa as chaves de cada usuário armazenadas no banco
- Estas servem apenas como fallback de desenvolvimento

---

### 📊 **7. MONITORAMENTO** (OPCIONAL)

```bash
# Sentry para tracking de erros (RECOMENDADO EM PRODUÇÃO)
SENTRY_DSN=https://your-sentry-dsn@sentry.io/project-id
```

---

### 🌍 **8. WEBHOOK URL PÚBLICA** (IMPORTANTE)

```bash
# URL pública do backend para webhooks TradingView
# Substitua pelo seu domínio da Digital Ocean
API_BASE_URL=https://your-app-name.ondigitalocean.app
VITE_WEBHOOK_PUBLIC_URL=https://your-app-name.ondigitalocean.app
```

**⚠️ CRÍTICO**:
- Esta URL é usada para gerar webhooks master dos bots
- Deve ser acessível publicamente pela internet
- TradingView enviará requisições POST para esta URL

---

## 🚨 POSSÍVEIS PROBLEMAS E SOLUÇÕES

### ❌ **PROBLEMA 1: Database Connection Pool Exhausted**

**Erro**:
```
asyncpg.exceptions.TooManyConnectionsError: sorry, too many clients already
```

**Causa**: Supabase Free Tier tem limite de conexões (ex: 20-30 conexões)

**Solução**:
```bash
# Ajustar pool de conexões
DB_POOL_SIZE=5
DB_MAX_OVERFLOW=10
```

**Verificação**:
- Supabase Dashboard → Database → Connection Pooler
- Usar **Transaction Mode** (porta 6543) ao invés de Session Mode
- URL correta: `postgresql+asyncpg://...@...pooler.supabase.com:6543/postgres`

---

### ❌ **PROBLEMA 2: Redis Connection Refused**

**Erro**:
```
redis.exceptions.ConnectionError: Error connecting to Redis
```

**Causa**: Redis URL incorreta ou Redis não configurado

**Soluções**:

**Opção 1 - Redis Gerenciado Digital Ocean**:
```bash
# Criar Managed Redis Database na Digital Ocean
# Copiar connection string do dashboard
REDIS_URL=redis://default:PASSWORD@db-redis-XXXXX-do-user-XXXXX.ondigitalocean.com:25061
```

**Opção 2 - Upstash Redis (Free Tier)**:
```bash
# Criar conta em upstash.com
# Criar database Redis
REDIS_URL=redis://default:PASSWORD@REGION.upstash.io:PORT
```

**Opção 3 - Redis Cloud (Free)**:
```bash
# Criar conta em redis.com
REDIS_URL=redis://default:PASSWORD@redis-XXXXX.cloud.redislabs.com:PORT
```

---

### ❌ **PROBLEMA 3: ENCRYPTION_MASTER_KEY Missing**

**Erro**:
```
ValueError: ENCRYPTION_MASTER_KEY environment variable is required
```

**Causa**: Falta a chave de encriptação

**Solução**:
```bash
# Gerar nova chave Fernet
python3 << 'EOF'
from cryptography.fernet import Fernet
key = Fernet.generate_key().decode()
print(f"ENCRYPTION_MASTER_KEY={key}")
EOF

# Adicionar às variáveis de ambiente da Digital Ocean
ENCRYPTION_MASTER_KEY=ABC123...XYZ789==  # 44 caracteres
```

**⚠️ BACKUP**: Salve esta chave em local seguro ANTES do deploy!

---

### ❌ **PROBLEMA 4: CORS Blocked**

**Erro no Console do Browser**:
```
Access to fetch at 'https://api.domain.com' from origin 'https://app.domain.com'
has been blocked by CORS policy
```

**Causa**: Frontend não está na lista CORS_ORIGINS

**Solução**:
```bash
# Adicionar TODOS os domínios do frontend
CORS_ORIGINS=["https://app.domain.com","https://www.app.domain.com","http://localhost:3000"]
```

**Formato Correto**:
- JSON array string
- Protocolo completo (https://)
- Sem barra final

---

### ❌ **PROBLEMA 5: Webhook TradingView 404 Not Found**

**Erro**:
```
TradingView webhook failed: 404 Not Found
```

**Causa**: URL do webhook incorreta ou não acessível

**Verificações**:
1. `API_BASE_URL` está correta?
2. App está rodando na Digital Ocean?
3. URL pública está acessível?

**Teste**:
```bash
# Testar de fora da Digital Ocean
curl https://your-app.ondigitalocean.app/health
# Deve retornar 200 OK
```

**Solução**:
```bash
# Configurar corretamente
API_BASE_URL=https://your-app-name.ondigitalocean.app
VITE_WEBHOOK_PUBLIC_URL=https://your-app-name.ondigitalocean.app
```

---

### ❌ **PROBLEMA 6: Python Dependencies Fail**

**Erro durante build**:
```
ERROR: Could not find a version that satisfies the requirement package==X.Y.Z
```

**Causa**: Python version incompatível ou dependência desatualizada

**Solução**:
```dockerfile
# Garantir Python 3.11+ no Dockerfile
FROM python:3.11-slim

# requirements.txt sem versões fixas muito específicas
# Trocar de:
some-package==1.2.3
# Para:
some-package>=1.2.0,<2.0.0
```

---

### ❌ **PROBLEMA 7: Port Already in Use**

**Erro**:
```
OSError: [Errno 98] Address already in use
```

**Causa**: Digital Ocean espera que app rode na porta especificada

**Solução**:
```bash
# Digital Ocean App Platform usa variável PORT automaticamente
# NÃO definir PORT manualmente, ou usar:
PORT=${PORT:-8000}
```

**Em main.py**:
```python
import os
port = int(os.getenv("PORT", 8000))
uvicorn.run(app, host="0.0.0.0", port=port)
```

---

### ❌ **PROBLEMA 8: Static Files 404**

**Erro**: Frontend build files retornam 404

**Causa**: Digital Ocean precisa de configuração especial para SPA

**Solução - Criar `app.yaml`**:
```yaml
name: global-automation-backend
region: nyc
services:
  - name: api
    build_command: pip install -r apps/api-python/requirements.txt
    run_command: cd apps/api-python && uvicorn main:app --host 0.0.0.0 --port $PORT
    environment_slug: python
    http_port: 8000
    health_check:
      http_path: /health
```

---

## ✅ CHECKLIST PRÉ-DEPLOY

### **1. Variáveis de Ambiente Configuradas**
- [ ] `SECRET_KEY` gerado (min 32 chars aleatórios)
- [ ] `ENCRYPTION_MASTER_KEY` gerado (44 chars Fernet)
- [ ] `ENCRYPTION_KEY` gerado (32 chars)
- [ ] `TV_WEBHOOK_SECRET` definido
- [ ] `DATABASE_URL` configurada (Supabase)
- [ ] `REDIS_URL` configurada
- [ ] `CORS_ORIGINS` com domínio do frontend
- [ ] `API_BASE_URL` com domínio da Digital Ocean
- [ ] `ENV=production`
- [ ] `DEBUG=false`

### **2. Banco de Dados Preparado**
- [ ] Tabelas criadas (migrations executadas)
- [ ] Sistema de bots criado (`create_bots_system.sql`)
- [ ] Sistema de admin criado (`create_admin_system.sql`)
- [ ] Colunas SL/TP adicionadas
- [ ] Allowed directions adicionado
- [ ] Usuário admin criado

### **3. Redis Configurado**
- [ ] Redis database criado (Digital Ocean ou Upstash)
- [ ] Connection string testada
- [ ] Cache funcionando

### **4. Arquivos de Deploy**
- [ ] `requirements.txt` atualizado
- [ ] `Dockerfile` configurado (se usar)
- [ ] `.dockerignore` criado
- [ ] `app.yaml` criado (se usar App Platform)

### **5. Segurança**
- [ ] `.env` NÃO commitado no Git
- [ ] Secrets armazenados em vault
- [ ] HTTPS habilitado
- [ ] Rate limiting configurado

---

## 📝 COMANDOS PARA GERAR SECRETS

### **Secret Key (32+ chars)**
```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

### **Encryption Master Key (Fernet 44 chars)**
```bash
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

### **Encryption Key (32 bytes)**
```bash
python3 -c "import secrets; print(secrets.token_hex(16))"
```

### **TradingView Webhook Secret**
```bash
python3 -c "import secrets; print(secrets.token_urlsafe(24))"
```

---

## 🔧 CONFIGURAÇÃO DIGITAL OCEAN APP PLATFORM

### **app.yaml completo**:
```yaml
name: global-automation-api
region: nyc
services:
  - name: backend
    github:
      repo: Mvmmv86/GlobalAutomation
      branch: main
      deploy_on_push: true
    build_command: |
      cd apps/api-python && pip install -r requirements.txt
    run_command: |
      cd apps/api-python && uvicorn main:app --host 0.0.0.0 --port $PORT
    environment_slug: python
    instance_count: 1
    instance_size_slug: basic-xxs
    http_port: 8000
    health_check:
      http_path: /health
      initial_delay_seconds: 60
      period_seconds: 10
      timeout_seconds: 5
      success_threshold: 1
      failure_threshold: 3
    envs:
      - key: ENV
        value: production
      - key: DEBUG
        value: "false"
      - key: SECRET_KEY
        value: ${SECRET_KEY}
        type: SECRET
      - key: ENCRYPTION_MASTER_KEY
        value: ${ENCRYPTION_MASTER_KEY}
        type: SECRET
      - key: ENCRYPTION_KEY
        value: ${ENCRYPTION_KEY}
        type: SECRET
      - key: TV_WEBHOOK_SECRET
        value: ${TV_WEBHOOK_SECRET}
        type: SECRET
      - key: DATABASE_URL
        value: ${DATABASE_URL}
        type: SECRET
      - key: REDIS_URL
        value: ${REDIS_URL}
        type: SECRET
      - key: CORS_ORIGINS
        value: '["https://your-frontend.com"]'
      - key: API_BASE_URL
        value: ${_self.PRIVATE_URL}
```

---

## 🎯 ORDEM DE DEPLOY RECOMENDADA

1. **Criar Redis Database** (Digital Ocean Managed ou Upstash)
2. **Configurar Supabase** (já existente)
3. **Gerar todos os secrets** (comandos acima)
4. **Criar App na Digital Ocean**
5. **Adicionar variáveis de ambiente**
6. **Conectar repositório GitHub**
7. **Fazer deploy**
8. **Verificar logs**
9. **Testar endpoints** (`/health`, `/api/v1/auth/login`)
10. **Configurar domínio customizado** (opcional)

---

## 📊 MONITORAMENTO PÓS-DEPLOY

### **Verificar Saúde da Aplicação**:
```bash
curl https://your-app.ondigitalocean.app/health
# Esperado: {"status": "healthy"}
```

### **Verificar Logs**:
- Digital Ocean Dashboard → App → Runtime Logs
- Filtrar por "error", "exception", "failed"

### **Testar Endpoints Críticos**:
```bash
# Login
curl -X POST https://your-app.ondigitalocean.app/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@tradingplatform.com","password":"Admin123!@#"}'

# Bots disponíveis
curl https://your-app.ondigitalocean.app/api/v1/bots/available
```

---

## 🆘 SUPORTE E TROUBLESHOOTING

Se encontrar problemas:

1. **Verificar logs da Digital Ocean**
2. **Verificar status do Redis** (ping)
3. **Verificar conexão com Supabase** (dashboard)
4. **Testar variáveis localmente** (criar `.env` temporário)
5. **Consultar documentação**:
   - [Digital Ocean App Platform](https://docs.digitalocean.com/products/app-platform/)
   - [Supabase Connection](https://supabase.com/docs/guides/database/connecting-to-postgres)

---

**✅ Guia preparado para deploy em produção**
**📅 Última atualização**: 21/10/2025

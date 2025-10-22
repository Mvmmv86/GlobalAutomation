# ✅ CHECKLIST DE DEPLOY - DIGITAL OCEAN

**Projeto**: Global Automation
**Data**: 21/10/2025

---

## 🎯 **O QUE EU (CLAUDE) JÁ FIZ POR VOCÊ**

- ✅ Gerei todos os 4 secrets necessários
- ✅ Criei arquivo `.env` pronto com valores
- ✅ Identifiquei problemas no código
- ✅ Preparei documentação completa

---

## 📝 **O QUE VOCÊ PRECISA FAZER**

### **PARTE 1: PREPARAÇÃO (15 minutos)**

- [ ] **1.1** Abrir arquivo `DIGITAL_OCEAN_READY.env` (já está pronto!)
- [ ] **1.2** SALVAR estes secrets em local seguro (1Password, vault):
  ```
  ENCRYPTION_MASTER_KEY=hq9SeiQHhcq5xDHNNPcaYj1nHB3tG5HT-PhCVG-ZGbU=
  SECRET_KEY=DURlj4p3u-YOhRhKGBjI4z3CY_I2N2W5Biek-mfx6Ls
  ```

- [ ] **1.3** Criar Redis Database:

  **Opção A - Digital Ocean (Recomendado)**:
  1. Acessar: https://cloud.digitalocean.com/databases
  2. Click "Create" → "Database"
  3. Escolher: Redis
  4. Plan: Basic ($15/mês) ou Development ($7/mês)
  5. Região: Mesma do seu app
  6. Click "Create Database"
  7. Copiar "Connection String"
  8. Substituir em `DIGITAL_OCEAN_READY.env`:
     ```
     REDIS_URL=redis://default:SENHA@host:25061
     ```

  **Opção B - Upstash (Grátis)**:
  1. Criar conta: https://upstash.com
  2. Create Database → Redis
  3. Copiar "Redis URL"
  4. Substituir em `DIGITAL_OCEAN_READY.env`

---

### **PARTE 2: DIGITAL OCEAN APP (20 minutos)**

- [ ] **2.1** Acessar Digital Ocean: https://cloud.digitalocean.com/apps
- [ ] **2.2** Click "Create App"
- [ ] **2.3** Conectar GitHub:
  - Source: GitHub
  - Repository: `Mvmmv86/GlobalAutomation`
  - Branch: `main`
  - Autodeploy: ✅ Enabled

- [ ] **2.4** Configurar Build:
  - Type: Web Service
  - Build Command: `cd apps/api-python && pip install -r requirements.txt`
  - Run Command: `cd apps/api-python && uvicorn main:app --host 0.0.0.0 --port $PORT`
  - HTTP Port: `8000`

- [ ] **2.5** Escolher Plano:
  - Basic: $5/mês (512MB RAM, 1 vCPU) ✅ Recomendado para começar
  - Professional: $12/mês (se precisar mais recursos)

- [ ] **2.6** Nomear a aplicação:
  - Exemplo: `global-automation-api`
  - A URL será: `global-automation-api.ondigitalocean.app`

- [ ] **2.7** Copiar a URL da app (vai aparecer após criar)
  - Exemplo: `https://global-automation-api-abc123.ondigitalocean.app`

- [ ] **2.8** Atualizar `DIGITAL_OCEAN_READY.env` com a URL:
  ```
  API_BASE_URL=https://global-automation-api-abc123.ondigitalocean.app
  VITE_WEBHOOK_PUBLIC_URL=https://global-automation-api-abc123.ondigitalocean.app
  ALLOWED_HOSTS=["global-automation-api-abc123.ondigitalocean.app"]
  ```

---

### **PARTE 3: VARIÁVEIS DE AMBIENTE (10 minutos)**

- [ ] **3.1** Na Digital Ocean App → Settings → Environment Variables
- [ ] **3.2** Abrir `DIGITAL_OCEAN_READY.env`
- [ ] **3.3** Copiar e colar **CADA** variável:

  **CRÍTICAS (copiar exatamente)**:
  - [ ] `ENV=production`
  - [ ] `DEBUG=false`
  - [ ] `SECRET_KEY=DURlj4p3u-YOhRhKGBjI4z3CY_I2N2W5Biek-mfx6Ls`
  - [ ] `ENCRYPTION_MASTER_KEY=hq9SeiQHhcq5xDHNNPcaYj1nHB3tG5HT-PhCVG-ZGbU=`
  - [ ] `ENCRYPTION_KEY=ffdb8b01e87468367cac9d037be852eb`
  - [ ] `TV_WEBHOOK_SECRET=HRIPSfcdViivRqerQ0kgBUo8aR9ZV03A`
  - [ ] `DATABASE_URL=postgresql+asyncpg://postgres.zmdqmrugotfftxvrwdsd:Wzg0kBvtrSbclQ9V@aws-1-us-east-2.pooler.supabase.com:5432/postgres`
  - [ ] `REDIS_URL=` (sua URL do Redis)
  - [ ] `API_BASE_URL=` (URL da app Digital Ocean)
  - [ ] `CORS_ORIGINS=` (com domínio do frontend)

  **OPCIONAIS**:
  - [ ] `BINANCE_API_KEY` (se quiser fallback)
  - [ ] `BINANCE_API_SECRET` (se quiser fallback)
  - [ ] `SENTRY_DSN` (se quiser monitoramento)

- [ ] **3.4** Click "Save"

---

### **PARTE 4: DEPLOY (5 minutos)**

- [ ] **4.1** Digital Ocean vai fazer build automático
- [ ] **4.2** Aguardar build (5-10 minutos)
- [ ] **4.3** Verificar logs: App → Runtime Logs
  - Procurar por: "Database connected"
  - Procurar por: "Redis connected"
  - Procurar por erros

---

### **PARTE 5: TESTE (5 minutos)**

- [ ] **5.1** Testar health check:
  ```bash
  curl https://SUA-URL.ondigitalocean.app/health
  ```
  Esperado: `{"status":"healthy"}`

- [ ] **5.2** Testar login:
  ```bash
  curl -X POST https://SUA-URL.ondigitalocean.app/api/v1/auth/login \
    -H "Content-Type: application/json" \
    -d '{"email":"admin@tradingplatform.com","password":"Admin123!@#"}'
  ```

- [ ] **5.3** Testar bots:
  ```bash
  curl https://SUA-URL.ondigitalocean.app/api/v1/bots/available
  ```

---

## 🚨 **SE ALGO DER ERRADO**

### **Erro: Database Connection Failed**
- Verificar se `DATABASE_URL` está correta
- Verificar se Supabase está online
- Ajustar `DB_POOL_SIZE=3` e `DB_MAX_OVERFLOW=7`

### **Erro: Redis Connection Failed**
- Verificar se `REDIS_URL` está correta
- Verificar se Redis database está rodando
- Testar Redis: `redis-cli -u "SUA_REDIS_URL" ping`

### **Erro: 502 Bad Gateway**
- Verificar logs da aplicação
- Verificar se porta está correta (`$PORT`)
- Verificar se build completou com sucesso

### **Erro: CORS Blocked**
- Adicionar domínio do frontend em `CORS_ORIGINS`
- Formato: `["https://seu-frontend.com"]`

---

## 📊 **RESUMO FINAL**

**Tempo estimado total**: ~1 hora

**Custos mensais**:
- Digital Ocean App (Basic): $5/mês
- Digital Ocean Redis: $7-15/mês
- **OU** Upstash Redis: Grátis
- **Total**: $5-20/mês

**Próximos passos após deploy**:
1. Configurar domínio customizado (opcional)
2. Configurar SSL/HTTPS (automático na Digital Ocean)
3. Configurar frontend para apontar para nova URL
4. Testar webhooks TradingView

---

**✅ CHECKLIST PRONTO PARA USO**
**📅 Gerado em**: 21/10/2025

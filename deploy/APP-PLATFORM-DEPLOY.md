# 🚀 DEPLOY NO APP PLATFORM - DigitalOcean

**MÉTODO RECOMENDADO:** Muito mais simples que Droplet!

**Tempo**: 10-15 minutos
**Custo**: ~$12-15/mês (com database)
**Dificuldade**: Fácil (apenas cliques!)

---

## 🎯 VANTAGENS DO APP PLATFORM

✅ **Deploy automático** do Git
✅ **SSL/HTTPS grátis** e automático
✅ **Escala automática**
✅ **Zero configuração** de servidor
✅ **Rollback** com 1 clique
✅ **Logs integrados**
✅ **CI/CD built-in**

---

## 📋 PASSO A PASSO

### **1. Acesse App Platform**

1. Vá para: https://cloud.digitalocean.com/apps
2. Clique em **"Create App"**

---

### **2. Conectar Repositório GitHub**

1. Escolha: **GitHub**
2. Clique em **"Authorize DigitalOcean"**
3. Selecione o repositório: **Mvmmv86/GlobalAutomation**
4. Branch: **main**
5. Clique em **"Next"**

---

### **3. Configurar Recursos (Resources)**

O App Platform vai detectar automaticamente 2 serviços:

#### **3.1 Backend (Python/FastAPI)**

- **Tipo**: Web Service
- **Nome**: `trading-api`
- **Source Directory**: `apps/api-python/`
- **Build Command**:
  ```bash
  pip install -r requirements.txt
  ```
- **Run Command**:
  ```bash
  uvicorn main:app --host 0.0.0.0 --port 8000
  ```
- **HTTP Port**: `8000`
- **Instance Size**: **Basic ($12/mês - 1GB RAM)**
- **Instance Count**: 1

#### **3.2 Frontend (React/Vite)**

- **Tipo**: Static Site
- **Nome**: `trading-frontend`
- **Source Directory**: `frontend-new/`
- **Build Command**:
  ```bash
  npm install && npm run build
  ```
- **Output Directory**: `dist`

---

### **4. Configurar Variáveis de Ambiente**

Clique em **"Environment Variables"** para o **backend**:

#### **Variáveis OBRIGATÓRIAS:**

```bash
# 1. Aplicação
ENV=production
DEBUG=false
PORT=8000

# 2. SECRET_KEY (GERE AGORA!)
# Abra terminal e execute:
# python3 -c "import secrets; print(secrets.token_urlsafe(64))"
SECRET_KEY=COLE_AQUI_O_SECRET_GERADO

# 3. ENCRYPTION_KEY (GERE AGORA!)
# pip install cryptography
# python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
ENCRYPTION_KEY=COLE_AQUI_ENCRYPTION_KEY

# 4. DATABASE_URL (Supabase)
# Acesse: https://supabase.com/dashboard/project/_/settings/database
# Copie Connection String (Transaction mode)
DATABASE_URL=postgresql+asyncpg://postgres.xxxxx:SENHA@aws-0-sa-east-1.pooler.supabase.com:6543/postgres

# 5. TV_WEBHOOK_SECRET (GERE AGORA!)
# python3 -c "import secrets; print(secrets.token_hex(32))"
TV_WEBHOOK_SECRET=COLE_AQUI_WEBHOOK_SECRET

# 6. CORS (App Platform vai dar um domínio automaticamente)
CORS_ORIGINS=["https://trading-frontend-xxxxx.ondigitalocean.app"]
ALLOWED_HOSTS=["trading-api-xxxxx.ondigitalocean.app"]

# 7. JWT
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# 8. Redis (opcional - ou use Redis do App Platform)
REDIS_URL=redis://localhost:6379/0

# 9. Rate Limiting
RATE_LIMIT_PER_MINUTE=100
WEBHOOK_RATE_LIMIT_PER_MINUTE=200
```

**Marque como "Encrypted"** todas as senhas/secrets!

---

### **5. Configurar Frontend .env**

No **frontend**, adicione:

```bash
# API URL será o domínio do backend
# Exemplo: https://trading-api-xxxxx.ondigitalocean.app
VITE_API_URL=${trading-api.PUBLIC_URL}/api/v1
VITE_NODE_ENV=production
VITE_APP_NAME=Trading Platform
```

**DICA:** Use a variável `${trading-api.PUBLIC_URL}` para referenciar automaticamente o backend!

---

### **6. Configurar Database (Opcional)**

Se quiser usar database do DigitalOcean em vez de Supabase:

1. Clique em **"Add Resource"**
2. Escolha: **Database**
3. Engine: **PostgreSQL**
4. Plan: **Basic ($15/mês)**
5. Nome: `trading-db`

O App Platform vai criar automaticamente a variável `${trading-db.DATABASE_URL}`

---

### **7. Revisar e Criar**

1. **Região**: Escolha **New York** ou **San Francisco** (mais próximas do Brasil com App Platform)
2. **Nome do App**: `globalautomation-trading`
3. **Review**: Verifique tudo
4. Clique em **"Create Resources"**

---

### **8. Aguardar Deploy (5-10 min)**

O App Platform vai:
1. ✅ Clonar o repositório
2. ✅ Instalar dependências
3. ✅ Build backend e frontend
4. ✅ Provisionar SSL
5. ✅ Deploy completo

**Status:** Acompanhe em tempo real na página!

---

### **9. Testar Sistema**

Após deploy, você vai ter:

```
Frontend: https://trading-frontend-xxxxx.ondigitalocean.app
Backend:  https://trading-api-xxxxx.ondigitalocean.app
```

**Testar:**
1. Acesse frontend no navegador
2. Teste API: `https://trading-api-xxxxx.ondigitalocean.app/health`
3. Veja docs: `https://trading-api-xxxxx.ondigitalocean.app/docs`

---

## 🎯 ATUALIZAR CORS APÓS DEPLOY

Depois que o deploy terminar, você vai saber os domínios finais.

**Atualize as variáveis de ambiente:**

```bash
# Backend - Environment Variables
CORS_ORIGINS=["https://trading-frontend-xxxxx.ondigitalocean.app","https://globalautomation-trading.ondigitalocean.app"]
ALLOWED_HOSTS=["trading-api-xxxxx.ondigitalocean.app"]
```

Salve e o App Platform vai fazer **redeploy automático**!

---

## 🔄 DEPLOYS FUTUROS (AUTOMÁTICOS!)

**SUPER SIMPLES:**

```bash
# No seu computador
git add .
git commit -m "minhas mudanças"
git push origin main

# App Platform detecta e faz deploy AUTOMATICAMENTE! 🎉
```

---

## 🌐 CONFIGURAR DOMÍNIO PRÓPRIO (Opcional)

Se você tem `seudominio.com`:

### **1. No App Platform**
1. Vá em **Settings** → **Domains**
2. Clique em **"Add Domain"**
3. Digite: `app.seudominio.com` (frontend)
4. Digite: `api.seudominio.com` (backend)

### **2. No seu DNS**
Adicione os registros CNAME que o App Platform mostrar:

```
CNAME  app   →  trading-frontend-xxxxx.ondigitalocean.app
CNAME  api   →  trading-api-xxxxx.ondigitalocean.app
```

**SSL é automático!** 🔒

---

## 💰 CUSTOS MENSAIS

| Recurso | Custo |
|---------|-------|
| Backend (Basic 1GB) | $12/mês |
| Frontend (Static) | $3/mês |
| **Database (escolha 1):** | |
| → Supabase (grátis) | $0 |
| → DO Postgres Basic | $15/mês |
| **TOTAL (com Supabase)** | **$15/mês** |
| **TOTAL (com DO DB)** | **$30/mês** |

**RECOMENDAÇÃO:** Use **Supabase** (grátis) = **$15/mês total**

---

## ✅ CHECKLIST

- [ ] Repositório GitHub conectado
- [ ] Backend configurado (apps/api-python/)
- [ ] Frontend configurado (frontend-new/)
- [ ] Variáveis de ambiente preenchidas
- [ ] CORS configurado com domínios corretos
- [ ] Deploy executado com sucesso
- [ ] Sistema acessível via HTTPS
- [ ] API respondendo
- [ ] (Opcional) Domínio próprio configurado

---

## 🆘 TROUBLESHOOTING

### **Build falha no backend**
- Veja **Build Logs** no App Platform
- Verifique se `requirements.txt` está correto
- Veja se todas variáveis de ambiente estão setadas

### **Frontend não carrega API**
- Verifique `VITE_API_URL` no frontend
- Confirme CORS no backend
- Teste API diretamente: `https://trading-api-xxxxx.../health`

### **Database não conecta**
- Verifique `DATABASE_URL` (Supabase)
- Teste conexão no Supabase dashboard
- Veja logs do backend no App Platform

---

## 📊 COMANDOS ÚTEIS

### **Ver Logs**
```
App Platform → seu app → Runtime Logs
```

### **Forçar Redeploy**
```
App Platform → seu app → Settings → Force Rebuild
```

### **Rollback**
```
App Platform → seu app → Deployments → escolha versão anterior
```

---

## 🎯 PRÓXIMOS PASSOS

1. ✅ Deploy no App Platform (este guia)
2. 🔒 Configurar domínio próprio (opcional)
3. 📊 Habilitar alertas de performance
4. 💾 Configurar backups automáticos (se usar DO Database)
5. 🚀 Escalar instâncias se necessário

---

**MUITO MAIS FÁCIL QUE DROPLET!** 🎉

**Precisa de ajuda?**
- Docs: https://docs.digitalocean.com/products/app-platform/
- Support: Via DigitalOcean dashboard

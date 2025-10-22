# 🎯 ADICIONAR VARIÁVEIS DE AMBIENTE - PASSO A PASSO

## ✅ STATUS ATUAL:
- ✅ **App deployed**: https://globalautomation-tqu2m.ondigitalocean.app
- ✅ **API respondendo**: /health funcionando
- ⚠️ **Configuração incompleta**: Falta adicionar env vars

---

## 📋 PRÓXIMO PASSO (5 MINUTOS):

### **1. Abrir arquivo de variáveis**

Abra o arquivo: **DIGITAL_OCEAN_ENV_FINAL.txt**

Esse arquivo contém TODAS as 27 variáveis de ambiente já configuradas com:
- ✅ URL correta do seu app: `globalautomation-tqu2m.ondigitalocean.app`
- ✅ Redis URL do Upstash
- ✅ Database URL do Supabase
- ✅ Todas as secrets (JWT, encryption, etc)

### **2. Copiar TUDO do arquivo**

1. Abrir: `/home/globalauto/global/DIGITAL_OCEAN_ENV_FINAL.txt`
2. Selecionar TUDO (Ctrl+A)
3. Copiar (Ctrl+C)

### **3. Colar na Digital Ocean**

1. Digital Ocean → Ir para o seu app: **globalautomation**
2. Click na aba **"Settings"**
3. Procurar seção **"Environment Variables"** ou **"App-Level Environment Variables"**
4. Click em **"Edit"** ou **"Bulk Editor"** (modo texto)
5. **COLAR** todo o conteúdo copiado
6. Click em **"Save"** ou **"Encrypt and Save"**

### **4. Aguardar restart (2 minutos)**

Depois de salvar:
- O app vai **reiniciar automaticamente**
- Aguarde 1-2 minutos
- O status vai mudar para "Deploying" → "Running"

---

## ✅ COMO SABER QUE FUNCIONOU:

### **Teste 1: Endpoint /health**

Acesse no navegador:
```
https://globalautomation-tqu2m.ondigitalocean.app/health
```

**Deve mostrar**:
```json
{
  "service": "TradingView Gateway API",
  "version": "1.0.0",
  "environment": "production",  ← MUDOU DE "development" PARA "production"
  "status": "healthy",
  "database": "asyncpg (pgBouncer transaction mode)"
}
```

### **Teste 2: Runtime Logs**

Nos logs, deve SUMIR os erros:
- ✅ **SEM** "Error 111 connecting to localhost:6379"
- ✅ **SEM** "Binance connector initialized in DEMO mode"
- ✅ Ver "Redis connected successfully" ou similar

---

## 📊 VARIÁVEIS QUE SERÃO ADICIONADAS:

Total: **27 variáveis**

**Principais**:
- `ENV=production` ← Muda de development para production
- `REDIS_URL=rediss://...upstash.io:6379` ← Corrige erro Redis
- `DATABASE_URL=postgresql+asyncpg://...` ← Supabase
- `CORS_ORIGINS=["https://globalautomation-tqu2m.ondigitalocean.app",...]` ← Permite frontend
- `API_BASE_URL=https://globalautomation-tqu2m.ondigitalocean.app` ← URL correta
- `ENCRYPTION_MASTER_KEY=...` ← Descriptografia das API keys da Binance
- `SECRET_KEY=...` ← JWT tokens
- E mais 20 variáveis...

---

## ⏰ TEMPO ESTIMADO:

| Passo | Tempo |
|-------|-------|
| Copiar arquivo | 30 segundos |
| Ir em Settings → Env Vars | 1 minuto |
| Colar e salvar | 1 minuto |
| Aguardar restart | 2 minutos |
| **TOTAL** | **~5 minutos** |

---

## 🚨 IMPORTANTE:

- **NÃO EDITE** as variáveis manualmente (use Bulk Editor)
- **COLE TODAS** de uma vez (não uma por uma)
- **AGUARDE** o restart completar antes de testar

---

## 🎯 DEPOIS DE ADICIONAR:

1. Teste `/health` (deve mostrar "production")
2. Teste `/docs` (documentação da API)
3. Verifique Runtime Logs (sem erros Redis)
4. Pronto para usar! 🎉

---

**ADICIONE AS VARIÁVEIS AGORA E ME AVISE QUANDO TERMINAR!** 🚀

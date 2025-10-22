# 🚀 GUIA COMPLETO: DEPLOY DO FRONTEND NA DIGITAL OCEAN

## ✅ PRÉ-REQUISITOS (JÁ FEITOS):
- ✅ Backend deployed: `https://globalautomation-tqu2m.ondigitalocean.app`
- ✅ Conta Digital Ocean ativa
- ✅ Repositório GitHub: `Mvmmv86/GlobalAutomation`

---

## 📋 PASSO A PASSO COMPLETO (15-20 minutos)

### **PARTE 1: CRIAR NOVO APP NA DIGITAL OCEAN (5 min)**

#### **1.1. Acessar Digital Ocean**
- Ir para: https://cloud.digitalocean.com/
- Login com sua conta

#### **1.2. Criar Novo App**
1. Click em **"Create"** (canto superior direito)
2. Selecionar **"Apps"**
3. Ou ir direto em: **Apps** → **"Create App"**

#### **1.3. Conectar ao GitHub**
1. **Source**: Selecionar **"GitHub"**
2. Se aparecer para conectar: Click em **"Connect GitHub Account"**
3. Autorizar Digital Ocean a acessar seus repositórios

#### **1.4. Selecionar Repositório**
1. **Repository**: `Mvmmv86/GlobalAutomation`
2. **Branch**: `main`
3. **Source Directory**: `/frontend-new` ← **IMPORTANTE!**
4. **Autodeploy**: ✅ Marcar (para deploy automático)
5. Click em **"Next"**

---

### **PARTE 2: CONFIGURAR BUILD SETTINGS (3 min)**

#### **2.1. Configurar Tipo de Recurso**
1. **Resource Type**: Selecionar **"Static Site"** (não "Web Service")
2. **Name**: `global-frontend` (ou nome de sua preferência)
3. **Branch**: `main` (confirmar)

#### **2.2. Configurar Build Command**

**Build Command** (cole exatamente isto):
```bash
npm install && npm run build
```

**Output Directory** (cole exatamente isto):
```
dist
```

#### **2.3. HTTP Routes**
- **Catchall Route**: `/` → `index.html` (já vem configurado)
- Deixar como está

#### **2.4. Click em "Next"**

---

### **PARTE 3: CONFIGURAR PLANO E REGIÃO (1 min)**

#### **3.1. Escolher Plano**
- **Plan**: Selecionar **"Starter"** (FREE ou $5/mês)
- **Region**: `New York` ou `San Francisco` (mesma região do backend se possível)

#### **3.2. Click em "Next"**

---

### **PARTE 4: ADICIONAR VARIÁVEIS DE AMBIENTE (5 min)**

#### **4.1. Na seção "Environment Variables"**

Click em **"Edit"** ou **"Add Variable"**

#### **4.2. Adicionar as 2 variáveis:**

**Variável 1:**
```
Key: VITE_API_URL
Value: https://globalautomation-tqu2m.ondigitalocean.app
```

**Variável 2:**
```
Key: VITE_WEBHOOK_PUBLIC_URL
Value: https://globalautomation-tqu2m.ondigitalocean.app
```

⚠️ **IMPORTANTE**: Use a URL **SEM** a barra `/` no final!

#### **4.3. Salvar Variáveis**

---

### **PARTE 5: REVISAR E CRIAR APP (1 min)**

#### **5.1. Revisar Configurações**

Confirme que está assim:
- ✅ **Source**: `Mvmmv86/GlobalAutomation` branch `main` directory `/frontend-new`
- ✅ **Type**: Static Site
- ✅ **Build Command**: `npm install && npm run build`
- ✅ **Output Directory**: `dist`
- ✅ **Environment Variables**: 2 variáveis (VITE_API_URL, VITE_WEBHOOK_PUBLIC_URL)
- ✅ **Autodeploy**: Enabled

#### **5.2. Click em "Create Resources"**

Digital Ocean vai:
1. Criar o app
2. Iniciar o primeiro build
3. Fazer deploy automaticamente

---

### **PARTE 6: AGUARDAR BUILD (5-8 min)**

#### **6.1. Acompanhar o Build**

1. Você será redirecionado para a página do app
2. Ver status: **"Building..."**
3. Click em **"View Logs"** ou **"Build Logs"** para acompanhar

#### **6.2. O que esperar nos logs:**

```
✓ Cloning repository...
✓ Installing dependencies... (npm install)
✓ Building application... (npm run build)
  Creating optimized production build...
  Transforming files...
  Rendering pages...
✓ Build complete!
✓ Deploying static files...
✓ Deployment successful!
```

#### **6.3. Aguardar Status "Live"**

Quando terminar, o status muda para **"Live"** ou **"Running"**

---

### **PARTE 7: COPIAR URL DO FRONTEND (1 min)**

#### **7.1. Pegar a URL do Frontend**

Na página do app, procure pela URL:
```
https://global-frontend-xxxxx.ondigitalocean.app
```

Ou algo tipo:
```
https://seu-app.ondigitalocean.app
```

#### **7.2. COPIAR ESSA URL**

Você vai precisar dela para atualizar o CORS do backend!

---

### **PARTE 8: ATUALIZAR CORS DO BACKEND (2 min)**

#### **8.1. Ir no App do Backend**

1. Digital Ocean → Apps → **"globalautomation"** (backend)
2. Settings → Environment Variables
3. Click em **"Edit"** ou **"Bulk Editor"**

#### **8.2. Atualizar variável CORS_ORIGINS**

Procure pela variável:
```
CORS_ORIGINS=["https://globalautomation-tqu2m.ondigitalocean.app","http://localhost:3000"]
```

Adicione a URL do frontend:
```
CORS_ORIGINS=["https://globalautomation-tqu2m.ondigitalocean.app","https://global-frontend-xxxxx.ondigitalocean.app","http://localhost:3000"]
```

⚠️ **Substitua** `global-frontend-xxxxx.ondigitalocean.app` pela URL REAL do seu frontend!

#### **8.3. Salvar e Aguardar Restart**

Click em **"Save"** - Backend vai reiniciar (2 min)

---

### **PARTE 9: TESTAR O FRONTEND (2 min)**

#### **9.1. Abrir Frontend no Navegador**

```
https://global-frontend-xxxxx.ondigitalocean.app
```

**Deve aparecer**:
- ✅ Página de login
- ✅ Logo da aplicação
- ✅ Campos de usuário e senha
- ✅ Sem erros no console do navegador

#### **9.2. Testar Login (Opcional)**

Se você tiver usuário cadastrado:
1. Tentar fazer login
2. Deve conectar no backend
3. Redirecionar para dashboard

#### **9.3. Verificar Console do Navegador**

Abrir DevTools (F12) → Console

**✅ SUCESSO - Deve mostrar**:
- Sem erros de CORS
- Sem erros de conexão
- Requisições para `https://globalautomation-tqu2m.ondigitalocean.app` funcionando

**❌ SE DER ERRO**:
- `CORS policy`: Volte e verifique se adicionou a URL do frontend no CORS_ORIGINS do backend

---

## 🎉 PRONTO! SISTEMA COMPLETO DEPLOYED!

### **URLs Finais:**

| Componente | URL |
|------------|-----|
| **Backend API** | `https://globalautomation-tqu2m.ondigitalocean.app` |
| **Frontend Web** | `https://global-frontend-xxxxx.ondigitalocean.app` |
| **Docs API** | `https://globalautomation-tqu2m.ondigitalocean.app/docs` |

---

## 📝 CHECKLIST FINAL:

- [ ] Frontend deployed e status "Live"
- [ ] URL do frontend copiada
- [ ] CORS_ORIGINS do backend atualizado com URL do frontend
- [ ] Frontend abre no navegador sem erros
- [ ] Login funciona (se tiver usuário)
- [ ] Dashboard carrega (se tiver acesso)

---

## ⚠️ PROBLEMAS COMUNS:

### **Problema 1: Build falha com "Module not found"**
**Solução**: Verificar se `package.json` tem todas as dependências. Rodar `npm install` localmente primeiro.

### **Problema 2: Página em branco**
**Solução**:
1. Verificar se `Output Directory` está como `dist`
2. Verificar se `Build Command` está correto
3. Ver logs de build para erros

### **Problema 3: Erro CORS ao fazer login**
**Solução**:
1. Adicionar URL do frontend em `CORS_ORIGINS` do backend
2. Aguardar backend reiniciar (2 min)
3. Tentar novamente

### **Problema 4: "Failed to fetch" ao conectar API**
**Solução**:
1. Verificar se `VITE_API_URL` está correto (URL do backend)
2. Verificar se backend está rodando (status "Running")
3. Testar backend diretamente: `https://globalautomation-tqu2m.ondigitalocean.app/health`

---

## 🚀 PRÓXIMOS PASSOS APÓS DEPLOY:

1. ✅ Criar usuário admin (se não tiver)
2. ✅ Configurar exchange accounts (Binance API keys)
3. ✅ Criar webhooks do TradingView
4. ✅ Testar fluxo completo de trading

---

**AGORA SIGA OS PASSOS ACIMA E ME AVISE QUANDO CHEGAR EM CADA PARTE!** 🎯

Vou te ajudar se tiver alguma dúvida ou problema!

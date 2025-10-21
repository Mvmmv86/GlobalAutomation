# 🚀 GUIA COMPLETO DE DEPLOY - DigitalOcean

**Sistema**: GlobalAutomation Trading Platform
**Servidor**: Ubuntu 22.04 LTS
**RAM**: 1GB (mínimo) | 2GB (recomendado)
**Tempo total**: 30-45 minutos

---

## 📋 ÍNDICE

1. [Criar Droplet](#1-criar-droplet)
2. [Conectar via SSH](#2-conectar-via-ssh)
3. [Setup do Servidor](#3-setup-do-servidor)
4. [Clonar Projeto](#4-clonar-projeto)
5. [Configurar Credenciais](#5-configurar-credenciais)
6. [Deploy Backend](#6-deploy-backend)
7. [Deploy Frontend](#7-deploy-frontend)
8. [Testar Sistema](#8-testar-sistema)
9. [Configurar Domínio (Opcional)](#9-configurar-domínio-opcional)
10. [SSL/HTTPS (Opcional)](#10-ssl-https-opcional)

---

## 1. Criar Droplet

Siga o guia: `01-CRIAR-DROPLET.md`

**Resumo:**
1. Acesse: https://cloud.digitalocean.com/
2. Clique em "Create" → "Droplets"
3. Escolha: Ubuntu 22.04 (LTS) x64
4. Plano: Basic $6/mês (1GB RAM)
5. Região: São Paulo 1
6. Autenticação: SSH Key (recomendado)
7. Hostname: `trading-platform-prod`
8. Clique em "Create Droplet"

**Anote o IP:** `___.___.___.___ ` (exemplo: 64.225.123.45)

---

## 2. Conectar via SSH

```bash
# Substitua pelo seu IP
ssh root@SEU-IP-AQUI

# Exemplo:
ssh root@64.225.123.45
```

Se aparecer pergunta sobre "authenticity", digite: `yes`

---

## 3. Setup do Servidor

```bash
# Baixar o script de setup
curl -O https://raw.githubusercontent.com/Mvmmv86/GlobalAutomation/main/deploy/02-SETUP-SERVER.sh

# OU se já clonou o projeto:
# git clone https://github.com/Mvmmv86/GlobalAutomation.git
# cd GlobalAutomation

# Executar setup (demora ~10-15 minutos)
bash 02-SETUP-SERVER.sh
```

**O que este script faz:**
- ✅ Instala Python 3.11
- ✅ Instala Node.js 18
- ✅ Instala PM2 (gerenciador de processos)
- ✅ Instala Nginx (servidor web)
- ✅ Configura Firewall (UFW)
- ✅ Cria Swap de 2GB (ajuda com 1GB RAM)
- ✅ Instala Git, Certbot e dependências

---

## 4. Clonar Projeto

```bash
# Ir para diretório de apps
cd /opt/trading-platform

# Clonar repositório
git clone https://github.com/Mvmmv86/GlobalAutomation.git

# Entrar no projeto
cd GlobalAutomation

# Verificar branch
git branch
```

---

## 5. Configurar Credenciais

### **5.1 Copiar Template do .env**

```bash
cp deploy/.env.production.example apps/api-python/.env
```

### **5.2 Gerar Secrets Fortes**

```bash
# SECRET_KEY (64 caracteres)
python3.11 -c "import secrets; print(secrets.token_urlsafe(64))"

# ENCRYPTION_KEY (32 bytes base64)
python3.11 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# TV_WEBHOOK_SECRET (32 caracteres hex)
python3.11 -c "import secrets; print(secrets.token_hex(32))"
```

### **5.3 Editar .env**

```bash
nano apps/api-python/.env
```

**Preencha estes campos OBRIGATÓRIOS:**

```bash
# 1. SECRET_KEY (cole o gerado acima)
SECRET_KEY=cole_aqui_o_secret_key_de_64_caracteres

# 2. ENCRYPTION_KEY (cole o gerado acima)
ENCRYPTION_KEY=cole_aqui_encryption_key_32_bytes_base64

# 3. DATABASE_URL (Supabase)
# Acesse: https://supabase.com/dashboard/project/_/settings/database
# Copie a "Connection String" (Transaction mode)
DATABASE_URL=postgresql+asyncpg://postgres.xxxxx:SUA_SENHA@aws-0-sa-east-1.pooler.supabase.com:6543/postgres

# 4. TV_WEBHOOK_SECRET (cole o gerado acima)
TV_WEBHOOK_SECRET=cole_aqui_webhook_secret

# 5. CORS_ORIGINS (ajuste para seu IP ou domínio)
CORS_ORIGINS=["http://SEU-IP","http://localhost:3000"]
```

**Salvar:** `Ctrl + O`, `Enter`, `Ctrl + X`

---

## 6. Deploy Backend

```bash
# Executar script de deploy do backend
bash deploy/03-DEPLOY-BACKEND.sh
```

**O que acontece:**
1. Cria virtual environment Python
2. Instala dependências (requirements.txt)
3. Testa configuração
4. Inicia backend com PM2
5. Configura auto-sync
6. Testa health check

**Verificar:**
```bash
# Ver status
pm2 status

# Ver logs
pm2 logs trading-api --lines 50

# Testar API
curl http://localhost:8000/health
```

Deve retornar: `{"status":"healthy"}`

---

## 7. Deploy Frontend

```bash
# Executar script de deploy do frontend
bash deploy/04-DEPLOY-FRONTEND.sh
```

**O que acontece:**
1. Cria .env do frontend (com API_URL)
2. Instala dependências npm
3. Build de produção (Vite)
4. Configura Nginx
5. Testa frontend

**Verificar:**
```bash
# Ver status Nginx
systemctl status nginx

# Testar frontend
curl http://localhost/
```

---

## 8. Testar Sistema

### **8.1 Testar no Navegador**

Acesse: `http://SEU-IP/`

Você deve ver a tela de login do Trading Platform!

### **8.2 Testar API**

```bash
# Health check
curl http://SEU-IP/api/v1/health

# Docs interativa
# Acesse no navegador: http://SEU-IP/api/v1/docs
```

### **8.3 Ver Logs**

```bash
# Backend
pm2 logs trading-api

# Nginx
tail -f /var/log/nginx/access.log

# Sistema
pm2 monit
```

---

## 9. Configurar Domínio (Opcional)

Se você tem um domínio (ex: `seudominio.com`):

### **9.1 Configurar DNS**

No painel do seu provedor de domínio:

```
Tipo: A
Nome: @
Valor: SEU-IP-DO-DROPLET
TTL: 3600

Tipo: A
Nome: api
Valor: SEU-IP-DO-DROPLET
TTL: 3600

Tipo: A
Nome: app
Valor: SEU-IP-DO-DROPLET
TTL: 3600
```

### **9.2 Atualizar Frontend .env**

```bash
nano /opt/trading-platform/GlobalAutomation/frontend-new/.env
```

Altere:
```bash
VITE_API_URL=https://api.seudominio.com/api/v1
```

Rebuild frontend:
```bash
cd /opt/trading-platform/GlobalAutomation/frontend-new
npm run build
systemctl reload nginx
```

---

## 10. SSL/HTTPS (Opcional)

**Com domínio configurado**, instale SSL grátis:

```bash
# Instalar certificado SSL (Let's Encrypt)
certbot --nginx -d seudominio.com -d api.seudominio.com -d app.seudominio.com

# Seguir instruções
# Email: seu@email.com
# Agree: Y
# Redirect HTTP → HTTPS: Y
```

Pronto! Seu site agora tem HTTPS! 🔒

---

## ✅ CHECKLIST FINAL

- [ ] Droplet criado e acessível via SSH
- [ ] Setup executado (Python, Node, Nginx, PM2)
- [ ] Projeto clonado
- [ ] .env configurado com credenciais reais
- [ ] Backend rodando (pm2 status)
- [ ] Frontend buildado e servido pelo Nginx
- [ ] Sistema acessível em http://SEU-IP/
- [ ] API respondendo em http://SEU-IP/api/v1/health
- [ ] (Opcional) Domínio configurado
- [ ] (Opcional) SSL/HTTPS ativo

---

## 🔧 COMANDOS ÚTEIS

### **PM2 (Backend)**
```bash
pm2 status                      # Ver status
pm2 logs trading-api            # Ver logs do backend
pm2 logs trading-sync           # Ver logs do sync
pm2 restart trading-api         # Reiniciar backend
pm2 stop trading-api            # Parar backend
pm2 monit                       # Monitor em tempo real
```

### **Nginx (Frontend)**
```bash
systemctl status nginx          # Status do Nginx
systemctl reload nginx          # Recarregar config
systemctl restart nginx         # Reiniciar Nginx
tail -f /var/log/nginx/access.log   # Ver acessos
tail -f /var/log/nginx/error.log    # Ver erros
```

### **Sistema**
```bash
free -h                         # Ver uso de RAM
df -h                           # Ver uso de disco
htop                            # Monitor do sistema
ufw status                      # Ver firewall
```

### **Deploy Updates**
```bash
cd /opt/trading-platform/GlobalAutomation
git pull origin main            # Atualizar código
bash deploy/03-DEPLOY-BACKEND.sh   # Redeploy backend
bash deploy/04-DEPLOY-FRONTEND.sh  # Redeploy frontend
```

---

## 🆘 TROUBLESHOOTING

### **Backend não inicia**
```bash
pm2 logs trading-api            # Ver erro
cat apps/api-python/.env        # Verificar credenciais
python3.11 apps/api-python/main.py  # Testar manualmente
```

### **Frontend não aparece**
```bash
systemctl status nginx          # Ver status Nginx
nginx -t                        # Testar config
ls frontend-new/dist/           # Verificar se build existe
```

### **Sem memória (1GB RAM)**
```bash
free -h                         # Ver RAM
swapon --show                   # Ver swap
pm2 restart all                 # Reiniciar processos
```

### **API não conecta**
```bash
# Ver se backend está ouvindo
lsof -i:8000

# Testar localmente
curl http://localhost:8000/health

# Ver firewall
ufw status
```

---

## 📊 CUSTOS ESTIMADOS

| Item | Custo/Mês |
|------|-----------|
| Droplet 1GB RAM | $6.00 |
| Bandwidth (1TB incluído) | $0.00 |
| **TOTAL** | **$6.00/mês** |

**Upgrades opcionais:**
- Droplet 2GB RAM: $12/mês (melhor performance)
- Backups automáticos: +20% ($1.20)
- Managed Database: +$15/mês

---

## 🎯 PRÓXIMOS PASSOS

1. **Monitoramento**: Configure alertas no DigitalOcean
2. **Backups**: Habilite backups automáticos (Droplet settings)
3. **Domínio**: Compre domínio e configure DNS
4. **SSL**: Instale certificado Let's Encrypt
5. **Segurança**: Configure fail2ban, SSH key-only
6. **Performance**: Monitore uso de RAM, considere upgrade se necessário

---

**Dúvidas?**
- Documentação DigitalOcean: https://docs.digitalocean.com
- PM2 Docs: https://pm2.keymetrics.io/docs
- Nginx Docs: https://nginx.org/en/docs

**Pronto para produção!** 🚀

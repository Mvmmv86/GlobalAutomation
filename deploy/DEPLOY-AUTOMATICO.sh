#!/bin/bash
# ========================================
# DEPLOY AUTOMÁTICO COMPLETO
# GlobalAutomation - DigitalOcean
# ========================================
# Este script faz TUDO automaticamente:
# 1. Setup do servidor
# 2. Clone do projeto
# 3. Deploy backend
# 4. Deploy frontend
#
# IMPORTANTE: Execute como root no servidor limpo
# TEMPO: 20-30 minutos

set -e  # Parar em caso de erro

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=========================================${NC}"
echo -e "${BLUE}🚀 DEPLOY AUTOMÁTICO - GlobalAutomation${NC}"
echo -e "${BLUE}=========================================${NC}"
echo ""

# ========================================
# VERIFICAÇÕES INICIAIS
# ========================================
echo -e "${YELLOW}📋 Verificando requisitos...${NC}"

# Verificar se é root
if [ "$EUID" -ne 0 ]; then
   echo -e "${RED}❌ Execute como root: sudo bash DEPLOY-AUTOMATICO.sh${NC}"
   exit 1
fi

# Verificar sistema operacional
if [ ! -f /etc/lsb-release ]; then
    echo -e "${RED}❌ Este script é para Ubuntu 22.04${NC}"
    exit 1
fi

source /etc/lsb-release
if [ "$DISTRIB_RELEASE" != "22.04" ]; then
    echo -e "${YELLOW}⚠️  Aviso: Testado apenas em Ubuntu 22.04. Você está usando $DISTRIB_RELEASE${NC}"
    read -p "Continuar mesmo assim? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

echo -e "${GREEN}✅ Sistema verificado${NC}"
echo ""

# ========================================
# CONFIGURAÇÃO INTERATIVA
# ========================================
echo -e "${BLUE}=========================================${NC}"
echo -e "${BLUE}⚙️  CONFIGURAÇÃO${NC}"
echo -e "${BLUE}=========================================${NC}"
echo ""

# Perguntar credenciais necessárias
echo -e "${YELLOW}Vamos configurar as credenciais necessárias.${NC}"
echo -e "${YELLOW}Você precisará de:${NC}"
echo "  1. URL do banco Supabase (Connection String)"
echo "  2. Secrets de segurança (vou gerar automaticamente)"
echo ""

read -p "Pressione ENTER para continuar..."
echo ""

# Supabase Database URL
echo -e "${BLUE}1. DATABASE URL (Supabase)${NC}"
echo "Acesse: https://supabase.com/dashboard/project/_/settings/database"
echo "Copie a 'Connection String' (Transaction mode)"
echo ""
read -p "Cole aqui: " DATABASE_URL

if [ -z "$DATABASE_URL" ]; then
    echo -e "${RED}❌ DATABASE_URL é obrigatório!${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Database URL configurado${NC}"
echo ""

# Gerar secrets automaticamente
echo -e "${BLUE}2. Gerando secrets de segurança...${NC}"

# Instalar Python temporariamente se necessário
if ! command -v python3 &> /dev/null; then
    apt update -qq
    apt install -y python3 python3-pip -qq
fi

# Gerar SECRET_KEY
SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(64))")
echo -e "${GREEN}✅ SECRET_KEY gerado${NC}"

# Gerar ENCRYPTION_KEY
pip3 install cryptography -qq 2>/dev/null || true
ENCRYPTION_KEY=$(python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
echo -e "${GREEN}✅ ENCRYPTION_KEY gerado${NC}"

# Gerar TV_WEBHOOK_SECRET
TV_WEBHOOK_SECRET=$(python3 -c "import secrets; print(secrets.token_hex(32))")
echo -e "${GREEN}✅ TV_WEBHOOK_SECRET gerado${NC}"

echo ""

# Obter IP público
PUBLIC_IP=$(curl -s http://ifconfig.me)
echo -e "${BLUE}3. IP Público detectado: ${PUBLIC_IP}${NC}"
echo ""

# ========================================
# FASE 1: ATUALIZAR SISTEMA
# ========================================
echo -e "${BLUE}=========================================${NC}"
echo -e "${BLUE}📦 FASE 1/7: Atualizando sistema${NC}"
echo -e "${BLUE}=========================================${NC}"

apt update
DEBIAN_FRONTEND=noninteractive apt upgrade -y -qq

echo -e "${GREEN}✅ Sistema atualizado${NC}"
echo ""

# ========================================
# FASE 2: INSTALAR DEPENDÊNCIAS
# ========================================
echo -e "${BLUE}=========================================${NC}"
echo -e "${BLUE}🔧 FASE 2/7: Instalando dependências${NC}"
echo -e "${BLUE}=========================================${NC}"

# Python 3.11
echo "  🐍 Instalando Python 3.11..."
apt install -y software-properties-common -qq
add-apt-repository -y ppa:deadsnakes/ppa
apt update -qq
apt install -y python3.11 python3.11-venv python3.11-dev python3-pip build-essential libssl-dev libffi-dev -qq

# Node.js 18
echo "  📗 Instalando Node.js 18..."
curl -fsSL https://deb.nodesource.com/setup_18.x | bash - > /dev/null 2>&1
apt install -y nodejs -qq

# PM2
echo "  ⚙️  Instalando PM2..."
npm install -g pm2 > /dev/null 2>&1

# Nginx
echo "  🌐 Instalando Nginx..."
apt install -y nginx -qq

# Certbot
echo "  🔒 Instalando Certbot..."
apt install -y certbot python3-certbot-nginx -qq

# Git
echo "  📚 Instalando Git..."
apt install -y git curl wget unzip htop nano vim -qq

# UFW
echo "  🔥 Configurando Firewall..."
apt install -y ufw -qq
ufw --force enable > /dev/null 2>&1
ufw allow 22/tcp > /dev/null 2>&1
ufw allow 80/tcp > /dev/null 2>&1
ufw allow 443/tcp > /dev/null 2>&1

# Swap
echo "  💿 Configurando Swap (2GB)..."
if [ $(swapon --show | wc -l) -eq 0 ]; then
    fallocate -l 2G /swapfile
    chmod 600 /swapfile
    mkswap /swapfile > /dev/null 2>&1
    swapon /swapfile
    echo '/swapfile none swap sw 0 0' >> /etc/fstab
    sysctl vm.swappiness=10 > /dev/null 2>&1
    echo 'vm.swappiness=10' >> /etc/sysctl.conf
fi

# Iniciar serviços
systemctl start nginx
systemctl enable nginx > /dev/null 2>&1
pm2 startup systemd -u root --hp /root > /dev/null 2>&1

echo -e "${GREEN}✅ Todas as dependências instaladas${NC}"
echo ""

# ========================================
# FASE 3: CLONAR PROJETO
# ========================================
echo -e "${BLUE}=========================================${NC}"
echo -e "${BLUE}📁 FASE 3/7: Clonando projeto${NC}"
echo -e "${BLUE}=========================================${NC}"

mkdir -p /opt/trading-platform
cd /opt/trading-platform

if [ -d "GlobalAutomation" ]; then
    echo "  📁 Projeto já existe, atualizando..."
    cd GlobalAutomation
    git pull origin main
else
    echo "  📥 Clonando repositório..."
    git clone https://github.com/Mvmmv86/GlobalAutomation.git
    cd GlobalAutomation
fi

echo -e "${GREEN}✅ Projeto clonado${NC}"
echo ""

# ========================================
# FASE 4: CONFIGURAR .ENV
# ========================================
echo -e "${BLUE}=========================================${NC}"
echo -e "${BLUE}⚙️  FASE 4/7: Configurando .env${NC}"
echo -e "${BLUE}=========================================${NC}"

cat > apps/api-python/.env << EOF
# ========================================
# GLOBALAUTOMATION - PRODUÇÃO
# Gerado automaticamente em $(date)
# ========================================

# Aplicação
ENV=production
DEBUG=false
PORT=8000
VERSION=1.0.0

# Secrets (gerados automaticamente)
SECRET_KEY=${SECRET_KEY}
ENCRYPTION_KEY=${ENCRYPTION_KEY}
TV_WEBHOOK_SECRET=${TV_WEBHOOK_SECRET}

# JWT
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# Database (Supabase)
DATABASE_URL=${DATABASE_URL}
DB_POOL_SIZE=10
DB_MAX_OVERFLOW=20
DB_POOL_TIMEOUT=30

# Redis (local)
REDIS_URL=redis://localhost:6379/0
REDIS_MAX_CONNECTIONS=10
REDIS_TIMEOUT=5

# CORS (ajuste para seu domínio)
CORS_ORIGINS=["http://${PUBLIC_IP}","http://localhost:3000"]
ALLOWED_HOSTS=["${PUBLIC_IP}","localhost"]

# Rate Limiting
RATE_LIMIT_PER_MINUTE=100
WEBHOOK_RATE_LIMIT_PER_MINUTE=200
AUTH_RATE_LIMIT_PER_MINUTE=500

# Celery
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/1

# Logs
LOG_LEVEL=INFO
LOG_FORMAT=json
EOF

echo -e "${GREEN}✅ .env configurado${NC}"
echo ""

# ========================================
# FASE 5: DEPLOY BACKEND
# ========================================
echo -e "${BLUE}=========================================${NC}"
echo -e "${BLUE}🐍 FASE 5/7: Deploy Backend${NC}"
echo -e "${BLUE}=========================================${NC}"

cd /opt/trading-platform/GlobalAutomation/apps/api-python

# Criar venv
echo "  📦 Criando virtual environment..."
rm -rf venv
python3.11 -m venv venv
source venv/bin/activate

# Instalar dependências
echo "  📥 Instalando dependências..."
pip install --upgrade pip > /dev/null 2>&1
pip install -r requirements.txt > /dev/null 2>&1

# Parar processo antigo
pm2 delete trading-api 2>/dev/null || true
pm2 delete trading-sync 2>/dev/null || true

# Iniciar com PM2
echo "  🚀 Iniciando backend com PM2..."
pm2 start venv/bin/python \
    --name trading-api \
    --interpreter none \
    -- -m uvicorn main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --workers 1 \
    --cwd /opt/trading-platform/GlobalAutomation/apps/api-python

# Iniciar auto_sync
if [ -f "auto_sync.sh" ]; then
    chmod +x auto_sync.sh
    pm2 start auto_sync.sh --name trading-sync
fi

pm2 save > /dev/null 2>&1

# Aguardar inicialização
echo "  ⏳ Aguardando backend iniciar..."
sleep 10

# Testar health check
if curl -f http://localhost:8000/health > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Backend rodando!${NC}"
else
    echo -e "${YELLOW}⚠️  Backend iniciado, mas health check falhou${NC}"
    echo "  Veja logs: pm2 logs trading-api"
fi

echo ""

# ========================================
# FASE 6: DEPLOY FRONTEND
# ========================================
echo -e "${BLUE}=========================================${NC}"
echo -e "${BLUE}📗 FASE 6/7: Deploy Frontend${NC}"
echo -e "${BLUE}=========================================${NC}"

cd /opt/trading-platform/GlobalAutomation/frontend-new

# Criar .env
echo "  ⚙️  Configurando .env do frontend..."
cat > .env << EOF
VITE_API_URL=http://${PUBLIC_IP}:8000/api/v1
VITE_NODE_ENV=production
VITE_APP_NAME=Trading Platform
VITE_APP_VERSION=1.0.0
EOF

# Instalar dependências
echo "  📦 Instalando dependências npm..."
rm -rf node_modules
npm install > /dev/null 2>&1

# Build
echo "  🏗️  Building frontend..."
rm -rf dist
npm run build

if [ ! -d "dist" ]; then
    echo -e "${RED}❌ Build falhou!${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Frontend buildado${NC}"
echo ""

# ========================================
# FASE 7: CONFIGURAR NGINX
# ========================================
echo -e "${BLUE}=========================================${NC}"
echo -e "${BLUE}🌐 FASE 7/7: Configurando Nginx${NC}"
echo -e "${BLUE}=========================================${NC}"

# Criar configuração Nginx
cat > /etc/nginx/sites-available/trading-platform << 'EOF'
server {
    listen 80 default_server;
    listen [::]:80 default_server;
    server_name _;

    # Backend API
    location /api/ {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # CORS
        add_header 'Access-Control-Allow-Origin' '*' always;
        add_header 'Access-Control-Allow-Methods' 'GET, POST, PUT, DELETE, OPTIONS' always;
        add_header 'Access-Control-Allow-Headers' 'Content-Type, Authorization' always;
    }

    # Frontend
    location / {
        root /opt/trading-platform/GlobalAutomation/frontend-new/dist;
        try_files $uri $uri/ /index.html;
        index index.html;

        # Cache assets
        location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$ {
            expires 1y;
            add_header Cache-Control "public, immutable";
        }
    }

    # Gzip compression
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_types text/plain text/css text/xml text/javascript application/x-javascript application/xml+rss application/javascript application/json;
}
EOF

# Remover default e ativar nossa config
rm -f /etc/nginx/sites-enabled/default
ln -sf /etc/nginx/sites-available/trading-platform /etc/nginx/sites-enabled/

# Testar config
echo "  🧪 Testando configuração Nginx..."
nginx -t

if [ $? -eq 0 ]; then
    systemctl reload nginx
    echo -e "${GREEN}✅ Nginx configurado e recarregado${NC}"
else
    echo -e "${RED}❌ Erro na configuração do Nginx${NC}"
    exit 1
fi

echo ""

# ========================================
# RESUMO FINAL
# ========================================
echo -e "${GREEN}=========================================${NC}"
echo -e "${GREEN}✅ DEPLOY COMPLETO!${NC}"
echo -e "${GREEN}=========================================${NC}"
echo ""
echo -e "${BLUE}📊 RESUMO DO DEPLOY:${NC}"
echo ""
echo -e "🌐 ${YELLOW}ACESSE O SISTEMA:${NC}"
echo -e "   ${GREEN}http://${PUBLIC_IP}/${NC}"
echo ""
echo -e "🔌 ${YELLOW}API Health Check:${NC}"
echo -e "   ${GREEN}http://${PUBLIC_IP}/api/v1/health${NC}"
echo ""
echo -e "📚 ${YELLOW}API Docs (Swagger):${NC}"
echo -e "   ${GREEN}http://${PUBLIC_IP}/api/v1/docs${NC}"
echo ""
echo -e "${BLUE}📋 STATUS DOS SERVIÇOS:${NC}"
pm2 status
echo ""
echo -e "${BLUE}💾 USO DE MEMÓRIA:${NC}"
free -h
echo ""
echo -e "${BLUE}📊 COMANDOS ÚTEIS:${NC}"
echo "  Ver logs backend:     pm2 logs trading-api"
echo "  Ver logs sync:        pm2 logs trading-sync"
echo "  Restart backend:      pm2 restart trading-api"
echo "  Ver logs Nginx:       tail -f /var/log/nginx/access.log"
echo "  Monitor sistema:      pm2 monit"
echo ""
echo -e "${YELLOW}🔐 SECRETS GERADOS (SALVE EM LOCAL SEGURO):${NC}"
echo "  SECRET_KEY:         ${SECRET_KEY:0:20}..."
echo "  ENCRYPTION_KEY:     ${ENCRYPTION_KEY:0:20}..."
echo "  TV_WEBHOOK_SECRET:  ${TV_WEBHOOK_SECRET:0:20}..."
echo ""
echo -e "${BLUE}🎯 PRÓXIMOS PASSOS:${NC}"
echo "  1. Teste o sistema: http://${PUBLIC_IP}/"
echo "  2. Configure domínio (opcional)"
echo "  3. Instale SSL: certbot --nginx -d seudominio.com"
echo "  4. Configure backup automático no DigitalOcean"
echo ""
echo -e "${GREEN}🚀 Sistema pronto para uso!${NC}"
echo ""

#!/bin/bash
# ========================================
# DEPLOY FRONTEND - GlobalAutomation
# ========================================
# Build e deploy do frontend React + Vite
# Tempo estimado: 3-5 minutos

set -e  # Parar em caso de erro

echo "========================================="
echo "🚀 DEPLOY FRONTEND - React + Vite"
echo "========================================="
echo ""

# Verificar se está no diretório correto
if [ ! -f "frontend-new/package.json" ]; then
    echo "❌ ERRO: Execute este script na raiz do projeto GlobalAutomation"
    echo "   cd /opt/trading-platform/GlobalAutomation"
    echo "   bash deploy/04-DEPLOY-FRONTEND.sh"
    exit 1
fi

# ========================================
# FASE 1: Configurar .env do Frontend
# ========================================
echo "⚙️  FASE 1: Configurando .env do frontend..."

cd frontend-new

# Obter IP público do servidor
PUBLIC_IP=$(curl -s http://ifconfig.me)

# Criar .env de produção
cat > .env << EOF
# API URL - AJUSTE CONFORME SEU DOMÍNIO!
# Se você configurou domínio:
#   VITE_API_URL=https://api.seudominio.com/api/v1
# Se está usando IP:
VITE_API_URL=http://${PUBLIC_IP}:8000/api/v1

# Environment
VITE_NODE_ENV=production

# Application
VITE_APP_NAME=Trading Platform
VITE_APP_VERSION=1.0.0
EOF

echo "✅ .env criado com API_URL: http://${PUBLIC_IP}:8000/api/v1"
echo ""
echo "⚠️  IMPORTANTE: Se você configurar domínio, edite:"
echo "   nano frontend-new/.env"
echo "   Altere VITE_API_URL para https://api.seudominio.com/api/v1"
echo ""

# ========================================
# FASE 2: Instalar Dependências
# ========================================
echo "📦 FASE 2: Instalando dependências npm..."

# Limpar node_modules e cache se existir
if [ -d "node_modules" ]; then
    echo "  Limpando node_modules antigo..."
    rm -rf node_modules
fi

# Instalar dependências
npm install --production=false

echo "✅ Dependências instaladas"
echo ""

# ========================================
# FASE 3: Build para Produção
# ========================================
echo "🏗️  FASE 3: Buildando para produção..."

# Remover build antigo
if [ -d "dist" ]; then
    rm -rf dist
fi

# Build
npm run build

# Verificar se build foi criado
if [ ! -d "dist" ]; then
    echo "❌ ERRO: Build falhou! Diretório dist/ não foi criado."
    exit 1
fi

echo "✅ Build criado em frontend-new/dist/"
echo ""

# ========================================
# FASE 4: Verificar Build
# ========================================
echo "🔍 FASE 4: Verificando build..."

# Contar arquivos
FILE_COUNT=$(find dist -type f | wc -l)
echo "  📁 Arquivos no build: $FILE_COUNT"

# Tamanho total
BUILD_SIZE=$(du -sh dist | cut -f1)
echo "  💾 Tamanho do build: $BUILD_SIZE"

# Verificar index.html
if [ ! -f "dist/index.html" ]; then
    echo "❌ ERRO: index.html não encontrado no build!"
    exit 1
fi

echo "✅ Build válido"
echo ""

# ========================================
# FASE 5: Configurar Nginx
# ========================================
echo "🌐 FASE 5: Configurando Nginx..."

cd /opt/trading-platform/GlobalAutomation

# Copiar configuração do Nginx
if [ -f "deploy/nginx-config.conf" ]; then
    cp deploy/nginx-config.conf /etc/nginx/sites-available/trading-platform

    # Criar link simbólico se não existir
    if [ ! -L /etc/nginx/sites-enabled/trading-platform ]; then
        ln -s /etc/nginx/sites-available/trading-platform /etc/nginx/sites-enabled/
    fi

    echo "✅ Configuração Nginx copiada"
else
    echo "⚠️  nginx-config.conf não encontrado, criando configuração básica..."

    cat > /etc/nginx/sites-available/trading-platform << 'EOF'
# Backend API
server {
    listen 80;
    server_name _;

    # API Backend
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
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml application/xml+rss text/javascript;
}
EOF

    ln -sf /etc/nginx/sites-available/trading-platform /etc/nginx/sites-enabled/
    echo "✅ Configuração básica criada"
fi

echo ""

# ========================================
# FASE 6: Testar Configuração Nginx
# ========================================
echo "🧪 FASE 6: Testando configuração Nginx..."

nginx -t

if [ $? -ne 0 ]; then
    echo "❌ ERRO: Configuração Nginx inválida!"
    exit 1
fi

echo "✅ Configuração Nginx OK"
echo ""

# ========================================
# FASE 7: Recarregar Nginx
# ========================================
echo "🔄 FASE 7: Recarregando Nginx..."

systemctl reload nginx
systemctl status nginx --no-pager | head -10

echo "✅ Nginx recarregado"
echo ""

# ========================================
# FASE 8: Testar Frontend
# ========================================
echo "🏥 FASE 8: Testando frontend..."

# Aguardar Nginx carregar
sleep 2

# Testar se frontend está acessível
if curl -f http://localhost/ > /dev/null 2>&1; then
    echo "✅ Frontend acessível!"
else
    echo "⚠️  Aviso: Frontend pode não estar acessível via localhost"
fi

echo ""

# ========================================
# RESUMO FINAL
# ========================================
echo "========================================="
echo "✅ FRONTEND DEPLOY COMPLETO!"
echo "========================================="
echo ""
echo "🌐 ACESSE O SISTEMA:"
echo "  URL: http://${PUBLIC_IP}/"
echo "  API: http://${PUBLIC_IP}/api/v1/health"
echo ""
echo "📊 ARQUITETURA:"
echo "  Frontend:  Nginx (porta 80) → /frontend-new/dist/"
echo "  Backend:   Nginx (proxy)     → localhost:8000"
echo ""
echo "⚙️  COMANDOS ÚTEIS:"
echo "  Ver logs Nginx:    tail -f /var/log/nginx/access.log"
echo "  Reload Nginx:      systemctl reload nginx"
echo "  Status Nginx:      systemctl status nginx"
echo ""
echo "🔒 PRÓXIMO PASSO (Opcional):"
echo "   1. Configure domínio (DNS apontando para ${PUBLIC_IP})"
echo "   2. Instale SSL: certbot --nginx -d seudominio.com"
echo ""
echo "========================================="

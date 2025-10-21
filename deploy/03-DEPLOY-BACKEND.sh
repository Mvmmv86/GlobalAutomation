#!/bin/bash
# ========================================
# DEPLOY BACKEND - GlobalAutomation
# ========================================
# Deploy do backend FastAPI com PM2
# Tempo estimado: 5-10 minutos

set -e  # Parar em caso de erro

echo "========================================="
echo "🚀 DEPLOY BACKEND - FastAPI + PM2"
echo "========================================="
echo ""

# Verificar se está no diretório correto
if [ ! -f "apps/api-python/main.py" ]; then
    echo "❌ ERRO: Execute este script na raiz do projeto GlobalAutomation"
    echo "   cd /opt/trading-platform/GlobalAutomation"
    echo "   bash deploy/03-DEPLOY-BACKEND.sh"
    exit 1
fi

# Verificar se .env existe
if [ ! -f "apps/api-python/.env" ]; then
    echo "❌ ERRO: Arquivo .env não encontrado!"
    echo ""
    echo "Configure o .env primeiro:"
    echo "  1. cp deploy/.env.production.example apps/api-python/.env"
    echo "  2. nano apps/api-python/.env"
    echo "  3. Preencha com suas credenciais reais"
    exit 1
fi

# ========================================
# FASE 1: Criar Virtual Environment
# ========================================
echo "🐍 FASE 1: Criando virtual environment..."

cd apps/api-python

# Remover venv antigo se existir
if [ -d "venv" ]; then
    echo "  Removendo venv antigo..."
    rm -rf venv
fi

# Criar novo venv com Python 3.11
python3.11 -m venv venv

# Ativar venv
source venv/bin/activate

echo "✅ Virtual environment criado"
echo ""

# ========================================
# FASE 2: Instalar Dependências
# ========================================
echo "📦 FASE 2: Instalando dependências Python..."

# Upgrade pip
pip install --upgrade pip

# Instalar dependências
pip install -r requirements.txt

echo "✅ Dependências instaladas"
echo ""

# ========================================
# FASE 3: Testar Configuração
# ========================================
echo "🧪 FASE 3: Testando configuração..."

# Testar importação do módulo principal
python -c "import main; print('✅ Importação OK')"

# Verificar .env
python -c "
import os
from dotenv import load_dotenv
load_dotenv()
required = ['SECRET_KEY', 'DATABASE_URL', 'ENCRYPTION_KEY']
missing = [k for k in required if not os.getenv(k)]
if missing:
    print(f'❌ ERRO: Variáveis faltando no .env: {missing}')
    exit(1)
print('✅ .env configurado corretamente')
"

echo ""

# ========================================
# FASE 4: Configurar PM2
# ========================================
echo "⚙️  FASE 4: Configurando PM2..."

cd /opt/trading-platform/GlobalAutomation

# Parar processo antigo se existir
pm2 delete trading-api 2>/dev/null || true

# Iniciar aplicação com PM2
pm2 start apps/api-python/venv/bin/python \
    --name trading-api \
    --interpreter none \
    -- -m uvicorn main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --workers 1 \
    --cwd /opt/trading-platform/GlobalAutomation/apps/api-python

# Salvar configuração PM2
pm2 save

echo "✅ PM2 configurado"
echo ""

# ========================================
# FASE 5: Aguardar Inicialização
# ========================================
echo "⏳ FASE 5: Aguardando inicialização..."

sleep 5

# Verificar se está rodando
pm2 status trading-api

echo ""

# ========================================
# FASE 6: Testar Health Check
# ========================================
echo "🏥 FASE 6: Testando health check..."

# Tentar 5 vezes (app pode demorar um pouco)
for i in {1..5}; do
    if curl -f http://localhost:8000/health 2>/dev/null; then
        echo ""
        echo "✅ Health check OK!"
        break
    else
        echo "  Tentativa $i/5..."
        sleep 2
    fi
done

echo ""

# ========================================
# FASE 7: Configurar Auto Sync
# ========================================
echo "🔄 FASE 7: Configurando auto sync..."

# Parar auto_sync antigo se existir
pm2 delete trading-sync 2>/dev/null || true

# Verificar se script existe
if [ -f "apps/api-python/auto_sync.sh" ]; then
    chmod +x apps/api-python/auto_sync.sh

    # Iniciar auto_sync com PM2
    pm2 start apps/api-python/auto_sync.sh \
        --name trading-sync \
        --cwd /opt/trading-platform/GlobalAutomation/apps/api-python

    pm2 save

    echo "✅ Auto sync configurado"
else
    echo "⚠️  auto_sync.sh não encontrado (opcional)"
fi

echo ""

# ========================================
# FASE 8: Ver Logs
# ========================================
echo "📄 FASE 8: Últimas linhas do log..."

pm2 logs trading-api --lines 20 --nostream

echo ""

# ========================================
# RESUMO FINAL
# ========================================
echo "========================================="
echo "✅ BACKEND DEPLOY COMPLETO!"
echo "========================================="
echo ""
echo "📋 STATUS:"
pm2 status
echo ""
echo "🌐 ENDPOINTS:"
echo "  Health Check: http://localhost:8000/health"
echo "  API Docs:     http://localhost:8000/docs"
echo "  OpenAPI:      http://localhost:8000/openapi.json"
echo ""
echo "📊 COMANDOS ÚTEIS:"
echo "  Ver logs:       pm2 logs trading-api"
echo "  Restart:        pm2 restart trading-api"
echo "  Stop:           pm2 stop trading-api"
echo "  Status:         pm2 status"
echo "  Monit:          pm2 monit"
echo ""
echo "🎯 PRÓXIMO PASSO:"
echo "   bash deploy/04-DEPLOY-FRONTEND.sh"
echo ""
echo "========================================="

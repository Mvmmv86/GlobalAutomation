#!/bin/bash
#
# Script para iniciar o backend FastAPI com cache implementado
# FASE 1 - Cache de Posições
#
# Uso: ./START_BACKEND_WITH_CACHE.sh
#

set -e

echo "=================================================="
echo "  INICIANDO BACKEND COM CACHE (FASE 1)"
echo "=================================================="
echo ""

# Verificar se já há processo na porta 8000
if lsof -ti:8000 > /dev/null 2>&1; then
    echo "⚠️  Detectado processo na porta 8000"
    echo "   Finalizando processo antigo..."
    pkill -f "python3 main.py" || true
    sleep 2
fi

# Ir para diretório do backend
cd /home/globalauto/global/apps/api-python

echo "📦 Verificando dependências..."
python3 -c "from infrastructure.cache import get_positions_cache; print('✅ Módulo de cache carregado')"

echo ""
echo "🚀 Iniciando backend FastAPI..."
echo "   - Porta: 8000"
echo "   - Cache: Ativo (TTL: 3s)"
echo "   - Cleanup: Automático (60s)"
echo ""

# Iniciar backend em background
nohup python3 main.py > /tmp/backend_cache.log 2>&1 &
BACKEND_PID=$!

echo "✅ Backend iniciado (PID: $BACKEND_PID)"
echo "   Logs: /tmp/backend_cache.log"
echo ""

# Aguardar inicialização
echo "⏳ Aguardando inicialização (10s)..."
sleep 10

# Verificar se está rodando
if lsof -ti:8000 > /dev/null 2>&1; then
    echo "✅ Backend rodando na porta 8000"
else
    echo "❌ Erro: Backend não iniciou corretamente"
    echo "   Verifique os logs em /tmp/backend_cache.log"
    exit 1
fi

# Testar health endpoint
echo ""
echo "🔍 Testando health endpoint..."
if curl -s http://localhost:8000/api/v1/health/ping > /dev/null 2>&1; then
    echo "✅ Health endpoint OK"
else
    echo "⚠️  Health endpoint não respondeu"
fi

# Testar cache metrics
echo ""
echo "📊 Testando cache metrics..."
if curl -s http://localhost:8000/api/v1/dashboard/cache/metrics > /dev/null 2>&1; then
    echo "✅ Cache metrics endpoint OK"
    echo ""
    echo "   Métricas disponíveis em:"
    echo "   http://localhost:8000/api/v1/dashboard/cache/metrics"
else
    echo "⚠️  Cache metrics não disponível"
fi

echo ""
echo "=================================================="
echo "  ✅ BACKEND INICIADO COM SUCESSO!"
echo "=================================================="
echo ""
echo "📋 Endpoints principais:"
echo "   - API Root: http://localhost:8000/"
echo "   - Health: http://localhost:8000/api/v1/health/ping"
echo "   - Balances (cached): http://localhost:8000/api/v1/dashboard/balances"
echo "   - Cache Metrics: http://localhost:8000/api/v1/dashboard/cache/metrics"
echo "   - API Docs: http://localhost:8000/docs"
echo ""
echo "🔧 Comandos úteis:"
echo "   - Ver logs: tail -f /tmp/backend_cache.log"
echo "   - Parar backend: pkill -f 'python3 main.py'"
echo "   - Ver cache metrics: curl http://localhost:8000/api/v1/dashboard/cache/metrics"
echo "   - Invalidar cache: curl -X POST http://localhost:8000/api/v1/dashboard/cache/invalidate"
echo ""
echo "📊 Para testar o cache:"
echo "   1. Abra http://localhost:3000 (frontend)"
echo "   2. Navegue para Dashboard"
echo "   3. Observe console do navegador para logs de cache"
echo "   4. Veja métricas em /api/v1/dashboard/cache/metrics"
echo ""

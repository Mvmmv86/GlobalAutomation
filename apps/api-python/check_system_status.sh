#!/bin/bash

echo "════════════════════════════════════════════════════════════════"
echo "🔍 VERIFICAÇÃO DO SISTEMA - TradingView Webhooks"
echo "════════════════════════════════════════════════════════════════"

# 1. Verificar Backend
echo ""
echo "1️⃣  Verificando Backend (porta 8000)..."
if lsof -i:8000 >/dev/null 2>&1; then
    echo "   ✅ Backend RODANDO"
    lsof -i:8000 | grep LISTEN
else
    echo "   ❌ Backend NÃO ESTÁ RODANDO"
    echo "   ⚠️  Inicie com: python3 main.py"
fi

# 2. Verificar ngrok
echo ""
echo "2️⃣  Verificando ngrok (porta 4040)..."
if lsof -i:4040 >/dev/null 2>&1; then
    echo "   ✅ ngrok RODANDO"
    echo "   📡 Dashboard: http://localhost:4040"
    echo ""
    echo "   🌐 URL Pública do ngrok:"
    curl -s http://localhost:4040/api/tunnels 2>/dev/null | grep -o '"public_url":"https://[^"]*"' | cut -d'"' -f4 || echo "   ⚠️  Não conseguiu pegar a URL"
else
    echo "   ❌ ngrok NÃO ESTÁ RODANDO"
    echo "   ⚠️  Inicie com: ngrok http 8000"
fi

# 3. Testar endpoint de health
echo ""
echo "3️⃣  Testando endpoint de health..."
if curl -s http://localhost:8000/health >/dev/null 2>&1; then
    echo "   ✅ Backend respondendo corretamente"
else
    echo "   ❌ Backend não responde"
fi

# 4. Resumo
echo ""
echo "════════════════════════════════════════════════════════════════"
echo "📊 RESUMO"
echo "════════════════════════════════════════════════════════════════"

BACKEND_OK=$(lsof -i:8000 >/dev/null 2>&1 && echo "1" || echo "0")
NGROK_OK=$(lsof -i:4040 >/dev/null 2>&1 && echo "1" || echo "0")

if [ "$BACKEND_OK" = "1" ] && [ "$NGROK_OK" = "1" ]; then
    echo "✅ SISTEMA PRONTO PARA RECEBER ALERTAS!"
    echo ""
    echo "🔗 Webhooks configurados:"
    echo "   - BTC_TPO_12min: https://SUA-URL.ngrok.io/webhooks/tv/btctpo"
    echo "   - ETH_TPO_12min: https://SUA-URL.ngrok.io/webhooks/tv/ethtpo"
    echo "   - SOL_TPO_12min: https://SUA-URL.ngrok.io/webhooks/tv/soltpo"
    echo "   - BNB_TPO_5min:  https://SUA-URL.ngrok.io/webhooks/tv/bnbtpo"
else
    echo "⚠️  SISTEMA NÃO ESTÁ PRONTO!"
    echo ""
    if [ "$BACKEND_OK" = "0" ]; then
        echo "❌ Backend precisa ser iniciado: python3 main.py"
    fi
    if [ "$NGROK_OK" = "0" ]; then
        echo "❌ ngrok precisa ser iniciado: ngrok http 8000"
    fi
fi

echo ""
echo "════════════════════════════════════════════════════════════════"

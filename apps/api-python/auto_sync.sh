#!/bin/bash
# Script de sincronização automática a cada 30 segundos
# Mantém os dados sempre atualizados
# Busca automaticamente a conta principal (is_main=true)

API_URL="http://localhost:8000/api/v1/sync/balances"
API_BASE="http://localhost:8000/api/v1"

echo "🚀 Iniciando sincronização automática a cada 30 segundos..."
echo "📝 Para parar, pressione Ctrl+C"
echo ""

# Função para buscar a conta principal
get_main_account() {
    ACCOUNTS_RESPONSE=$(curl -s "$API_BASE/exchange-accounts")
    ACCOUNT_ID=$(echo "$ACCOUNTS_RESPONSE" | grep -o '"id":"[^"]*"' | grep -B1 '"is_main":true' | head -1 | cut -d'"' -f4)

    if [ -z "$ACCOUNT_ID" ]; then
        # Se não encontrar conta principal, pegar a primeira conta ativa
        ACCOUNT_ID=$(echo "$ACCOUNTS_RESPONSE" | grep -o '"id":"[^"]*"' | head -1 | cut -d'"' -f4)
    fi

    echo "$ACCOUNT_ID"
}

# Buscar conta principal na primeira execução
ACCOUNT_ID=$(get_main_account)
echo "🎯 Conta Principal ID: $ACCOUNT_ID"
echo ""

while true; do
    # Timestamp atual
    TIMESTAMP=$(date '+%H:%M:%S')

    # A cada ciclo, verificar se a conta principal mudou
    NEW_ACCOUNT_ID=$(get_main_account)
    if [ "$NEW_ACCOUNT_ID" != "$ACCOUNT_ID" ]; then
        ACCOUNT_ID="$NEW_ACCOUNT_ID"
        echo "🔄 Conta principal atualizada: $ACCOUNT_ID"
        echo ""
    fi

    echo "🔄 $TIMESTAMP - Sincronizando dados da Binance..."

    # Sincronizar balances
    echo "  💰 Sincronizando balances..."
    RESPONSE=$(curl -s -X POST "$API_URL/$ACCOUNT_ID")

    # Sincronizar positions
    echo "  🎯 Sincronizando positions..."
    POSITIONS_RESPONSE=$(curl -s -X POST "http://localhost:8000/api/v1/sync/positions/$ACCOUNT_ID")

    # Verificar se foi bem sucedido
    BALANCES_SUCCESS=false
    POSITIONS_SUCCESS=false

    if echo "$RESPONSE" | grep -q '"success":true'; then
        SYNCED_COUNT=$(echo "$RESPONSE" | grep -o '"synced_count":[0-9]*' | cut -d':' -f2)
        echo "  ✅ Balances: $SYNCED_COUNT sincronizados"
        BALANCES_SUCCESS=true
    else
        echo "  ❌ Erro nos balances: $RESPONSE"
    fi

    if echo "$POSITIONS_RESPONSE" | grep -q '"success":true'; then
        POSITIONS_COUNT=$(echo "$POSITIONS_RESPONSE" | grep -o '"synced_count":[0-9]*' | cut -d':' -f2)
        echo "  ✅ Positions: $POSITIONS_COUNT sincronizadas"
        POSITIONS_SUCCESS=true
    else
        echo "  ❌ Erro nas positions: $POSITIONS_RESPONSE"
    fi

    # Detectar posições fechadas (roda a cada 5 minutos apenas)
    MINUTE=$(date '+%M')
    if [ $((MINUTE % 5)) -eq 0 ]; then
        echo "  🔍 Detectando posições fechadas..."
        python3 detect_closed_positions.py 2>&1 | grep -E "(fechadas detectadas|DETECTADO FECHAMENTO|Erro)" | sed 's/^/     /'
    fi

    if [ "$BALANCES_SUCCESS" = true ] && [ "$POSITIONS_SUCCESS" = true ]; then
        echo "✅ $TIMESTAMP - Sincronização completa realizada com sucesso!"
    else
        echo "⚠️ $TIMESTAMP - Sincronização parcial ou com erros"
    fi

    echo "⏳ Aguardando 30 segundos..."
    echo ""

    # Aguardar 30 segundos
    sleep 30
done
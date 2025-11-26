#!/bin/bash
# Auto-sync MELHORADO - Sincroniza TODAS as contas a cada 5 segundos
# Sistema rápido e dinâmico para trading em tempo real

API_URL="http://localhost:8000/api/v1"
SYNC_INTERVAL=5  # 5 segundos para trading rápido!

# Cores para output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 Auto-Sync Multi-Account v2.0${NC}"
echo -e "${YELLOW}⚡ Intervalo: ${SYNC_INTERVAL} segundos${NC}"
echo -e "${YELLOW}📊 Sincronizando TODAS as contas ativas${NC}"
echo ""

# Função para obter todas as contas ativas
get_active_accounts() {
    curl -s "$API_URL/exchange-accounts" | \
        python3 -c "import sys, json; data=json.load(sys.stdin); [print(acc['id']) for acc in data.get('data', []) if acc.get('is_active')]" 2>/dev/null
}

# Loop principal
while true; do
    TIMESTAMP=$(date '+%H:%M:%S')
    echo -e "\n${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "⏰ ${TIMESTAMP} - Iniciando sincronização..."

    # Obter contas ativas
    ACCOUNTS=$(get_active_accounts)
    ACCOUNT_COUNT=$(echo "$ACCOUNTS" | grep -c .)

    if [ -z "$ACCOUNTS" ]; then
        echo -e "${RED}⚠️  Nenhuma conta ativa encontrada!${NC}"
    else
        echo -e "${YELLOW}📊 Sincronizando ${ACCOUNT_COUNT} conta(s)...${NC}"

        SUCCESS_COUNT=0
        FAIL_COUNT=0

        # Sincronizar cada conta
        while IFS= read -r ACCOUNT_ID; do
            if [ ! -z "$ACCOUNT_ID" ]; then
                # Nome curto do ID para log
                SHORT_ID="${ACCOUNT_ID:0:8}..."

                # Sincronizar positions
                POS_RESPONSE=$(curl -s -X POST "$API_URL/sync/positions/$ACCOUNT_ID" 2>/dev/null)

                if echo "$POS_RESPONSE" | grep -q '"success":true'; then
                    POS_COUNT=$(echo "$POS_RESPONSE" | grep -o '"synced_count":[0-9]*' | cut -d':' -f2)
                    echo -e "  ✅ ${SHORT_ID}: ${POS_COUNT:-0} posições"
                    ((SUCCESS_COUNT++))
                else
                    echo -e "  ❌ ${SHORT_ID}: Erro no sync"
                    ((FAIL_COUNT++))
                fi
            fi
        done <<< "$ACCOUNTS"

        # Resumo
        if [ $SUCCESS_COUNT -gt 0 ]; then
            echo -e "${GREEN}✅ Sucesso: ${SUCCESS_COUNT} conta(s)${NC}"
        fi
        if [ $FAIL_COUNT -gt 0 ]; then
            echo -e "${RED}❌ Falhas: ${FAIL_COUNT} conta(s)${NC}"
        fi
    fi

    # Aguardar intervalo
    echo -e "${YELLOW}⏳ Próximo sync em ${SYNC_INTERVAL}s...${NC}"
    sleep $SYNC_INTERVAL
done
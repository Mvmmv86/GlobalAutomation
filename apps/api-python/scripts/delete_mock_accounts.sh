#!/bin/bash
# Script para remover contas mock via API, mantendo apenas a conta real

# URL da API
API_URL="http://172.18.0.3:3001/api/v1/exchange-accounts"

# Token de autenticação (se necessário)
TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI0MDU1YmFjYS02OWI3LTQ0MzQtOTM5Yi1jNDY1ODNmNDZiZjYiLCJlbWFpbCI6InRlc3RlQHRlc3RlLmNvbSIsImV4cCI6MTczNTY5MjEwNn0.nGj9R1tWgOj8fWh7rCZlT4wKKq4qD1iV5YUObfNRzew"

# Conta real a manter (não remover)
REAL_ACCOUNT="78e6b4fa-9a71-4360-b808-f1cd7c98dcbe"

# Array de contas para remover
ACCOUNTS_TO_REMOVE=(
    "7edce3b4-8ba2-4275-b136-7a8b6b6e93ba"  # tests (testnet)
    "1cfb9b63-bdd1-470d-9763-92f32635d2d8"  # Teste Frontend Fix (testnet)  
    "0f505abb-0260-4b73-8580-a6332f2ec37b"  # Test API Keys (testnet)
    "f42d8315-1a1e-4eb4-aef1-cbeda245f928"  # testeMarcus (testnet)
    "a91cf0e8-f9d1-409a-bd1b-e83a1ac55a68"  # Test Real Keys (testnet)
    "94b8a494-acd2-40dd-8773-63d7773ab8d1"  # Test Binance Testnet
    "770e8400-e29b-41d4-a716-446655440001"  # Demo Binance Testnet
    "770e8400-e29b-41d4-a716-446655440004"  # Admin Binance Live (outra conta)
    "770e8400-e29b-41d4-a716-446655440003"  # Trader Binance Testnet
    "770e8400-e29b-41d4-a716-446655440002"  # Demo Bybit Testnet
)

echo "🧹 Iniciando limpeza de contas mock..."
echo "✅ Mantendo conta real: $REAL_ACCOUNT"
echo "❌ Removendo ${#ACCOUNTS_TO_REMOVE[@]} contas mock/testnet"
echo ""

# Função para deletar uma conta
delete_account() {
    local account_id=$1
    echo "🗑️ Removendo conta: $account_id"
    
    response=$(curl -s -w "\nHTTP_CODE:%{http_code}" \
        -X DELETE \
        -H "Authorization: Bearer $TOKEN" \
        "$API_URL/$account_id")
    
    http_code=$(echo "$response" | grep "HTTP_CODE:" | sed 's/HTTP_CODE://')
    body=$(echo "$response" | sed '/HTTP_CODE:/d')
    
    if [ "$http_code" = "200" ] || [ "$http_code" = "204" ]; then
        echo "   ✅ Conta removida com sucesso"
    else
        echo "   ❌ Erro ao remover conta (HTTP $http_code): $body"
    fi
}

# Remover cada conta
for account_id in "${ACCOUNTS_TO_REMOVE[@]}"; do
    delete_account "$account_id"
    sleep 0.5  # Pequena pausa entre requests
done

echo ""
echo "🎉 Limpeza concluída!"
echo "📊 Verificando resultado final..."

# Listar contas restantes
echo ""
echo "📋 Contas restantes:"
curl -s -H "Authorization: Bearer $TOKEN" "$API_URL" | \
python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    if data.get('success'):
        accounts = data.get('data', [])
        print(f'Total de contas: {len(accounts)}')
        for acc in accounts:
            status = '✅ REAL' if acc['id'] == '$REAL_ACCOUNT' else '❌ DEVERIA TER SIDO REMOVIDA'
            print(f'  {status} - {acc[\"name\"]} ({acc[\"exchange\"]} {acc[\"environment\"]})')
    else:
        print('Erro ao listar contas')
except:
    print('Erro ao processar resposta')
"
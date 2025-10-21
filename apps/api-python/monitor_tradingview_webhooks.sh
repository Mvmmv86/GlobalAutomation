#!/bin/bash

echo "🔍 Monitorando webhooks do TradingView em tempo real..."
echo "📡 Endpoint: /api/v1/bots/webhook/master/{webhook_path}"
echo ""
echo "Aguardando sinais do TradingView..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

tail -f /tmp/backend.log | grep --line-buffered -i "master webhook\|webhook_path\|ticker\|action\|bot not found\|invalid webhook"

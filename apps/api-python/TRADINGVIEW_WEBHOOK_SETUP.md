# 📺 Como Configurar Webhook no TradingView (Plataforma Real)

## 🚀 Passo 1: Preparar seu Servidor

### Opção A: Servidor Local (Desenvolvimento)
Se você está testando localmente, precisa expor seu servidor para a internet:

1. **Instalar ngrok** (se não tiver):
```bash
# Linux/Mac
curl -s https://ngrok-agent.s3.amazonaws.com/ngrok.asc | sudo tee /etc/apt/trusted.gpg.d/ngrok.asc >/dev/null && echo "deb https://ngrok-agent.s3.amazonaws.com buster main" | sudo tee /etc/apt/sources.list.d/ngrok.list && sudo apt update && sudo apt install ngrok

# Ou baixe de: https://ngrok.com/download
```

2. **Expor seu servidor local**:
```bash
# Em um terminal, mantenha seu servidor rodando:
python main.py

# Em outro terminal, exponha para internet:
ngrok http 8000
```

3. **Copie a URL do ngrok** (será algo como: `https://abc123.ngrok.io`)

### Opção B: Servidor na Nuvem
Se seu servidor está na nuvem (AWS, Google Cloud, etc):
- Sua URL será: `http://SEU_IP_PUBLICO:8000`
- Certifique-se que a porta 8000 está aberta no firewall

## 📊 Passo 2: Configurar no TradingView

### 2.1 - Criar um Script Pine com Alerta

1. Acesse **TradingView.com** e faça login
2. Abra um gráfico (ex: BTCUSDT)
3. Clique em **Pine Editor** (na parte inferior)
4. Cole este script de exemplo:

```pinescript
//@version=5
indicator("Webhook Test", overlay=true)

// Condição simples: quando preço cruza a média móvel
ma = ta.sma(close, 20)
crossUp = ta.crossover(close, ma)
crossDown = ta.crossunder(close, ma)

// Plotar média
plot(ma, color=color.blue, linewidth=2)

// Criar alertas
if crossUp
    alert('{"action": "buy", "ticker": "' + syminfo.ticker + '", "price": ' + str.tostring(close) + '}', alert.freq_once_per_bar)
    label.new(bar_index, high, "BUY", color=color.green, textcolor=color.white)

if crossDown
    alert('{"action": "sell", "ticker": "' + syminfo.ticker + '", "price": ' + str.tostring(close) + '}', alert.freq_once_per_bar)
    label.new(bar_index, low, "SELL", color=color.red, textcolor=color.white)
```

5. Clique em **Add to Chart**

### 2.2 - Criar o Alerta com Webhook

1. Clique com botão direito no gráfico → **Add Alert**

2. Configure o alerta:
   - **Condition**: Escolha seu indicador "Webhook Test"
   - **Alert name**: "Test Webhook"
   - **Message**: (deixe em branco, o script já envia)

3. **Na seção Notifications**:
   - ✅ Marque **Webhook URL**
   - Cole sua URL:
     ```
     # Se usando ngrok:
     https://abc123.ngrok.io/api/v1/webhooks/tradingview
     
     # Se servidor público:
     http://189.85.177.101:8000/api/v1/webhooks/tradingview
     ```

4. Clique em **Create**

## 🧪 Passo 3: Testar o Webhook

### Teste Manual (Recomendado primeiro)
1. No TradingView, vá em **Alerts** (sino no topo)
2. Encontre seu alerta
3. Clique nos 3 pontos → **Test Alert**
4. Verifique no terminal do servidor se recebeu

### Teste Automático
1. Espere o preço cruzar a média móvel
2. Ou mude o timeframe para forçar um cruzamento
3. O alerta será disparado automaticamente

## 📝 Passo 4: Verificar Recebimento

No terminal onde está rodando o servidor, você verá:

```
============================================================
🚨 WEBHOOK RECEBIDO DO TRADINGVIEW!
📅 Time: 2024-01-20T15:30:45.123456
📦 Payload: {"action": "buy", "ticker": "BTCUSDT", "price": 45123.50}
============================================================
```

Os webhooks também são salvos em: `tradingview_webhooks.log`

## 🔧 Formato de Payload Personalizado

### Payload Simples (JSON):
```json
{
  "action": "{{strategy.order.action}}",
  "ticker": "{{ticker}}",
  "price": {{close}},
  "volume": {{volume}},
  "time": "{{time}}"
}
```

### Payload Completo (para produção):
```json
{
  "action": "{{strategy.order.action}}",
  "ticker": "{{ticker}}",
  "price": {{close}},
  "quantity": 0.1,
  "order_type": "{{strategy.order.comment}}",
  "strategy": "{{strategy.name}}",
  "position_size": {{strategy.position_size}},
  "stop_loss": {{plot_0}},
  "take_profit": {{plot_1}}
}
```

## ⚠️ Troubleshooting

### Webhook não chega:
1. Verifique se a URL está correta
2. Teste com webhook.site primeiro
3. Verifique firewall/portas
4. Certifique-se que o servidor está rodando

### Erro 404/500:
1. Verifique o endpoint: `/api/v1/webhooks/tradingview`
2. Verifique os logs do servidor
3. Teste localmente primeiro com curl

### Ngrok expira:
- Conta gratuita do ngrok tem limite de 2h
- Crie uma conta para URL fixa

## 🎯 Endpoints Disponíveis

- `POST /api/v1/webhooks/tradingview` - Webhook principal
- `POST /api/v1/webhooks/tv/test-webhook` - Teste com payload completo
- `GET /api/v1/health/` - Verificar se API está online
- `GET /` - Status da API

## 📊 Exemplo de Teste com cURL

```bash
# Teste local
curl -X POST http://localhost:8000/api/v1/webhooks/tradingview \
  -H "Content-Type: application/json" \
  -d '{"action":"buy","ticker":"BTCUSDT","price":45000}'

# Teste com ngrok
curl -X POST https://abc123.ngrok.io/api/v1/webhooks/tradingview \
  -H "Content-Type: application/json" \
  -d '{"action":"buy","ticker":"BTCUSDT","price":45000}'
```

## 🚀 Próximos Passos

1. **Segurança**: Adicione autenticação/HMAC
2. **Processamento**: Conecte com exchange real
3. **Logging**: Implemente sistema de logs robusto
4. **Monitoramento**: Configure alertas de falha

---

**Suporte**: Se tiver problemas, verifique `tradingview_webhooks.log` ou os logs do servidor.
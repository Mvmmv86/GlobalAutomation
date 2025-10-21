# 🔧 Troubleshooting: TradingView Webhooks Não Chegam

## 🚨 PROBLEMA IDENTIFICADO

Os alertas do TradingView **NÃO** estão chegando no backend porque:

1. ❌ **Backend não está rodando** (porta 8000 não está ativa)
2. ❌ **URLs usam `localhost`** - TradingView não consegue acessar localhost!

## 💡 SOLUÇÃO EM 3 PASSOS

### PASSO 1: Iniciar o Backend

```bash
cd /home/globalauto/global/apps/api-python
python3 main.py
```

Verificar se subiu:
```bash
lsof -i:8000  # Deve mostrar o processo
curl http://localhost:8000/health  # Deve retornar 200 OK
```

---

### PASSO 2: Expor o Backend na Internet

**O TradingView precisa de uma URL PÚBLICA!**

#### OPÇÃO A: Usar ngrok (Mais Rápido) ⚡

1. **Instalar ngrok:**
```bash
# Baixar ngrok
wget https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-linux-amd64.tgz
tar xvzf ngrok-v3-stable-linux-amd64.tgz
sudo mv ngrok /usr/local/bin/
```

2. **Autenticar (necessário uma vez):**
```bash
# Criar conta grátis em: https://dashboard.ngrok.com/signup
# Copiar o authtoken e rodar:
ngrok config add-authtoken SEU_TOKEN_AQUI
```

3. **Expor o backend:**
```bash
ngrok http 8000
```

Você verá algo assim:
```
Forwarding  https://abc123.ngrok.io -> http://localhost:8000
```

4. **Atualizar URLs no TradingView:**
```
ANTES: http://localhost:8000/webhooks/tv/btctpo
DEPOIS: https://abc123.ngrok.io/webhooks/tv/btctpo
```

---

#### OPÇÃO B: Usar Cloudflare Tunnel (Grátis e Permanente) 🌐

1. **Instalar cloudflared:**
```bash
wget https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb
sudo dpkg -i cloudflared-linux-amd64.deb
```

2. **Autenticar:**
```bash
cloudflared tunnel login
```

3. **Criar túnel:**
```bash
cloudflared tunnel create trading-webhooks
cloudflared tunnel route dns trading-webhooks webhooks.seudominio.com
```

4. **Iniciar túnel:**
```bash
cloudflared tunnel --url http://localhost:8000
```

---

#### OPÇÃO C: Servidor com IP Público (Produção) 🖥️

Se você tem um servidor na nuvem (AWS, DigitalOcean, etc):

1. **Configurar firewall:**
```bash
sudo ufw allow 8000/tcp
```

2. **Iniciar backend com IP público:**
```bash
python3 main.py --host 0.0.0.0 --port 8000
```

3. **URLs no TradingView:**
```
http://SEU_IP_PUBLICO:8000/webhooks/tv/btctpo
```

---

### PASSO 3: Testar o Webhook

#### 3A. Teste Local (antes de configurar no TradingView)

```bash
# Testar endpoint de health
curl http://localhost:8000/health

# Testar webhook localmente
curl -X POST http://localhost:8000/webhooks/tv/btctpo \
  -H "Content-Type: application/json" \
  -d '{
    "ticker": "BTCUSDT",
    "action": "buy",
    "price": 67000
  }'
```

#### 3B. Teste via ngrok/Cloudflare

```bash
# Substituir URL pela do ngrok/cloudflare
curl -X POST https://abc123.ngrok.io/webhooks/tv/btctpo \
  -H "Content-Type: application/json" \
  -d '{
    "ticker": "BTCUSDT",
    "action": "buy",
    "price": 67000
  }'
```

#### 3C. Verificar logs do backend

Abrir outro terminal e monitorar logs:
```bash
tail -f /caminho/para/logs/backend.log
# OU se estiver rodando no terminal, ver output direto
```

---

## 📋 CHECKLIST DE VALIDAÇÃO

Antes de configurar no TradingView, verificar:

- [ ] Backend está rodando (`lsof -i:8000`)
- [ ] Health endpoint responde (`curl http://localhost:8000/health`)
- [ ] Webhook responde localmente (curl test acima)
- [ ] ngrok/cloudflare está rodando
- [ ] URL pública do webhook responde (curl test via URL pública)
- [ ] Logs do backend mostram a requisição chegando

---

## 🔄 ATUALIZAR TRADINGVIEW

Depois de escolher a solução, atualizar os alertas:

### URLs Antigas (NÃO FUNCIONAM):
```
❌ http://localhost:8000/webhooks/tv/btctpo
❌ http://localhost:8000/webhooks/tv/ethtpo
❌ http://localhost:8000/webhooks/tv/soltpo
❌ http://localhost:8000/webhooks/tv/bnbtpo
```

### URLs Novas (com ngrok exemplo):
```
✅ https://abc123.ngrok.io/webhooks/tv/btctpo
✅ https://abc123.ngrok.io/webhooks/tv/ethtpo
✅ https://abc123.ngrok.io/webhooks/tv/soltpo
✅ https://abc123.ngrok.io/webhooks/tv/bnbtpo
```

### Payload JSON no TradingView:
```json
{
  "ticker": "{{ticker}}",
  "action": "buy",
  "price": {{close}}
}
```

---

## 🎯 MINHA RECOMENDAÇÃO

Para **desenvolvimento/testes**: Use **ngrok** (mais rápido)
Para **produção**: Use **Cloudflare Tunnel** (grátis e confiável) ou servidor com IP público

---

## 📊 MONITORAMENTO

Após configurar, você pode monitorar em tempo real:

```bash
# Ver webhooks recebidos
python3 check_webhooks_via_di.py

# Ver logs do backend
tail -f logs/backend.log

# Ver conexões ativas
watch -n 1 'lsof -i:8000'
```

---

## ❓ PROBLEMAS COMUNS

### "Conexão Recusada"
- Backend não está rodando → Iniciar com `python3 main.py`

### "Timeout"
- Firewall bloqueando → Liberar porta: `sudo ufw allow 8000`
- ngrok não rodando → Iniciar: `ngrok http 8000`

### "404 Not Found"
- URL path incorreto → Verificar: `/webhooks/tv/NOME_CORRETO`

### "500 Internal Server Error"
- Ver logs do backend para detalhes do erro
- Verificar se banco de dados está acessível

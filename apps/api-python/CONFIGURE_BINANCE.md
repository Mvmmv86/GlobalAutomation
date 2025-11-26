# 🔐 Configuração das Credenciais da Binance

## Passo 1: Obter suas credenciais na Binance

1. Acesse [Binance.com](https://www.binance.com) e faça login
2. Vá em **Perfil → Gerenciamento de API**
3. Clique em **Criar API**
4. Defina um nome para a API (ex: "Trading Platform")
5. Complete a verificação 2FA
6. **IMPORTANTE**: Anote sua **API Key** e **Secret Key** imediatamente (a Secret só aparece uma vez!)

## Passo 2: Configurar permissões da API

Na página de gerenciamento da API:
- ✅ **Ativar**: Leitura (Enable Reading)
- ✅ **Ativar**: Trading Spot (Enable Spot Trading) - se quiser executar ordens
- ❌ **Desativar**: Saques (Withdrawals) - por segurança
- 📍 **Restrição de IP** (opcional mas recomendado): Adicione seu IP

## Passo 3: Adicionar ao arquivo .env

Edite o arquivo `/workspace/apps/api-python/.env` e adicione:

```bash
# Suas credenciais reais da Binance
BINANCE_API_KEY=sua_api_key_aqui
BINANCE_API_SECRET=sua_secret_key_aqui
```

⚠️ **Substitua** `sua_api_key_aqui` e `sua_secret_key_aqui` pelas suas credenciais reais!

## Passo 4: Executar a configuração

Após adicionar suas credenciais, execute:

```bash
cd /workspace/apps/api-python
python setup_binance_credentials.py
```

Este script irá:
1. ✅ Validar suas credenciais
2. ✅ Testar a conexão com a Binance
3. ✅ Criptografar e salvar no banco de dados
4. ✅ Configurar tudo permanentemente

## Passo 5: Verificar funcionamento

Para verificar se tudo está funcionando:

```bash
python test_binance_data.py
```

## 📌 Checklist

- [ ] Criei a API Key na Binance
- [ ] Habilitei permissões de Leitura
- [ ] Copiei a API Key e Secret Key
- [ ] Adicionei as credenciais no .env
- [ ] Executei setup_binance_credentials.py
- [ ] Teste funcionou com sucesso

## 🚨 Segurança

- **NUNCA** compartilhe suas credenciais
- **NUNCA** commite o arquivo .env no git
- **SEMPRE** use restrição de IP quando possível
- **DESATIVE** permissões de saque para segurança

## 🆘 Problemas Comuns

### "API-key format invalid"
→ Verifique se copiou a chave completa sem espaços

### "Invalid API-key, IP, or permissions for action"
→ Adicione seu IP na whitelist da Binance

### "Signature for this request is not valid"
→ Verifique se a Secret Key está correta

### Conexão recusada
→ Verifique se não está usando VPN
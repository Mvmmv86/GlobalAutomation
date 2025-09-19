# GlobalAutomations AI

Uma plataforma completa para automação de serviços, incluindo trading de criptomoedas, marketing e suporte.

## 🏗️ Estrutura Atual do Projeto (Execução Nativa)

```
GlobalAutomation/
├── apps/
│   └── api-python/        # Backend FastAPI + Python (Operacional)
├── frontend-new/          # Frontend React/TypeScript (Operacional)
├── docs/                  # Documentação
├── venv/                  # Ambiente Python
└── CLAUDE.md             # Instruções para desenvolvimento
```

**Nota**: Sistema migrou para **execução nativa** (sem Docker) para melhor performance e menor consumo de CPU.

## 🚀 Como Executar (Sistema Nativo)

### Execução do Sistema Completo

```bash
# Backend FastAPI
cd /home/globalauto/global/apps/api-python
python3 main.py &

# Frontend React
cd /home/globalauto/global/frontend-new
PORT=3000 npm run dev &

# Auto Sync (Sincronização automática com Binance)
cd /home/globalauto/global/apps/api-python
./auto_sync.sh &
```

## 🔧 Configuração

O sistema está configurado para execução nativa:

- **Backend API**: http://localhost:8000
- **Frontend**: http://localhost:3000
- **Database**: Supabase (PostgreSQL remoto)
- **Environment**: `.env` configurado para produção

### Credenciais de Teste

- **Email**: `demo@tradingview.com`
- **Senha**: `demo123456`

## 🛠️ Desenvolvimento Local

### Pré-requisitos

- Python 3.11+
- Node.js 18+
- WSL2 (Windows) ou ambiente Linux/macOS

### Setup Inicial

1. Clone o repositório
2. Configure as variáveis de ambiente no `.env`
3. Instale dependências do backend: `pip install -r requirements.txt`
4. Instale dependências do frontend: `npm install`
5. Execute os comandos de inicialização acima

### Monitoramento

```bash
# Verificar status dos serviços
lsof -i:8000  # Backend
lsof -i:3000  # Frontend
ps aux | grep auto_sync  # Sincronização

# Logs em tempo real
tail -f logs/api.log    # Se existir
```

### Ambiente de Produção

- **Database**: Supabase PostgreSQL
- **API Keys**: Binance (configuradas no .env)
- **Deploy**: Execução nativa no servidor
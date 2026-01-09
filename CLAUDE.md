# CLAUDE.md
Este arquivo orienta o **Claude Code** (claude.ai/code) — e qualquer outro dev — a trabalhar de forma consistente e segura neste repositório.

---

## 1. Estado do Repositório
> *Atualize este bloco sempre que a estrutura principal mudar.*

| Data | Descrição |
|------|-----------|
| 2025-06-25 | Estrutura inicial (Dev Container + Docker Compose + pipelines CI) criada. |
| 2025-09-19 | **Sistema de Trading Operacional** - Dashboard funcionando com dados reais da Binance, sincronização automática implementada, projeto limpo e otimizado. |
| 2026-01-09 | **Migração para WSL + Droplet** - Ambiente de desenvolvimento migrado 100% para WSL Ubuntu. Produção migrada para Digital Ocean Droplet. |

---

## 2. Padrões de Linguagem & Frameworks

| Camada          | Stack Oficial                    | Observações |
|-----------------|----------------------------------|-------------|
| **Backend**     | **Python 3.12** + FastAPI        | Usar Pydantic e typer. Evitar Flask/Django salvo justificativa. |
| **Frontend**    | **React 18** (Vite)              | Components em TypeScript. Atomic-design + Tailwind. |
| **Scripts/CLI** | Python                           | Nada de Bash para lógicas complexas; manter `.py`. |
| **Infra**       | WSL2 Ubuntu (Nativo)             | Sem Docker para dev local. |

---

## 3. Fluxo de Planejamento Obrigatório

> **Regra de ouro**
> *Nenhum código ou comando destrutivo deve ser executado antes de um plano aprovado.*

1. **Análise da Demanda** – resumo em 3-5 frases, entradas/saídas.
2. **Plano de Ação** – etapas atômicas; marcar riscos (DB, infra).
3. **Validação de Riscos** – dependências, backup/rollback.
4. **Confirmação** – aguardar OK com tag `<!-- APPROVED -->`.
5. **Execução Controlada** – implementar somente o aprovado.
6. **Relatório Final** – arquivos alterados, comandos executados, SHA/PR.

> **Para Claude Code**
> Caso o solicitante não aprove explicitamente, **pare** e solicite detalhes.

---

## 4. Segurança de Execução & Dados

| Regra | Detalhe |
|-------|---------|
| **Sem comandos automáticos** | Nunca sugerir `python main.py`, `db-reset`, `DROP …` sem pedido explícito. |
| **⚠️ Git Push Manual** | **NUNCA fazer `git push` automaticamente**. Apenas fazer push quando o usuário **solicitar explicitamente** com palavras como "pode dar push", "faz o push", "envia pro github". Fazer commits locais normalmente, mas **SEMPRE aguardar autorização EXPLÍCITA para push**. |
| **⚠️ Git Commit Manual** | **NUNCA fazer `git commit` automaticamente**. Apenas fazer commit quando o usuário **solicitar explicitamente**. Preparar as mudanças e mostrar o que será commitado, mas **aguardar OK do usuário antes de commitar**. |
| **⚠️ Testar SEMPRE em localhost** | **NUNCA fazer deploy direto para produção**. SEMPRE testar as mudanças no ambiente local (localhost) primeiro. Só após o usuário confirmar que está funcionando localmente, prosseguir com commit/push. |
| **Migrations transacionais** | Alembic/Prisma em modo `--sql` primeiro; aplicar após revisão. |
| **Ambientes isolados** | `.env` define `ENV=dev/test/prod`; prod nunca hard-coded. |
| **Backups antes de dados críticos** | Ex.: `pg_dump ... > backup_$(date +%F).sql`. |
| **Permissões mínimas** | Usuários DB: `app_rw`, `app_migrator`; evitar `postgres` root. |

---

## 5. ⚠️ AMBIENTE DE DESENVOLVIMENTO - WSL OBRIGATÓRIO

### 🚨 REGRA CRÍTICA: SEMPRE RODAR NO WSL

**O ambiente de desenvolvimento DEVE rodar EXCLUSIVAMENTE no WSL Ubuntu.**

| Item | Caminho WSL | Status |
|------|-------------|--------|
| **Repositório** | `/home/claude/GlobalAutomation` | ✅ Principal |
| **Python venv** | `/home/claude/GlobalAutomation/venv` | ✅ Python 3.12 |
| **Node.js** | Sistema (v20.19.5) | ✅ Instalado |

### 📁 Estrutura de Diretórios

```
/home/claude/GlobalAutomation/
├── apps/
│   └── api-python/          # Backend FastAPI
├── frontend-new/            # Frontend Cliente (React)
├── frontend-admin/          # Frontend Admin (React)
├── venv/                    # Python virtual environment
├── .env                     # Variáveis de ambiente (NÃO COMMITAR)
└── deploy.sh                # Script de deploy automatizado
```

### 🔧 Configuração do .env (WSL)

O arquivo `.env` em `/home/claude/GlobalAutomation/.env` deve conter:

```bash
# Database
DATABASE_URL=postgresql+asyncpg://...

# Environment
ENV=development
DEBUG=true
PORT=8000

# Security Keys
SECRET_KEY=...
TV_WEBHOOK_SECRET=...
ENCRYPTION_KEY=...
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# IMPORTANTE: Para desenvolvimento local rápido
SKIP_HEAVY_MONITORS=true
```

**NOTA**: `SKIP_HEAVY_MONITORS=true` desabilita os monitores pesados (sync scheduler, indicator monitor, strategy websocket) para startup rápido em desenvolvimento.

---

## 6. Arquitetura e Portas do Sistema

### 🏗️ Serviços e Portas (Desenvolvimento Local)

| Serviço | Porta | Diretório WSL | Status |
|---------|-------|---------------|--------|
| **Backend API** | `8001` | `/home/claude/GlobalAutomation/apps/api-python/` | ✅ |
| **Frontend Cliente** | `3000` | `/home/claude/GlobalAutomation/frontend-new/` | ✅ |
| **Frontend Admin** | `3001` | `/home/claude/GlobalAutomation/frontend-admin/` | ✅ |

### 🔄 Fluxo de Dados

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Binance API   │ -> │  Backend FastAPI │ -> │ Frontend React  │
│   (Real-time)   │    │   (Port 8001)    │    │  (Port 3000)    │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │
                      ┌─────────▼─────────┐
                      │  PostgreSQL DB    │
                      │    (Supabase)     │
                      └───────────────────┘
```

### 📡 Endpoints Principais

| Endpoint | Função |
|----------|--------|
| `/api/v1/dashboard/balances` | Dados principais - SPOT/FUTURES + P&L |
| `/api/v1/auth/login` | Autenticação |
| `/api/v1/dashboard/active-positions` | Posições ativas |
| `/api/v1/dashboard/stats` | Estatísticas |

---

## 7. Comandos Essenciais - WSL

### 🚀 Iniciar o Sistema (FORMA RECOMENDADA)

```bash
# 1. Entrar no WSL
wsl

# 2. Ir para o diretório do projeto
cd /home/claude/GlobalAutomation

# 3. Ativar o venv e carregar variáveis
source venv/bin/activate
set -a && source .env && set +a

# 4. Iniciar Backend (porta 8001)
cd apps/api-python
setsid uvicorn main:app --host 0.0.0.0 --port 8001 > /tmp/backend.log 2>&1 &

# 5. Iniciar Frontend Cliente (porta 3000)
cd /home/claude/GlobalAutomation/frontend-new
setsid npm run dev > /tmp/frontend.log 2>&1 &

# 6. Iniciar Frontend Admin (porta 3001)
cd /home/claude/GlobalAutomation/frontend-admin
setsid npm run dev -- --port 3001 > /tmp/admin.log 2>&1 &
```

### 📋 Comandos Úteis

```bash
# Verificar processos rodando
ps aux | grep -E "uvicorn|node|vite" | grep -v grep

# Ver logs em tempo real
tail -f /tmp/backend.log
tail -f /tmp/frontend.log
tail -f /tmp/admin.log

# Parar todos os serviços
pkill -f uvicorn
pkill -f "node.*vite"

# Reiniciar WSL (se necessário)
wsl --shutdown  # No Windows
wsl             # Reiniciar

# Verificar uso de memória
free -h

# Testar Backend
curl http://127.0.0.1:8001/
```

### 🌐 URLs de Acesso Local

| Serviço | URL |
|---------|-----|
| **Backend API** | http://localhost:8001 |
| **Frontend Cliente** | http://localhost:3000 |
| **Frontend Admin** | http://localhost:3001 |

---

## 8. 🚀 PRODUÇÃO - Digital Ocean Droplet

### 🔐 Credenciais do Droplet

| Item | Valor |
|------|-------|
| **IP** | `167.71.14.195` |
| **Usuário** | `root` |
| **Acesso** | SSH com chave (`~/.ssh/id_rsa`) |
| **Projeto** | `/root/GlobalAutomation` |

### 🔌 Conectar ao Droplet

```bash
ssh root@167.71.14.195
```

### 🚀 Deploy no Droplet

#### Opção 1: Script Automatizado (RECOMENDADO)

```bash
cd /home/claude/GlobalAutomation
./deploy.sh droplet   # Apenas deploy no droplet
./deploy.sh full      # Commit + push + merge + deploy completo
```

#### Opção 2: Deploy Manual

```bash
ssh root@167.71.14.195 << 'ENDSSH'
cd /root/GlobalAutomation
git pull origin main
cd apps/api-python
source venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart globalautomation
ENDSSH
```

### 📊 Verificar Status no Droplet

```bash
# Status do serviço
ssh root@167.71.14.195 'systemctl status globalautomation'

# Logs recentes
ssh root@167.71.14.195 'journalctl -u globalautomation -n 50'

# Logs em tempo real
ssh root@167.71.14.195 'journalctl -u globalautomation -f'
```

### 🌐 URLs de Produção

| Serviço | URL |
|---------|-----|
| **Backend API** | `http://167.71.14.195:8000` |
| **API Docs** | `http://167.71.14.195:8000/docs` |

---

## 9. Git Workflow

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│ development │ --> │    main     │ --> │   Droplet   │ --> │  Produção   │
│  (código)   │     │  (stable)   │     │   (deploy)  │     │   (live)    │
└─────────────┘     └─────────────┘     └─────────────┘     └─────────────┘
```

1. Desenvolver na branch `development`
2. Testar localmente (localhost:8001)
3. Commit e push para `development`
4. Merge para `main` quando estiver pronto
5. Push para `main`
6. Deploy no droplet: `./deploy.sh droplet`

---

## 10. Troubleshooting

### Problema: Backend não inicia / trava no startup
**Solução**: Verificar se `SKIP_HEAVY_MONITORS=true` está no `.env`

### Problema: Frontend não conecta ao Backend
**Solução**: Verificar se o `.env` do frontend tem `VITE_API_URL=http://localhost:8001`

### Problema: Processos Node/Vite morrem
**Solução**: Usar `setsid` ao invés de `nohup` para manter processos rodando

### Problema: WSL consumindo muita memória
**Solução**: `wsl --shutdown` no Windows e reiniciar

### Problema: Erro de CORS
**Solução**: O settings.py já tem defaults corretos. NÃO definir CORS_ORIGINS no .env (o bash corrompe o JSON)

### Problema: Deploy falha no droplet
**Solução**: Verificar SSH key, conexão, e se o serviço está configurado no systemd

---

## 11. Regras para Claude Code

1. **SEMPRE executar comandos via WSL**: Use `wsl bash -c "comando"` para qualquer operação
2. **NUNCA editar arquivos diretamente no Windows**: Sempre copiar para WSL após edição
3. **Verificar .env antes de iniciar**: Garantir que variáveis estão corretas
4. **Usar setsid para processos em background**: `setsid comando &` mantém processos vivos
5. **Logs em /tmp/**: Backend em `/tmp/backend.log`, Frontend em `/tmp/frontend.log`
6. **Deploy**: Usar `./deploy.sh` ou SSH manual para o droplet `167.71.14.195`

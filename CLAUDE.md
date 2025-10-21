# CLAUDE.md
Este arquivo orienta o **Claude Code** (claude.ai/code) — e qualquer outro dev — a trabalhar de forma consistente e segura neste repositório.

---

## 1. Estado do Repositório
> *Atualize este bloco sempre que a estrutura principal mudar.*

| Data | Descrição |
|------|-----------|
| 2025-06-25 | Estrutura inicial (Dev Container + Docker Compose + pipelines CI) criada. |
| 2025-09-19 | **Sistema de Trading Operacional** - Dashboard funcionando com dados reais da Binance, sincronização automática implementada, projeto limpo e otimizado. |
| 2025-10-21 | **Limpeza Completa do Repositório** - Removidos completamente todos os vestígios Docker, diretórios legados (services/, apps/web/, apps/api/, workers, frontends antigos). Sistema 100% nativo confirmado. Backup criado em `/backups/cleanup-2025-10-21/`. |

---

## 2. Padrões de Linguagem & Frameworks

| Camada          | Stack Oficial                    | Observações |
|-----------------|----------------------------------|-------------|
| **Backend**     | **Python 3.11** + FastAPI        | Usar Pydantic e typer. Evitar Flask/Django salvo justificativa. |
| **Frontend**    | **React 18** (Vite)              | Components em TypeScript. Atomic-design + Tailwind. |
| **Scripts/CLI** | Python                           | Nada de Bash para lógicas complexas; manter `.py`. |
| **Infra**       | **Execução Nativa** (Sem Docker) | Deploy direto no servidor. PostgreSQL via Supabase. Process manager (PM2/systemd). |

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
| **Migrations transacionais** | Alembic/Prisma em modo `--sql` primeiro; aplicar após revisão. |
| **Ambientes isolados** | `.env` define `ENV=dev/test/prod`; prod nunca hard-coded. |
| **Backups antes de dados críticos** | Ex.: `pg_dump ... > backup_$(date +%F).sql`. |
| **Permissões mínimas** | Usuários DB: `app_rw`, `app_migrator`; evitar `postgres` root. |
| **Safe directory Git** | No Dev Container: `git config --global --add safe.directory /workspace`. |

---

## 5. Arquitetura e Portas do Sistema

### 🏗️ Estrutura Atual Funcionando (Execução Nativa - Sem Docker)

| Serviço | Porta | Diretório | Status |
|---------|-------|-----------|--------|
| **Backend API** | `8000` | `/apps/api-python/` | ✅ Operacional (python3 main.py) |
| **Frontend React** | `3000` | `/frontend-new/` | ✅ Operacional (npm run dev) |
| **Auto Sync** | - | `/apps/api-python/auto_sync.sh` | ✅ Ativo (30s) |

### 📝 Nota Importante sobre Docker

**Sistema atual**: Execução **NATIVA** (sem containers)
- ✅ **Melhor performance**: Sem overhead de containers
- ✅ **Menos CPU**: Resolveu problemas de consumo excessivo
- ✅ **Mais simples**: Deploy direto no ambiente (WSL2/Linux)

**Docker**: ❌ **COMPLETAMENTE REMOVIDO** (21/Out/2025)
- ✅ Todos os `Dockerfile*` removidos
- ✅ `docker-compose.backup.yml` removido
- ✅ `.devcontainer/` removido
- ✅ Configs relacionadas (`Caddyfile`, `turbo.json`, `pnpm-workspace.yaml`) removidos
- 📦 Backup completo salvo em `/backups/cleanup-2025-10-21/` (107MB)
- **Decisão**: Sistema funciona 100% nativo, sem planos de retornar ao Docker

### 🔄 Fluxo de Dados Implementado

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Binance API   │ -> │  Backend FastAPI │ -> │ Frontend React  │
│   (Real-time)   │    │   (Port 8000)    │    │  (Port 3000)    │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                        │                       │
         │              ┌─────────▼─────────┐             │
         │              │  PostgreSQL DB   │             │
         │              │    (Supabase)    │             │
         │              └───────────────────┘             │
         │                                                │
         └──────────── Auto Sync (30s) ◄──────────────────┘
```

### 📡 Endpoints Principais Funcionando

| Endpoint | Função | Frontend Hook |
|----------|--------|--------------|
| `/api/v1/dashboard/balances` | **Dados principais** - SPOT/FUTURES + P&L | `useBalancesSummary` |
| `/api/v1/sync/balances/{id}` | Sincronização automática | Auto Sync Script |
| `/api/v1/auth/login` | Autenticação | `useAuth` |
| `/api/v1/orders/stats` | Estatísticas de ordens | `useOrdersStats` |
| `/api/v1/positions/metrics` | Métricas de posições | `usePositionsMetrics` |

### 🎯 Configuração de Cache e Atualização

**Frontend (React Query)**:
```typescript
// useBalancesSummary - Atualização agressiva
staleTime: 0,           // Dados sempre considerados stale
gcTime: 0,              // Sem cache garbage collection
refetchInterval: 10000, // Refetch a cada 10 segundos
```

**Backend (P&L Real-time)**:
```python
# Dashboard Controller - Busca direta da Binance API
connector = BinanceConnector(api_key, api_secret, testnet=False)
positions_result = await connector.get_futures_positions()
# Calcula P&L em tempo real das posições
```

---

## 6. Comandos Essenciais

```bash
# Iniciar o sistema completo (Execução Nativa)
cd /home/globalauto/global/apps/api-python && python3 main.py &     # Backend API
cd /home/globalauto/global/frontend-new && PORT=3000 npm run dev &  # Frontend React
cd /home/globalauto/global/apps/api-python && ./auto_sync.sh &      # Auto Sync

# IMPORTANTE: Sistema roda NATIVO (sem Docker)
# Melhor performance e menor consumo de CPU

# Verificar status dos serviços
lsof -i:8000  # Backend
lsof -i:3000  # Frontend
ps aux | grep auto_sync  # Sincronização

# Desenvolvimento
pre-commit run --all-files              # lint + format + testes rápidos
pytest -q                               # suíte completa
make docs                               # gera documentação (se aplicável)
```

---

## 7. Estrutura Limpa do Projeto

> **Última atualização**: 21/Out/2025 (após limpeza completa)

```
GlobalAutomation/
├── apps/
│   └── api-python/              ✅ Backend FastAPI (ÚNICO backend ativo)
│       ├── main.py              → Entry point
│       ├── application/         → Services
│       ├── domain/              → Models & Interfaces
│       ├── infrastructure/      → DB, Exchanges, Cache, Security
│       ├── presentation/        → Controllers (API endpoints)
│       ├── auto_sync.sh         → Script de sincronização (30s)
│       ├── requirements.txt     → Dependências Python
│       └── .env                 → Configuração (não commitar)
│
├── frontend-new/                ✅ Frontend React (ÚNICO frontend ativo)
│   ├── src/
│   │   ├── components/          → Atomic Design (atoms/molecules/organisms/pages)
│   │   ├── hooks/               → React hooks customizados
│   │   ├── services/            → API client (axios)
│   │   ├── contexts/            → React Context (Auth, Theme)
│   │   └── types/               → TypeScript types
│   ├── package.json             → Dependências Node
│   └── .env                     → Config API URL (não commitar)
│
├── backups/                     ✅ Backups e histórico
│   └── cleanup-2025-10-21/      → Backup da limpeza (107MB)
│       ├── services_backup.tar.gz
│       ├── apps_legados_backup.tar.gz
│       └── frontends_antigos_backup.tar.gz
│
├── docs/                        ✅ Documentação do projeto
├── packages/                    ✅ Packages compartilhados (se usado)
├── shared/                      ✅ Utilitários compartilhados
├── venv/                        ⚠️ Virtual env Python (não commitar)
│
├── CLAUDE.md                    📖 Este arquivo
├── README.md                    📖 Documentação principal
├── .env.example                 📝 Template de configuração
├── .gitignore                   🚫 Arquivos ignorados
├── package.json                 📦 Config monorepo (se usado)
└── requirements.txt             📦 Dependências raiz (se usado)
```

### ❌ Removidos (21/Out/2025)

| Diretório/Arquivo | Motivo |
|-------------------|--------|
| `/services/` | Microserviços antigos (era duplicado de `/apps/api-python/`) |
| `/apps/api/` | API TypeScript antiga (substituída por FastAPI Python) |
| `/apps/web/` | Frontend Next.js antigo (substituído por Vite) |
| `/apps/web-trading/` | Cópia desatualizada do `/frontend-new/` |
| `/apps/worker-exec/` | Worker de execução não usado |
| `/apps/worker-recon/` | Worker de reconciliação não usado |
| `/frontend/` | Frontend antigo |
| `/frontend-backup/` | Backup de frontend |
| `/.devcontainer/` | Dev Container (não usamos mais) |
| Todos `Dockerfile*` | Não usamos Docker |
| `docker-compose.backup.yml` | Config Docker antiga |
| `Caddyfile` | Proxy reverso antigo |
| `turbo.json` | Monorepo não configurado |
| `pnpm-workspace.yaml` | Workspace não usado |

### ✅ Mantidos e Ativos

| Componente | Status | Observação |
|------------|--------|------------|
| `/apps/api-python/` | 🟢 ATIVO | Backend principal - Python 3.11 + FastAPI |
| `/frontend-new/` | 🟢 ATIVO | Frontend principal - React 18 + Vite |
| `/backups/` | 🟡 HISTÓRICO | Backups importantes preservados |
| `/docs/` | 🟡 DOCUMENTAÇÃO | Reports e documentação técnica |
| `/shared/` | 🟡 UTILITÁRIOS | Libs compartilhadas (se necessário) |

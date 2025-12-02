# CLAUDE.md
Este arquivo orienta o **Claude Code** (claude.ai/code) — e qualquer outro dev — a trabalhar de forma consistente e segura neste repositório.

---

## 1. Estado do Repositório
> *Atualize este bloco sempre que a estrutura principal mudar.*

| Data | Descrição |
|------|-----------|
| 2025-06-25 | Estrutura inicial (Dev Container + Docker Compose + pipelines CI) criada. |
| 2025-09-19 | **Sistema de Trading Operacional** - Dashboard funcionando com dados reais da Binance, sincronização automática implementada, projeto limpo e otimizado. |

---

## 2. Padrões de Linguagem & Frameworks

| Camada          | Stack Oficial                    | Observações |
|-----------------|----------------------------------|-------------|
| **Backend**     | **Python 3.11** + FastAPI        | Usar Pydantic e typer. Evitar Flask/Django salvo justificativa. |
| **Frontend**    | **React 18** (Vite)              | Components em TypeScript. Atomic-design + Tailwind. |
| **Scripts/CLI** | Python                           | Nada de Bash para lógicas complexas; manter `.py`. |
| **Infra**       | Docker Compose, Dev Containers   | Manifests K8s via Helm em `/k8s`. |

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
| **Safe directory Git** | No Dev Container: `git config --global --add safe.directory /workspace`. |

---

## 5. Arquitetura e Portas do Sistema

### 🏗️ Estrutura Atual Funcionando (Execução Nativa - Sem Docker)

| Serviço | Porta | Diretório | Status |
|---------|-------|-----------|--------|
| **Backend API** | `8001` | `/apps/api-python/` | ✅ Operacional (python3 -m uvicorn main:app --host 0.0.0.0 --port 8001) |
| **Frontend React** | `3000` | `/frontend-new/` | ✅ Operacional (npm run dev) |
| **Auto Sync** | - | `/apps/api-python/auto_sync.sh` | ⚠️ Desabilitado para dev local |

### 📝 Nota Importante sobre Docker

**Sistema atual**: Execução **NATIVA** (sem containers)
- ✅ **Melhor performance**: Sem overhead de containers
- ✅ **Menos CPU**: Resolveu problemas de consumo excessivo
- ✅ **Mais simples**: Deploy direto no ambiente WSL2

**Docker Compose**: ❌ **Removido do projeto**
- Arquivo `docker-compose.yml` → Movido para `docker-compose.backup.yml`
- Diretórios Docker órfãos → Identificados (alguns com permissões restritas)
- Sistema funciona 100% nativo agora

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

### 🌐 URLs de Produção (Digital Ocean)

| Serviço | URL | Descrição |
|---------|-----|-----------|
| **Frontend** | https://globalautomation-frontend-g9gmr.ondigitalocean.app | Interface Web (React) |
| **Backend API** | https://globalautomation-tqu2m.ondigitalocean.app | API FastAPI |
| **API Docs** | https://globalautomation-tqu2m.ondigitalocean.app/docs | Documentação Swagger |
| **Health Check** | https://globalautomation-tqu2m.ondigitalocean.app/health | Status da API |
| **Login** | https://globalautomation-frontend-g9gmr.ondigitalocean.app/login | Página de Login |

**Endpoints Principais**:
- Dashboard: `/api/v1/dashboard/balances`
- Autenticação: `/api/v1/auth/login`
- Sincronização: `/api/v1/sync/balances/{id}`

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

# CLAUDE.md
Este arquivo orienta o **Claude Code** (claude.ai/code) — e qualquer outro dev — a trabalhar de forma consistente e segura neste repositório.

---

## 1. Estado do Repositório
> *Atualize este bloco sempre que a estrutura principal mudar.*

| Data | Descrição |
|------|-----------|
| 2025-06-25 | Estrutura inicial (Dev Container + Docker Compose + pipelines CI) criada. |

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
| **Migrations transacionais** | Alembic/Prisma em modo `--sql` primeiro; aplicar após revisão. |
| **Ambientes isolados** | `.env` define `ENV=dev/test/prod`; prod nunca hard-coded. |
| **Backups antes de dados críticos** | Ex.: `pg_dump ... > backup_$(date +%F).sql`. |
| **Permissões mínimas** | Usuários DB: `app_rw`, `app_migrator`; evitar `postgres` root. |
| **Safe directory Git** | No Dev Container: `git config --global --add safe.directory /workspace`. |

---

## 5. Comandos Essenciais

```bash
# Dev Container
docker compose up service-template      # sobe FastAPI + deps
pre-commit run --all-files              # lint + format + testes rápidos
pytest -q                               # suíte completa
make docs                               # gera documentação (se aplicável)

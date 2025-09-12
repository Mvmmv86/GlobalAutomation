# 🚀 Nova Estrutura do Repositório GlobalAutomation

## 🎯 Visão Geral

O repositório foi reestruturado para suportar múltiplos serviços de forma organizada e escalável. A nova estrutura é baseada em um monorepo com separação clara de responsabilidades entre serviços, frontend, infraestrutura e código compartilhado.

## 🏗️ Estrutura de Diretórios

```
GlobalAutomation/
├── 🔧 services/                    # Todos os serviços da plataforma
│   ├── 💰 trading/                # Serviços de trading de cripto
│   │   ├── api-service/           # Backend API (Python/FastAPI)
│   │   ├── execution-service/     # Worker de execução (Node.js/TypeScript)
│   │   └── reconciliation-service/ # Worker de reconciliação (Node.js/TypeScript)
│   ├── 📈 marketing/              # (Futuro) Serviços de marketing
│   ├── 🎧 support/                # (Futuro) Serviços de suporte
│   └── ⚙️ core/                   # (Futuro) Serviços centrais
├── 🖥️ frontend/                   # Aplicações frontend
│   ├── trading-dashboard/         # Dashboard de trading (React/TypeScript)
│   ├── marketing-panel/           # (Futuro) Painel de marketing
│   └── support-portal/            # (Futuro) Portal de suporte
├── 📦 shared/                     # Código compartilhado
│   ├── libs/                      # Bibliotecas comuns
│   ├── models/                    # Modelos de dados
│   ├── utils/                     # Utilitários
│   └── templates/                 # Templates para novos serviços
├── 🏗️ infrastructure/             # Configurações de infraestrutura
│   ├── docker/                    # Dockerfiles específicos
│   ├── k8s/                       # (Futuro) Manifests Kubernetes
│   └── monitoring/                # (Futuro) Configurações de monitoramento
└── 📖 docs/                       # Documentação
    ├── api/                       # Documentação das APIs
    ├── architecture/              # Diagramas de arquitetura
    └── deployment/                # Guias de deployment
```

## 🔧 Serviços

### Trading
- **api-service**: Backend principal em Python/FastAPI que recebe os webhooks do TradingView e gerencia as ordens.
- **execution-service**: Worker em Node.js/TypeScript responsável pela execução das ordens nas exchanges.
- **reconciliation-service**: Worker em Node.js/TypeScript que reconcilia os dados entre a plataforma e as exchanges.

### Marketing e Suporte (Futuro)
- A estrutura está pronta para receber novos serviços de marketing e suporte, seguindo o mesmo padrão dos serviços de trading.

## 🖥️ Frontend

- **trading-dashboard**: Dashboard em React/TypeScript para visualização de métricas, ordens, posições e configuração da plataforma.

## 📦 Código Compartilhado

- **libs**: Bibliotecas e código reutilizável entre os serviços.
- **templates**: Templates para criação de novos serviços (Python/FastAPI e Vue.js).

## 🏗️ Infraestrutura

- **docker-compose.yml**: Arquivo de orquestração de serviços para ambiente de desenvolvimento local.
- **Dockerfiles**: Arquivos de configuração para construção das imagens Docker de cada serviço.

## 🚀 Próximos Passos

1. **Finalizar a migração**: Garantir que todos os serviços estão funcionando corretamente na nova estrutura.
2. **Desenvolver novos serviços**: Utilizar os templates para criar os serviços de marketing e suporte.
3. **Preparar para produção**: Criar os manifests Kubernetes e configurar o ambiente de produção.

Esta nova estrutura fornece uma base sólida para o crescimento da plataforma GlobalAutomation, permitindo o desenvolvimento de múltiplos serviços de forma organizada e escalável.


# GlobalAutomations AI

Uma plataforma completa para automação de serviços, incluindo trading de criptomoedas, marketing e suporte.

## 🏗️ Estrutura do Projeto

```
GlobalAutomation/
├── services/
│   └── trading/           # Serviços de trading
│       ├── api-service/   # Backend Python/FastAPI
│       ├── execution-service/
│       └── reconciliation-service/
├── frontend/
│   └── trading-dashboard/ # Frontend React/TypeScript
├── shared/
│   └── templates/         # Templates para novos serviços
├── infrastructure/        # Docker, K8s, configs
└── docs/                  # Documentação
```

## 🚀 Como Executar

### Opção 1: Desenvolvimento Local (Recomendado)

```bash
# Backend
cd services/trading/api-service
pip install -r requirements.txt
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Frontend (em outro terminal)
cd frontend/trading-dashboard
npm install
npm run dev
```

### Opção 2: Com Docker Compose

```bash
# Subir todos os serviços
docker-compose up -d

# Ou apenas alguns serviços
docker-compose up postgres redis api-service trading-dashboard
```

## 🔧 Configuração Inteligente

O sistema detecta automaticamente o ambiente:

- **Desenvolvimento Local**: Usa `localhost:8000`
- **Docker**: Usa `api-service:8000`  
- **Personalizado**: Define `VITE_API_URL` no `.env`

### Credenciais de Teste

- **Email**: `demo@tradingview.com`
- **Senha**: `demo123456`

## Local Development

### Prerequisites

- Docker and Docker Compose
- VS Code with Dev Containers extension

### Setup

1. Clone the repository
2. Open in VS Code
3. Click "Reopen in Container" when prompted
4. Services will start automatically via docker-compose

### Services

- **API**: http://localhost:8000
- **PostgreSQL**: localhost:5432
- **Redis**: localhost:6379

### Environment Variables

Copy `.env.example` to `.env` and configure:

```bash
POSTGRES_USER=globalautomations
POSTGRES_DB=globalautomations
POSTGRES_PASSWORD=your_password
```

### Running Tests

```bash
docker compose run --rm service-template pytest
```

### Building Services

```bash
docker compose build
```
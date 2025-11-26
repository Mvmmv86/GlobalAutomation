# GlobalAutomations AI

A platform for AI-powered automation services and bot management.

## Architecture

- **shared/**: Common services and utilities
- **platform-services/**: Core platform services  
- **bots/**: AI bot implementations
- **reports/**: Reporting and analytics services

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
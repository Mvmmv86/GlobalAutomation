# Integration Tests

Este diretório contém testes de integração abrangentes para o sistema TradingView Gateway, incluindo testes end-to-end, validação de webhooks, tratamento de erros e testes de performance.

## Estrutura dos Testes

### 📁 Arquivos de Teste

- **`webhook-flow.test.ts`** - Testes do fluxo completo webhook → trade
- **`webhook-validation.test.ts`** - Validação de webhooks do TradingView
- **`error-handling.test.ts`** - Cenários de erro e recuperação
- **`performance.test.ts`** - Testes de carga e performance

### 🔧 Configuração

- **`jest.config.js`** - Configuração do Jest para testes
- **`setup.ts`** - Setup global dos testes
- **`package.json`** - Dependencies e scripts específicos

## Como Executar

### Todos os Testes
```bash
cd packages/shared/src/test/integration
npm test
```

### Testes Específicos
```bash
# Testes de webhook
npm run test:webhook

# Testes de performance
npm run test:performance

# Testes de error handling
npm run test:error

# Testes de fluxo completo
npm run test:flow
```

### Com Coverage
```bash
npm run test:coverage
```

### Modo Watch
```bash
npm run test:watch
```

## Cenários Testados

### 🔄 Fluxo Webhook → Trade
- ✅ Processamento de ordens buy/sell
- ✅ Ordens market e limit
- ✅ Stop loss e take profit
- ✅ Leverage e margin
- ✅ Reduce only orders
- ✅ Validação de saldo
- ✅ Tracking de posições
- ✅ Multiple símbolos

### 🔐 Validação de Webhooks
- ✅ Verificação de assinatura HMAC
- ✅ Validação de campos obrigatórios
- ✅ Validação de timestamp
- ✅ Processamento de JSON malformado
- ✅ Campos customizados
- ✅ Processamento concorrente

### ⚠️ Error Handling
- ✅ Classificação de erros
- ✅ Retry com exponential backoff
- ✅ Circuit breaker patterns
- ✅ Rate limiting
- ✅ Network timeouts
- ✅ Exchange maintenance
- ✅ Insufficient balance
- ✅ Graceful degradation

### 🚀 Performance & Load
- ✅ Ordens concorrentes
- ✅ High-frequency requests
- ✅ Burst trading scenarios
- ✅ Mixed operation load
- ✅ Cache performance
- ✅ Memory usage
- ✅ Accuracy under load
- ✅ Connection pooling

## Mock Exchange Adapter

Os testes utilizam um `MockExchangeAdapter` que simula:

- ✅ Latência de rede realística
- ✅ Erros configuráveis
- ✅ Balances e posições
- ✅ Execução de ordens
- ✅ Validação de margem
- ✅ Estado consistente

### Configuração do Mock

```typescript
const mockExchange = new MockExchangeAdapter(
  { apiKey: 'test', secret: 'test' },
  {
    simulateLatency: 50,        // 50ms latência
    simulateErrors: false,      // Sem erros
    errorRate: 0.1,            // 10% erro rate
    balances: { 
      USDT: 10000, 
      BTC: 0.5 
    },
    positions: [],
    orders: []
  }
);
```

## Métricas de Coverage

O objetivo é manter **>80% coverage** em:
- ✅ Branches
- ✅ Functions  
- ✅ Lines
- ✅ Statements

## CI/CD Integration

Para uso em pipelines:

```bash
npm run test:ci
```

Gera reports em:
- `coverage/` - Coverage HTML
- `test-results/` - JUnit XML

## Debugging

### Logs Detalhados
```bash
npm run test:verbose
```

### Teste Específico
```bash
npx jest "webhook-flow" --verbose
```

### Com Debugging
```bash
node --inspect-brk node_modules/.bin/jest --runInBand
```

## Helpers Globais

Disponíveis em todos os testes:

```typescript
// Delay async
await global.testHelpers.delay(1000);

// Random data
const randomStr = global.testHelpers.randomString(10);
const randomNum = global.testHelpers.randomNumber(1, 100);
const randomPrice = global.testHelpers.randomPrice('BTCUSDT');

// Test data creators
const order = global.testHelpers.createTestOrder({ side: 'sell' });
const webhook = global.testHelpers.createTestWebhook({ action: 'buy' });
```

## Ambiente de Teste

Os testes configuram automaticamente:

- ✅ NODE_ENV=test
- ✅ Mock database URL
- ✅ Mock Redis URL  
- ✅ Test webhook secret
- ✅ Console log filtering
- ✅ Error handlers
- ✅ Mock fetch global

## Contribuindo

1. Adicione testes para novos cenários
2. Mantenha coverage >80%
3. Use helpers globais quando possível
4. Documente cenários complexos
5. Teste tanto success quanto failure paths

## Performance Benchmarks

### Targets Esperados

- **Latência média**: <100ms por operação
- **Throughput**: >100 ops/segundo
- **Memory**: <50MB increase para 1000 ops
- **Concurrent orders**: 50+ simultâneas
- **Cache hit**: >90% em repeated requests

### Load Testing

Os testes incluem cenários de:
- 100+ operações concorrentes
- Burst de 20 ordens em <1s
- Mixed workload sustentado
- High-frequency price requests
- Memory leak detection
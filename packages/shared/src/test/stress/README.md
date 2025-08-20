# Stress Testing Suite

Sistema completo de testes de stress, carga e estabilidade para o TradingView Gateway. Inclui testes de load, spike e endurance para validar o comportamento do sistema sob condições extremas.

## 📋 Tipos de Teste

### 🚀 Load Testing (`load-test.ts`)
Testa o sistema sob carga sustentada com múltiplos usuários concorrentes.

**Cenários:**
- **Light**: 10 usuários por 30s
- **Medium**: 50 usuários por 60s  
- **Heavy**: 100 usuários por 120s
- **Burst**: 200 usuários por 30s

### 🌊 Spike Testing (`spike-test.ts`)
Testa o comportamento durante picos súbitos de tráfego.

**Fases:**
1. **Baseline**: Carga normal
2. **Spike**: Aumento súbito de tráfego
3. **Recovery**: Retorno ao normal

**Cenários:**
- **Small**: 10→50→10 usuários
- **Medium**: 20→100→20 usuários
- **Large**: 30→200→30 usuários
- **Extreme**: 50→500→50 usuários

### ⏰ Endurance Testing (`endurance-test.ts`)
Testa estabilidade e vazamentos de memória durante execução prolongada.

**Cenários:**
- **Short**: 5 minutos
- **Medium**: 15 minutos
- **Long**: 30 minutos
- **Marathon**: 60 minutos

## 🚦 Como Executar

### Load Tests
```bash
cd packages/shared/src/test/stress

# Testes individuais
npm run load:light
npm run load:medium
npm run load:heavy
npm run load:burst
```

### Spike Tests
```bash
# Testes de pico
npm run spike:small
npm run spike:medium
npm run spike:large
npm run spike:extreme
```

### Endurance Tests
```bash
# Testes de resistência
npm run endurance:short
npm run endurance:medium
npm run endurance:long
npm run endurance:marathon
```

### Suites Completas
```bash
# Suite leve (CI/CD)
npm run all:light

# Suite média (testes regulares)
npm run all:medium

# Suite pesada (validação completa)
npm run all:heavy

# Para CI/CD (rápido)
npm run test:ci
```

## 📊 Métricas Coletadas

### Load Testing
- ✅ **Total de operações**
- ✅ **Operações bem-sucedidas/falhadas**
- ✅ **Latência média/máxima/mínima**
- ✅ **Throughput** (ops/segundo)
- ✅ **Taxa de erro**
- ✅ **Uso de memória**
- ✅ **Distribuição de latência** (P50, P75, P90, P95, P99)

### Spike Testing
- ✅ **Degradação de performance**
- ✅ **Tempo de recuperação**
- ✅ **Aumento de latência** (%)
- ✅ **Redução de throughput** (%)
- ✅ **Aumento da taxa de erro** (%)

### Endurance Testing
- ✅ **Vazamento de memória** (MB/hora)
- ✅ **Degradação de performance** (%/hora)
- ✅ **Estabilidade ao longo do tempo**
- ✅ **Tendências de latência/throughput**

## 🎯 Critérios de Sucesso

### Load Testing
- ✅ Taxa de erro < 5%
- ✅ Latência média < 200ms
- ✅ P95 latência < 500ms
- ✅ Memory usage < 50MB increase per 1k ops

### Spike Testing
- ✅ Degradação de latência < 100%
- ✅ Aumento de erro < 5%
- ✅ Tempo de recuperação < 30s
- ✅ Throughput mantém > 50% do baseline

### Endurance Testing
- ✅ Memory leak < 20 MB/hora
- ✅ Degradação de performance < 10%/hora
- ✅ Taxa de erro estável
- ✅ Sem falhas críticas

## 📈 Exemplo de Saída

### Load Test Results
```
🎯 === LOAD TEST RESULTS ===
📈 Operations: 1247 total, 1235 success, 12 failed
⚡ Throughput: 41.57 ops/sec
⏱️  Average Latency: 45.23ms
📊 Latency Distribution:
   P50: 42.00ms
   P90: 67.00ms
   P95: 89.00ms
   P99: 156.00ms
   Max: 234.00ms
❌ Error Rate: 0.96%
💾 Memory Usage: 15.43MB increase, 89.12MB peak
```

### Spike Test Results
```
🌊 === SPIKE TEST RESULTS ===
📊 Baseline Phase: 25.43 ops/sec, 45ms avg latency
⚡ Spike Phase: 18.76 ops/sec, 127ms avg latency  
🔄 Recovery Phase: 24.89 ops/sec, 48ms avg latency
📈 Impact Analysis:
   Latency Increase: 182.22%
   Throughput Decrease: 26.20%
   Error Rate Increase: 2.15%
   Recovery Time: 15.30s
```

## 🔧 Configuração

Cada teste pode ser configurado editando os arquivos:

### Load Test Config
```typescript
const config: LoadTestConfig = {
  concurrency: 50,
  duration: 60, // seconds
  rampUpTime: 10,
  operations: {
    placeOrder: 50, // 50% das operações
    getTicker: 25,
    getBalance: 15, 
    getPositions: 10
  }
};
```

### Mock Exchange Config
```typescript
const mockExchange = new MockExchangeAdapter(
  { apiKey: 'test', secret: 'test' },
  {
    simulateLatency: 50,     // 50ms de latência
    simulateErrors: false,   // Sem erros simulados
    errorRate: 0.1,         // 10% de taxa de erro
    balances: { 
      USDT: 100000,         // $100k USDT
      BTC: 10               // 10 BTC
    }
  }
);
```

## 🔍 Debugging

### Logs Detalhados
```bash
DEBUG=1 npm run load:medium
```

### Profile de Memória
```bash
node --inspect npm run endurance:long
```

### CPU Profiling
```bash
node --prof npm run load:heavy
```

## 📋 Checklist CI/CD

Para integração em pipelines:

```yaml
# .github/workflows/stress-test.yml
- name: Run Stress Tests
  run: |
    cd packages/shared/src/test/stress
    npm install
    npm run test:ci
```

### Critérios de Falha
- ✅ Taxa de erro > 5%
- ✅ Latência média > 200ms
- ✅ Memory leak > 50MB/hora
- ✅ Recovery time > 60s
- ✅ Degradação > 300%

## 📊 Benchmarks de Referência

### Hardware Base
- **CPU**: 4 cores, 2.4GHz
- **RAM**: 8GB
- **Storage**: SSD

### Performance Targets
- **Load**: >100 ops/sec sustained
- **Spike**: <100% latency increase  
- **Endurance**: <10MB/hour memory growth
- **Recovery**: <30s return to baseline

## 🛠️ Troubleshooting

### High Error Rates
```bash
# Check mock exchange config
# Reduce concurrency
# Increase timeouts
```

### Memory Issues
```bash
# Enable garbage collection logs
node --expose-gc --trace-gc npm run test
```

### Performance Degradation
```bash
# Profile CPU usage
node --prof npm run load:heavy
node --prof-process isolate-*.log > profile.txt
```

## 🔮 Roadmap

- [ ] **Real Exchange Integration**: Testes com exchanges reais
- [ ] **Network Simulation**: Latência e packet loss
- [ ] **Database Load**: Stress testing do PostgreSQL
- [ ] **Redis Performance**: Cache invalidation scenarios
- [ ] **Chaos Engineering**: Random failures injection
- [ ] **Geographic Distribution**: Multi-region testing
- [ ] **Container Limits**: Resource constraint testing
# CHECKLIST DE IMPLEMENTACAO: WEBHOOK SECURITY FIXES

**Data de Inicio:** ___/___/_____
**Responsavel:** _______________________
**Prazo:** 1 semana (7 dias uteis)

---

## PRE-REQUISITOS

### Infraestrutura
- [ ] Redis instalado e configurado
  - [ ] Localmente (desenvolvimento): `brew install redis` ou `apt-get install redis`
  - [ ] Producao: AWS ElastiCache Redis (cache.t3.micro)
  - [ ] Testar conexao: `redis-cli ping` → Resposta: `PONG`

- [ ] AWS Secrets Manager (ou alternativa)
  - [ ] Conta AWS configurada
  - [ ] IAM role com permissoes: `secretsmanager:GetSecretValue`, `secretsmanager:PutSecretValue`
  - [ ] Secrets criados: `binance/api/production`, `binance/api/staging`

- [ ] Dependencias Python
  ```bash
  pip install redis[asyncio]==5.0.0
  pip install circuitbreaker==1.4.0
  pip install pydantic==2.5.0
  pip install boto3==1.29.0  # Para AWS Secrets Manager
  ```

- [ ] Variaveis de ambiente atualizadas
  ```bash
  REDIS_URL=redis://localhost:6379
  AWS_REGION=us-east-1
  ENCRYPTION_MASTER_KEY=<sua-chave-gerada>
  ENV=development  # ou production
  ```

---

## DIA 1-2: RATE LIMITING + REPLAY PREVENTION (16h)

### FIX CRITICA-01: Rate Limiting Real

#### Implementacao (4h)
- [ ] Copiar classe `RedisRateLimiter` de `WEBHOOK_SECURITY_FIXES_EXAMPLES.py`
- [ ] Criar arquivo: `/apps/api-python/infrastructure/security/rate_limiter.py`
- [ ] Substituir funcao mock em `tradingview_webhook_service.py:271-275`
  ```python
  async def _check_rate_limiting(self, webhook_id: UUID) -> bool:
      rate_limiter = RedisRateLimiter()
      return await rate_limiter.check_rate_limit(
          webhook_id,
          rate_limit_per_minute=60,
          rate_limit_per_hour=1000
      )
  ```

#### Testes (2h)
- [ ] Teste unitario: `test_rate_limiting_allows_within_limits()`
- [ ] Teste unitario: `test_rate_limiting_blocks_exceeded()`
- [ ] Teste de integracao: Enviar 100 webhooks em 1 segundo
- [ ] Teste de integracao: Enviar 1000 webhooks em 1 minuto
- [ ] Verificar logs: "Rate limit exceeded" aparece corretamente

#### Validacao (1h)
- [ ] Redis keys criados corretamente: `webhook:<id>:minute:*`, `webhook:<id>:hour:*`
- [ ] TTL configurado: 60s (minute), 3600s (hour)
- [ ] Metrics: `rate_limit_exceeded_total` (se Prometheus configurado)

#### Rollback Plan (1h)
- [ ] Documentar como desabilitar temporariamente (return True)
- [ ] Configurar feature flag: `ENABLE_RATE_LIMITING=true/false`

---

### FIX CRITICA-02: Replay Attack Prevention

#### Implementacao (4h)
- [ ] Copiar classe `ReplayAttackPrevention` de `WEBHOOK_SECURITY_FIXES_EXAMPLES.py`
- [ ] Criar arquivo: `/apps/api-python/infrastructure/security/replay_prevention.py`
- [ ] Integrar em `_enhanced_hmac_validation()` (linha 200-217)
  ```python
  # NEW: Check replay attack
  replay_prevention = ReplayAttackPrevention()
  if not await replay_prevention.check_replay_attack(webhook_id, payload, timestamp):
      logger.warning("Replay attack detected", webhook_id=str(webhook_id))
      return False
  ```

#### Testes (2h)
- [ ] Teste unitario: `test_replay_prevention_allows_first_request()`
- [ ] Teste unitario: `test_replay_prevention_blocks_duplicate()`
- [ ] Teste de integracao: Enviar mesmo webhook 2x
- [ ] Teste de integracao: Enviar webhook apos 6 minutos (deve permitir)

#### Validacao (1h)
- [ ] Nonce keys criados: `webhook:nonce:<sha256>`
- [ ] TTL configurado: 360s (6 minutos)
- [ ] Security logs: "Replay attack detected" funciona

#### Rollback Plan (1h)
- [ ] Feature flag: `ENABLE_REPLAY_PREVENTION=true/false`
- [ ] Documentar impacto: Sem replay prevention, webhooks podem ser duplicados

---

## DIA 3-4: PAYLOAD VALIDATION + RACE CONDITIONS (14h)

### FIX CRITICA-03: Validacao de Payload com Pydantic

#### Implementacao (3h)
- [ ] Copiar classe `TradingViewWebhookPayload` de examples
- [ ] Criar arquivo: `/apps/api-python/presentation/schemas/tradingview_validated.py`
- [ ] Substituir validacao atual em `order_processor.py:103-130`
- [ ] Atualizar `_validate_tradingview_payload()` para usar Pydantic

#### Testes (2h)
- [ ] Teste: Valid payload (BTCUSDT, buy, 0.001) → ACEITO
- [ ] Teste: Invalid ticker (INVALID) → REJEITADO
- [ ] Teste: Invalid action (hack) → REJEITADO
- [ ] Teste: Negative quantity (-1) → REJEITADO
- [ ] Teste: Excessive quantity (999999999) → REJEITADO
- [ ] Teste: Extra fields ({"hack": "attempt"}) → REJEITADO

#### Validacao (1h)
- [ ] Todos payloads maliciosos rejeitados
- [ ] Logs: ValidationError com detalhes
- [ ] Error message sanitizado para external API

---

### FIX CRITICA-04: Distributed Locking

#### Implementacao (4h)
- [ ] Copiar funcao `distributed_lock()` de examples
- [ ] Criar arquivo: `/apps/api-python/infrastructure/security/distributed_lock.py`
- [ ] Integrar em `_execute_trading_order()` (linha 442-474)
  ```python
  lock_key = f"order:lock:{user_id}:{account.id}:{signal.ticker}:{signal.action}"
  async with distributed_lock(lock_key, timeout=10):
      # Execute order inside lock
      result = await self._create_order(account, user_id, signal)
  ```

#### Testes (2h)
- [ ] Teste: 2 webhooks identicos simultaneos → Apenas 1 ordem criada
- [ ] Teste: Lock timeout (10s) → Erro apropriado
- [ ] Teste: Lock release apos ordem criada
- [ ] Teste de stress: 10 webhooks simultaneos com simbolos diferentes

#### Validacao (2h)
- [ ] Redis locks criados: `order:lock:*`
- [ ] Timeout funcionando (10s)
- [ ] Lock released corretamente
- [ ] Sem deadlocks

---

## DIA 5-6: CIRCUIT BREAKER + SECRETS MANAGER (18h)

### FIX CRITICA-05: Circuit Breaker

#### Implementacao (4h)
- [ ] Instalar: `pip install circuitbreaker==1.4.0`
- [ ] Copiar classe `ExchangeCircuitBreaker` de examples
- [ ] Criar arquivo: `/apps/api-python/infrastructure/resilience/circuit_breaker.py`
- [ ] Integrar em `secure_exchange_service.py:create_order()` (linha 214-291)

#### Testes (3h)
- [ ] Teste: 5 falhas consecutivas → Circuit breaker OPEN
- [ ] Teste: Apos 60s → Circuit breaker HALF-OPEN
- [ ] Teste: 1 sucesso → Circuit breaker CLOSED
- [ ] Teste: Durante OPEN → Erro imediato (sem chamar API)

#### Validacao (2h)
- [ ] Circuit breaker states: CLOSED → OPEN → HALF_OPEN → CLOSED
- [ ] Logs: "Circuit breaker OPEN - Exchange API unavailable"
- [ ] Metrics: `circuit_breaker_state{exchange="binance"}` (se Prometheus)

---

### FIX CRITICA-06: Secrets Manager

#### Implementacao (6h)
- [ ] Instalar: `pip install boto3==1.29.0`
- [ ] Copiar classe `SecretsManager` de examples
- [ ] Criar arquivo: `/apps/api-python/infrastructure/security/secrets_manager.py`
- [ ] Criar secrets no AWS:
  ```bash
  aws secretsmanager create-secret \
      --name binance/api/production \
      --secret-string '{"api_key":"xxx","api_secret":"yyy"}'
  ```
- [ ] Atualizar `BinanceConnector.__init__()` para usar Secrets Manager
- [ ] Remover API keys do `.env` (manter apenas em staging/dev)

#### Testes (2h)
- [ ] Teste: Load secret from AWS → Success
- [ ] Teste: Cache working (5 minutes)
- [ ] Teste: Rotate secret → Old keys invalidated
- [ ] Teste: Fallback to .env in development mode

#### Validacao (1h)
- [ ] Secrets no AWS configurados
- [ ] Secrets nao mais em `.env` (producao)
- [ ] Cache funcionando (check CloudWatch metrics)
- [ ] Rotacao documentada

---

## DIA 7: ERROR SANITIZATION (4h)

### FIX CRITICA-07: Sanitizacao de Erros

#### Implementacao (2h)
- [ ] Copiar funcoes `sanitize_error_message()` e `sanitize_for_logging()` de examples
- [ ] Criar arquivo: `/apps/api-python/infrastructure/security/error_sanitization.py`
- [ ] Atualizar `tradingview_webhook_controller.py:116-128`
- [ ] Atualizar todos `logger.info/error/warning` para usar `sanitize_for_logging()`

#### Testes (1h)
- [ ] Teste: Internal error → Generic message
- [ ] Teste: Binance error → Sanitized message
- [ ] Teste: PII in logs → Hashed
- [ ] Teste: Stack trace → Not exposed

#### Validacao (1h)
- [ ] Auditar todos logs: grep "client_ip" → Deve estar hashed
- [ ] Auditar erros externos: Nao expor stack traces
- [ ] Compliance GDPR: PII removido de logs

---

## POS-IMPLEMENTACAO

### Testes de Integracao (4h)
- [ ] Teste end-to-end: TradingView → Backend → Binance
- [ ] Teste de carga: 100 webhooks/minuto por 10 minutos
- [ ] Teste de resiliencia: Desligar Redis → Sistema rejeita gracefully
- [ ] Teste de resiliencia: Binance API down → Circuit breaker ativa

### Monitoramento (2h)
- [ ] Health check: `/health/detailed` retorna status de todos componentes
- [ ] Metrics exportadas: rate_limit, replay_attacks, circuit_breaker_state
- [ ] Alertas configurados: Rate limit exceeded, Circuit breaker open
- [ ] Dashboards: Grafana com metricas de seguranca

### Documentacao (2h)
- [ ] Atualizar README.md com novos requisitos (Redis)
- [ ] Documentar configuracao de AWS Secrets Manager
- [ ] Criar runbook: Como responder a replay attacks
- [ ] Criar runbook: Como rotacionar API keys

### Deploy (2h)
- [ ] Criar branch: `security/critical-fixes`
- [ ] Code review com security checklist
- [ ] Merge para `main` apos aprovacao
- [ ] Deploy em staging
- [ ] Testes de smoke em staging
- [ ] Deploy em producao
- [ ] Monitoring pos-deploy (24h)

---

## METRICAS DE SUCESSO

### Antes da Implementacao
- [ ] Vulnerabilidades CRITICAS: 7
- [ ] Rate limiting: NAO FUNCIONA
- [ ] Replay prevention: NAO FUNCIONA
- [ ] Circuit breaker: NAO EXISTE
- [ ] Secrets: Em .env (INSEGURO)

### Apos Implementacao
- [ ] Vulnerabilidades CRITICAS: 0
- [ ] Rate limiting: FUNCIONA (60/min, 1000/hora)
- [ ] Replay prevention: FUNCIONA (nonce tracking)
- [ ] Circuit breaker: FUNCIONA (5 failures → open)
- [ ] Secrets: AWS Secrets Manager (SEGURO)

### Validacao Final
- [ ] Security scan: `bandit -r apps/api-python/` → Nenhum HIGH/CRITICAL
- [ ] Dependency check: `pip-audit` → Nenhuma vulnerabilidade
- [ ] Load test: 100 req/min por 10min → Sem crashes
- [ ] Pentest basico: Tentar replay, rate limit bypass → BLOQUEADO

---

## ROLLBACK PLAN

### Se algo der errado:

1. **Rate Limiting causando false positives:**
   ```python
   # Temporariamente, desabilitar:
   ENABLE_RATE_LIMITING=false
   ```

2. **Replay prevention bloqueando webhooks validos:**
   ```python
   # Aumentar TTL de nonce:
   self.nonce_ttl = 600  # 10 minutos
   ```

3. **Circuit breaker muito sensivel:**
   ```python
   # Aumentar threshold:
   self.failure_threshold = 10  # 10 failures ao inves de 5
   ```

4. **AWS Secrets Manager indisponivel:**
   ```python
   # Fallback para .env:
   use_secrets_manager = False
   ```

5. **Redis indisponivel:**
   ```python
   # Sistema deve FAIL SECURE (rejeitar requests)
   # Mas se necessario emergencia:
   BYPASS_SECURITY_CHECKS=true  # APENAS EMERGENCIA
   ```

---

## CONTATOS DE EMERGENCIA

**Backend Lead:** _______________________
**Security Team:** _______________________
**DevOps On-Call:** _______________________
**PagerDuty:** https://...

---

## NOTAS IMPORTANTES

1. **NAO PULAR ETAPAS** - Cada fix depende do anterior
2. **TESTAR EM STAGING** antes de producao
3. **BACKUP DO BANCO** antes de qualquer deploy
4. **MONITORING 24/7** durante primeira semana
5. **COMUNICAR TIME** sobre mudancas de seguranca

---

## ASSINATURAS

**Implementado por:** _______________________ Data: ___/___/_____

**Revisado por (Security):** _______________________ Data: ___/___/_____

**Aprovado por (CTO/Lead):** _______________________ Data: ___/___/_____

---

*Checklist baseado em auditoria de seguranca realizada em 09/10/2025*

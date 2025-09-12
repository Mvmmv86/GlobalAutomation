# Secrets Configuration

## GitHub Actions Secrets

Configure these secrets in your GitHub repository settings (Settings → Secrets and variables → Actions):

### Required Secrets

```bash
# Database
POSTGRES_PASSWORD=dev_password_123

# Security & Authentication  
TV_WEBHOOK_SECRET=6d7d138b668d612911d0154de75cd5be115b69b6dbcd408282a0987edfe554be
MASTER_KEY=3acff36f6c23187c112d5827d59d2a462d3e40bedd148ec06d260572d6fa98cc
JWT_SECRET=6eee2260098a97fa87a7d3ee0c50c610058c4047e92a36fe9a503ff23b3c2ca6
NEXTAUTH_SECRET=4851cf48a55058e11723bdf26c93d9810fc5e800a52972e1

# Exchange API Keys (Production)
BINANCE_API_KEY=your_production_binance_api_key
BINANCE_SECRET_KEY=your_production_binance_secret_key

BYBIT_API_KEY=your_production_bybit_api_key  
BYBIT_SECRET_KEY=your_production_bybit_secret_key
BYBIT_PASSPHRASE=your_production_bybit_passphrase

# Optional
SENTRY_DSN=your_sentry_dsn_for_error_tracking
```

## Local Development

1. Copy `.env.example` to `.env`
2. Replace placeholder values with actual secrets
3. **NEVER commit `.env` to Git**

## Production Deployment

For production environments, use:
- **BINANCE_TESTNET=false**
- **BYBIT_TESTNET=false**
- Strong passwords for database
- Valid Sentry DSN for monitoring

## Security Notes

- All secrets are 32+ character cryptographically secure random strings
- API keys should have minimal required permissions
- Use separate API keys for testnet vs mainnet
- Rotate secrets regularly (quarterly recommended)

## Emergency Procedures

If secrets are compromised:
1. Immediately revoke API keys on exchanges
2. Generate new secrets using: `openssl rand -hex 32`
3. Update GitHub secrets
4. Redeploy all services

---
**⚠️ DELETE THIS FILE AFTER CONFIGURING SECRETS ⚠️**
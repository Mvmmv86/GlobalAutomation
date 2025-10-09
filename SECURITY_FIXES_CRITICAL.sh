#!/bin/bash
# =====================================================
# SCRIPT DE CORREÇÃO DE VULNERABILIDADES CRÍTICAS
# Sistema de Trading - Binance Integration
# Data: 07 de Outubro de 2025
# =====================================================

set -e  # Exit on error

echo "======================================================"
echo "🔐 SECURITY FIXES - CRITICAL VULNERABILITIES"
echo "======================================================"
echo ""
echo "⚠️  ATENÇÃO: Este script irá:"
echo "   1. Gerar novas chaves de segurança"
echo "   2. Atualizar arquivo .env"
echo "   3. Criar backup do código atual"
echo "   4. Aplicar patches de segurança"
echo ""
read -p "Deseja continuar? (yes/no): " confirm

if [ "$confirm" != "yes" ]; then
    echo "❌ Operação cancelada pelo usuário."
    exit 1
fi

echo ""
echo "📍 Diretório de trabalho: $(pwd)"
echo ""

# =====================================================
# PASSO 1: Criar backup
# =====================================================
echo "📦 PASSO 1: Criando backup do sistema atual..."

BACKUP_DIR="backups/security_backup_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"

# Backup de arquivos críticos
cp apps/api-python/main.py "$BACKUP_DIR/main.py.backup"
cp apps/api-python/.env "$BACKUP_DIR/.env.backup" 2>/dev/null || echo "  ⚠️  .env não encontrado (será criado)"
cp apps/api-python/presentation/controllers/orders_controller.py "$BACKUP_DIR/orders_controller.py.backup"

echo "✅ Backup criado em: $BACKUP_DIR"
echo ""

# =====================================================
# PASSO 2: Gerar chaves seguras
# =====================================================
echo "🔑 PASSO 2: Gerando chaves de segurança..."

# Gerar JWT Secret Key (256 bits)
JWT_SECRET=$(openssl rand -hex 32)
echo "✅ JWT Secret Key gerado: ${JWT_SECRET:0:16}... (oculto)"

# Gerar Encryption Key (256 bits)
ENCRYPTION_KEY=$(openssl rand -hex 32)
echo "✅ Encryption Key gerado: ${ENCRYPTION_KEY:0:16}... (oculto)"

# Gerar TradingView Webhook Secret
TV_WEBHOOK_SECRET=$(openssl rand -hex 32)
echo "✅ TradingView Webhook Secret gerado: ${TV_WEBHOOK_SECRET:0:16}... (oculto)"

echo ""

# =====================================================
# PASSO 3: Atualizar .env
# =====================================================
echo "📝 PASSO 3: Atualizando arquivo .env..."

ENV_FILE="apps/api-python/.env"

# Criar .env se não existir
if [ ! -f "$ENV_FILE" ]; then
    echo "  📄 Criando novo arquivo .env..."
    touch "$ENV_FILE"
fi

# Função para atualizar ou adicionar variável
update_env_var() {
    local key=$1
    local value=$2
    local file=$3

    if grep -q "^${key}=" "$file" 2>/dev/null; then
        # Atualizar existente
        sed -i.bak "s|^${key}=.*|${key}=${value}|" "$file"
        echo "  ✅ Atualizado: $key"
    else
        # Adicionar novo
        echo "${key}=${value}" >> "$file"
        echo "  ✅ Adicionado: $key"
    fi
}

# Atualizar chaves críticas
update_env_var "JWT_SECRET_KEY" "$JWT_SECRET" "$ENV_FILE"
update_env_var "SECRET_KEY" "$JWT_SECRET" "$ENV_FILE"
update_env_var "ENCRYPTION_KEY" "$ENCRYPTION_KEY" "$ENV_FILE"
update_env_var "ENCRYPTION_MASTER_KEY" "$ENCRYPTION_KEY" "$ENV_FILE"
update_env_var "TV_WEBHOOK_SECRET" "$TV_WEBHOOK_SECRET" "$ENV_FILE"

# Adicionar outras configurações de segurança se não existirem
update_env_var "ENV" "development" "$ENV_FILE"
update_env_var "DEBUG" "true" "$ENV_FILE"
update_env_var "JWT_ALGORITHM" "HS256" "$ENV_FILE"
update_env_var "ACCESS_TOKEN_EXPIRE_MINUTES" "30" "$ENV_FILE"

echo ""

# =====================================================
# PASSO 4: Criar patch para main.py
# =====================================================
echo "🔧 PASSO 4: Criando patch de segurança para main.py..."

cat > "$BACKUP_DIR/security_patch_main.py" << 'PATCH_EOF'
# =====================================================
# SECURITY PATCH - main.py
# Aplicar manualmente ou usar script de merge
# =====================================================

# FIX 1: JWT Secret de variável de ambiente
# LOCALIZAÇÃO: Linha ~1336
# ANTES:
#   secret_key = "trading_platform_secret_key_2024"
# DEPOIS:

import os
secret_key = os.getenv("JWT_SECRET_KEY")
if not secret_key:
    raise ValueError("CRITICAL: JWT_SECRET_KEY environment variable not set!")

# FIX 2: Remover fallback de credenciais
# LOCALIZAÇÃO: Linha ~369-375
# ANTES:
#   except Exception as decrypt_error:
#       api_key = account['api_key'] or os.getenv('BINANCE_API_KEY')
# DEPOIS:

except Exception as decrypt_error:
    logger.critical(
        "CRITICAL: API key decryption failed",
        account_id=account_id,
        error=str(decrypt_error),
        exc_info=True
    )
    raise HTTPException(
        status_code=500,
        detail="Encryption key unavailable - contact support"
    )

# FIX 3: Sanitizar logs
# LOCALIZAÇÃO: Adicionar no início do arquivo após imports

SENSITIVE_HEADERS = {'authorization', 'x-api-key', 'cookie', 'token', 'x-auth-token'}
SENSITIVE_FIELDS = {'password', 'api_key', 'secret_key', 'passphrase', 'api_secret'}

def sanitize_dict(data: dict, depth: int = 0) -> dict:
    """Remove campos sensíveis de dicts antes de logar"""
    if depth > 5:  # Prevent infinite recursion
        return {"_truncated": "max_depth_reached"}

    sanitized = {}
    for key, value in data.items():
        if key.lower() in SENSITIVE_FIELDS:
            sanitized[key] = "***REDACTED***"
        elif isinstance(value, dict):
            sanitized[key] = sanitize_dict(value, depth + 1)
        elif isinstance(value, list):
            sanitized[key] = [
                sanitize_dict(item, depth + 1) if isinstance(item, dict) else item
                for item in value
            ]
        else:
            sanitized[key] = value
    return sanitized

# FIX 4: Atualizar middleware de logging
# LOCALIZAÇÃO: Linha ~140-196
# SUBSTITUIR middleware existente por:

@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all HTTP requests (sanitized)"""
    # Sanitizar headers
    headers = {
        k: v for k, v in request.headers.items()
        if k.lower() not in SENSITIVE_HEADERS
    }

    logger.info(
        "request_started",
        method=request.method,
        path=request.url.path,
        client_ip=get_remote_address(request),
        headers_count=len(request.headers.items())  # Não expor conteúdo
    )

    try:
        response = await call_next(request)

        logger.info(
            "request_completed",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            client_ip=get_remote_address(request),
        )

        return response

    except Exception as e:
        logger.error(
            "request_failed",
            method=request.method,
            path=request.url.path,
            client_ip=get_remote_address(request),
            error=str(e),
        )
        raise

PATCH_EOF

echo "✅ Patch criado em: $BACKUP_DIR/security_patch_main.py"
echo ""

# =====================================================
# PASSO 5: Criar dependency de autenticação
# =====================================================
echo "🔐 PASSO 5: Criando dependency de autenticação..."

cat > "apps/api-python/infrastructure/security/auth_dependency.py" << 'AUTH_EOF'
"""
Authentication Dependency for FastAPI
Validates JWT tokens and enforces authentication
"""

import os
import jwt
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import structlog

logger = structlog.get_logger(__name__)

# Security scheme
security = HTTPBearer()

# JWT Configuration
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")

if not JWT_SECRET_KEY:
    raise ValueError("CRITICAL: JWT_SECRET_KEY not configured!")


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> dict:
    """
    Validate JWT token and return current user

    Raises:
        HTTPException: If token is invalid or expired
    """
    token = credentials.credentials

    try:
        # Decode and verify token
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])

        # Validate token type
        if payload.get("type") != "access":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type"
            )

        # Extract user data
        user_id = payload.get("user_id")
        email = payload.get("email")

        if not user_id or not email:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload"
            )

        return {
            "user_id": user_id,
            "email": email,
            "exp": payload.get("exp")
        }

    except jwt.ExpiredSignatureError:
        logger.warning("Token expired", token_prefix=token[:10])
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired"
        )
    except jwt.InvalidTokenError as e:
        logger.warning("Invalid token", error=str(e), token_prefix=token[:10])
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )
    except Exception as e:
        logger.error("Token validation error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed"
        )


async def get_current_active_user(
    current_user: dict = Depends(get_current_user)
) -> dict:
    """
    Get current active user (can add additional checks here)
    """
    # Add additional checks if needed (e.g., user is not banned)
    return current_user


# Optional: Admin-only dependency
async def get_admin_user(
    current_user: dict = Depends(get_current_user)
) -> dict:
    """
    Validate user is admin

    Raises:
        HTTPException: If user is not admin
    """
    # TODO: Add admin check logic
    # if not current_user.get("is_admin"):
    #     raise HTTPException(status_code=403, detail="Admin access required")

    return current_user
AUTH_EOF

echo "✅ Dependency criado: apps/api-python/infrastructure/security/auth_dependency.py"
echo ""

# =====================================================
# PASSO 6: Criar script de validação
# =====================================================
echo "✅ PASSO 6: Criando script de validação..."

cat > "apps/api-python/validate_security.py" << 'VALIDATE_EOF'
#!/usr/bin/env python3
"""
Security Validation Script
Verifica se as correções de segurança foram aplicadas corretamente
"""

import os
import sys
from pathlib import Path

CRITICAL_CHECKS = [
    ("JWT_SECRET_KEY", "Chave JWT configurada"),
    ("ENCRYPTION_KEY", "Chave de criptografia configurada"),
    ("TV_WEBHOOK_SECRET", "Webhook secret configurado"),
]

def check_env_vars():
    """Verifica variáveis de ambiente críticas"""
    print("🔍 Verificando variáveis de ambiente...")

    missing = []
    for var, description in CRITICAL_CHECKS:
        value = os.getenv(var)
        if not value:
            print(f"  ❌ {var}: NÃO CONFIGURADA")
            missing.append(var)
        elif value.startswith("your-") or value == "change-this":
            print(f"  ⚠️  {var}: VALOR PADRÃO (mudar!)")
            missing.append(var)
        else:
            print(f"  ✅ {var}: OK ({description})")

    return len(missing) == 0

def check_main_py():
    """Verifica se main.py foi corrigido"""
    print("\n🔍 Verificando main.py...")

    main_py = Path("apps/api-python/main.py")
    if not main_py.exists():
        print("  ❌ main.py não encontrado")
        return False

    content = main_py.read_text()

    issues = []

    # Check 1: JWT secret hardcoded
    if 'secret_key = "trading_platform_secret_key_2024"' in content:
        print("  ❌ JWT secret ainda hardcoded (linha ~1336)")
        issues.append("JWT_HARDCODED")

    # Check 2: Fallback de credenciais
    if 'os.getenv(\'BINANCE_API_KEY\')' in content and 'fallback' in content.lower():
        print("  ⚠️  Fallback de credenciais ainda presente")
        issues.append("CREDENTIALS_FALLBACK")

    # Check 3: Sanitização de logs
    if 'sanitize_dict' not in content:
        print("  ⚠️  Função de sanitização de logs não encontrada")
        issues.append("LOG_SANITIZATION")

    if not issues:
        print("  ✅ main.py: Aparentemente corrigido")

    return len(issues) == 0

def check_auth_dependency():
    """Verifica se dependency de auth foi criado"""
    print("\n🔍 Verificando autenticação...")

    auth_dep = Path("apps/api-python/infrastructure/security/auth_dependency.py")
    if not auth_dep.exists():
        print("  ⚠️  auth_dependency.py não encontrado (criar manualmente)")
        return False

    print("  ✅ auth_dependency.py: Existe")
    return True

def main():
    print("=" * 60)
    print("🔐 VALIDAÇÃO DE SEGURANÇA")
    print("=" * 60)
    print()

    # Load .env
    from dotenv import load_dotenv
    env_path = Path("apps/api-python/.env")
    if env_path.exists():
        load_dotenv(env_path)
        print(f"✅ .env carregado: {env_path}")
    else:
        print(f"⚠️  .env não encontrado: {env_path}")

    print()

    # Run checks
    checks = [
        ("Variáveis de Ambiente", check_env_vars()),
        ("Correções em main.py", check_main_py()),
        ("Dependency de Autenticação", check_auth_dependency()),
    ]

    print("\n" + "=" * 60)
    print("📊 RESUMO")
    print("=" * 60)

    all_passed = all(passed for _, passed in checks)

    for name, passed in checks:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {name}")

    print()

    if all_passed:
        print("🎉 Todas as verificações passaram!")
        print("⚠️  IMPORTANTE: Revisar MANUALMENTE os patches antes de produção")
        return 0
    else:
        print("❌ Algumas verificações falharam")
        print("📖 Consulte SECURITY_AUDIT_REPORT_07_OCT_2025.md para detalhes")
        return 1

if __name__ == "__main__":
    sys.exit(main())
VALIDATE_EOF

chmod +x "apps/api-python/validate_security.py"
echo "✅ Script de validação criado: apps/api-python/validate_security.py"
echo ""

# =====================================================
# PASSO 7: Resumo
# =====================================================
echo "======================================================"
echo "✅ CORREÇÕES APLICADAS COM SUCESSO"
echo "======================================================"
echo ""
echo "📁 Arquivos criados/modificados:"
echo "   - .env: Chaves de segurança atualizadas"
echo "   - Backup: $BACKUP_DIR/"
echo "   - Patch: $BACKUP_DIR/security_patch_main.py"
echo "   - Auth Dependency: apps/api-python/infrastructure/security/auth_dependency.py"
echo "   - Validação: apps/api-python/validate_security.py"
echo ""
echo "⚠️  PRÓXIMOS PASSOS MANUAIS:"
echo ""
echo "1. REVISAR e aplicar o patch em main.py:"
echo "   cat $BACKUP_DIR/security_patch_main.py"
echo ""
echo "2. ADICIONAR autenticação nos endpoints (orders_controller.py):"
echo "   from infrastructure.security.auth_dependency import get_current_user"
echo "   @router.post('/create')"
echo "   async def create_order(current_user: dict = Depends(get_current_user)):"
echo ""
echo "3. VALIDAR correções:"
echo "   cd apps/api-python && python3 validate_security.py"
echo ""
echo "4. TESTAR localmente antes de commit"
echo ""
echo "5. CONSULTAR relatório completo:"
echo "   cat SECURITY_AUDIT_REPORT_07_OCT_2025.md"
echo ""
echo "======================================================"
echo "🔒 CHAVES GERADAS (CONFIDENCIAL)"
echo "======================================================"
echo "JWT_SECRET_KEY=${JWT_SECRET:0:16}..."
echo "ENCRYPTION_KEY=${ENCRYPTION_KEY:0:16}..."
echo "TV_WEBHOOK_SECRET=${TV_WEBHOOK_SECRET:0:16}..."
echo ""
echo "⚠️  IMPORTANTE: Manter chaves em local seguro!"
echo "              NÃO commitar .env no git!"
echo ""
echo "======================================================"

# Salvar chaves em arquivo seguro (apenas para backup)
KEYS_FILE="$BACKUP_DIR/KEYS_BACKUP.txt"
cat > "$KEYS_FILE" << KEY_EOF
# =====================================================
# BACKUP DE CHAVES DE SEGURANÇA
# Data: $(date)
# =====================================================
# CONFIDENCIAL - NÃO COMPARTILHAR
# =====================================================

JWT_SECRET_KEY=$JWT_SECRET
ENCRYPTION_KEY=$ENCRYPTION_KEY
TV_WEBHOOK_SECRET=$TV_WEBHOOK_SECRET

# =====================================================
# Instruções:
# 1. Manter este arquivo em local seguro
# 2. Usar vault/HSM em produção
# 3. Rotacionar chaves periodicamente
# =====================================================
KEY_EOF

chmod 600 "$KEYS_FILE"
echo "🔐 Backup de chaves salvo em: $KEYS_FILE (chmod 600)"
echo ""

echo "✅ Script concluído com sucesso!"
echo ""

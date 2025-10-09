#!/bin/bash
# Script de Limpeza do Repositório GlobalAutomation
# Data: 23/09/2025
# Objetivo: Remover APIs duplicadas, vestígios Docker e diretórios não usados

echo "========================================="
echo "🧹 LIMPEZA DO REPOSITÓRIO GLOBALAUTOMATION"
echo "========================================="
echo ""

# Verificar se está rodando como root/sudo
if [ "$EUID" -ne 0 ]; then
   echo "❌ Por favor, execute com sudo: sudo bash cleanup_repository.sh"
   exit 1
fi

# Diretório de backup
BACKUP_DIR="/home/globalauto/global/backups/cleanup_23sep"
echo "📁 Criando diretório de backup: $BACKUP_DIR"
mkdir -p $BACKUP_DIR

echo ""
echo "🔧 FASE 1: Removendo APIs duplicadas/antigas"
echo "---------------------------------------------"

# Mover services/trading (API duplicada que confunde - 228MB)
if [ -d "/home/globalauto/global/services" ]; then
    echo "  → Movendo services/ (API antiga da trading)..."
    mv /home/globalauto/global/services $BACKUP_DIR/
    echo "  ✅ services/ movido"
fi

# Mover apps/api (outra API que confunde)
if [ -d "/home/globalauto/global/apps/api" ]; then
    echo "  → Movendo apps/api/ (API antiga)..."
    mv /home/globalauto/global/apps/api $BACKUP_DIR/
    echo "  ✅ apps/api/ movido"
fi

# Mover apps não usados
for dir in web web-trading worker-exec worker-recon; do
    if [ -d "/home/globalauto/global/apps/$dir" ]; then
        echo "  → Movendo apps/$dir/ (não usado)..."
        mv /home/globalauto/global/apps/$dir $BACKUP_DIR/
        echo "  ✅ apps/$dir/ movido"
    fi
done

echo ""
echo "🐳 FASE 2: Removendo vestígios do Docker"
echo "---------------------------------------------"

# Remover Dockerfiles órfãos
find /home/globalauto/global -name "Dockerfile*" -not -path "*/backups/*" -not -path "*/node_modules/*" -not -path "*/.git/*" | while read file; do
    echo "  → Removendo: $file"
    mv "$file" $BACKUP_DIR/
done

# Remover docker-compose backup
if [ -f "/home/globalauto/global/docker-compose.backup.yml" ]; then
    echo "  → Movendo docker-compose.backup.yml..."
    mv /home/globalauto/global/docker-compose.backup.yml $BACKUP_DIR/
    echo "  ✅ docker-compose.backup.yml movido"
fi

# Remover .dockerignore se existir
if [ -f "/home/globalauto/global/.dockerignore" ]; then
    echo "  → Movendo .dockerignore..."
    mv /home/globalauto/global/.dockerignore $BACKUP_DIR/
    echo "  ✅ .dockerignore movido"
fi

echo ""
echo "🗂️ FASE 3: Removendo frontends antigos"
echo "---------------------------------------------"

# Mover frontend antigo (sem o -new)
if [ -d "/home/globalauto/global/frontend" ]; then
    echo "  → Movendo frontend/ (versão antiga)..."
    mv /home/globalauto/global/frontend $BACKUP_DIR/
    echo "  ✅ frontend/ movido"
fi

# Mover frontend-backup
if [ -d "/home/globalauto/global/frontend-backup" ]; then
    echo "  → Movendo frontend-backup/..."
    mv /home/globalauto/global/frontend-backup $BACKUP_DIR/
    echo "  ✅ frontend-backup/ movido"
fi

echo ""
echo "🧽 FASE 4: Limpando arquivos órfãos"
echo "---------------------------------------------"

# Mover shared/templates (não usado)
if [ -d "/home/globalauto/global/shared/templates" ]; then
    echo "  → Movendo shared/templates/..."
    mv /home/globalauto/global/shared/templates $BACKUP_DIR/
    echo "  ✅ shared/templates/ movido"
fi

# Mover shared/libs (não usado)
if [ -d "/home/globalauto/global/shared/libs" ]; then
    echo "  → Movendo shared/libs/..."
    mv /home/globalauto/global/shared/libs $BACKUP_DIR/
    echo "  ✅ shared/libs/ movido"
fi

# Remover Caddyfile (vestígio de infra antiga)
if [ -f "/home/globalauto/global/Caddyfile" ]; then
    echo "  → Movendo Caddyfile..."
    mv /home/globalauto/global/Caddyfile $BACKUP_DIR/
    echo "  ✅ Caddyfile movido"
fi

# Remover turbo.json (monorepo não configurado)
if [ -f "/home/globalauto/global/turbo.json" ]; then
    echo "  → Movendo turbo.json..."
    mv /home/globalauto/global/turbo.json $BACKUP_DIR/
    echo "  ✅ turbo.json movido"
fi

# Remover pnpm-workspace.yaml (não usado)
if [ -f "/home/globalauto/global/pnpm-workspace.yaml" ]; then
    echo "  → Movendo pnpm-workspace.yaml..."
    mv /home/globalauto/global/pnpm-workspace.yaml $BACKUP_DIR/
    echo "  ✅ pnpm-workspace.yaml movido"
fi

echo ""
echo "📊 FASE 5: Ajustando permissões"
echo "---------------------------------------------"
chown -R globalauto:globalauto /home/globalauto/global/backups/
echo "  ✅ Permissões ajustadas"

echo ""
echo "========================================="
echo "✅ LIMPEZA CONCLUÍDA COM SUCESSO!"
echo "========================================="
echo ""
echo "📋 RESUMO:"
echo "  • APIs duplicadas removidas"
echo "  • Vestígios Docker removidos"
echo "  • Frontends antigos removidos"
echo "  • Arquivos órfãos limpos"
echo ""
echo "📁 Backup salvo em: $BACKUP_DIR"
echo ""
echo "🏗️ ESTRUTURA LIMPA ATUAL:"
echo "  /apps/"
echo "    └── api-python/     ✅ (única API ativa)"
echo "  /frontend-new/        ✅ (único frontend ativo)"
echo "  /packages/shared/     ✅ (libs compartilhadas)"
echo ""
echo "⚠️ IMPORTANTE: Teste o sistema:"
echo "  1. Backend: curl http://localhost:8000/health"
echo "  2. Frontend: http://localhost:3000"
echo ""
#!/bin/bash
# ========================================
# SETUP SERVIDOR - GlobalAutomation
# ========================================
# Instala todas as dependências necessárias
# Sistema: Ubuntu 22.04 LTS
# RAM: 1GB (mínimo)
# Tempo estimado: 10-15 minutos

set -e  # Parar em caso de erro

echo "========================================="
echo "🚀 SETUP SERVIDOR - GlobalAutomation"
echo "========================================="
echo ""

# Verificar se está rodando como root
if [ "$EUID" -ne 0 ]; then
   echo "❌ Por favor, execute como root: sudo bash 02-SETUP-SERVER.sh"
   exit 1
fi

# Verificar memória disponível
TOTAL_RAM=$(free -m | awk '/^Mem:/{print $2}')
echo "💾 RAM Total: ${TOTAL_RAM}MB"
if [ "$TOTAL_RAM" -lt 900 ]; then
    echo "⚠️  AVISO: RAM baixa detectada. Recomendamos 2GB para melhor performance."
fi
echo ""

# ========================================
# FASE 1: Atualizar Sistema
# ========================================
echo "📦 FASE 1: Atualizando sistema..."
apt update
apt upgrade -y
echo "✅ Sistema atualizado"
echo ""

# ========================================
# FASE 2: Instalar Python 3.11
# ========================================
echo "🐍 FASE 2: Instalando Python 3.11..."

# Adicionar repositório deadsnakes
apt install -y software-properties-common
add-apt-repository -y ppa:deadsnakes/ppa
apt update

# Instalar Python 3.11
apt install -y python3.11 python3.11-venv python3.11-dev python3-pip
apt install -y build-essential libssl-dev libffi-dev

# Verificar versão
python3.11 --version
echo "✅ Python 3.11 instalado"
echo ""

# ========================================
# FASE 3: Instalar Node.js 18
# ========================================
echo "📗 FASE 3: Instalando Node.js 18..."

# Adicionar repositório NodeSource
curl -fsSL https://deb.nodesource.com/setup_18.x | bash -

# Instalar Node.js
apt install -y nodejs

# Verificar versões
node --version
npm --version
echo "✅ Node.js 18 instalado"
echo ""

# ========================================
# FASE 4: Instalar PM2 (Process Manager)
# ========================================
echo "⚙️  FASE 4: Instalando PM2..."

npm install -g pm2

# Configurar PM2 para iniciar no boot
pm2 startup systemd -u root --hp /root

echo "✅ PM2 instalado"
echo ""

# ========================================
# FASE 5: Instalar Nginx
# ========================================
echo "🌐 FASE 5: Instalando Nginx..."

apt install -y nginx

# Iniciar Nginx
systemctl start nginx
systemctl enable nginx

# Verificar status
systemctl status nginx --no-pager

echo "✅ Nginx instalado e rodando"
echo ""

# ========================================
# FASE 6: Instalar Certbot (SSL - Opcional)
# ========================================
echo "🔒 FASE 6: Instalando Certbot (para SSL)..."

apt install -y certbot python3-certbot-nginx

echo "✅ Certbot instalado"
echo ""

# ========================================
# FASE 7: Configurar Firewall
# ========================================
echo "🔥 FASE 7: Configurando Firewall (UFW)..."

# Instalar UFW
apt install -y ufw

# Permitir SSH (IMPORTANTE!)
ufw allow 22/tcp
ufw allow OpenSSH

# Permitir HTTP/HTTPS
ufw allow 80/tcp
ufw allow 443/tcp

# Habilitar firewall (não bloquear SSH!)
yes | ufw enable

# Ver status
ufw status

echo "✅ Firewall configurado"
echo ""

# ========================================
# FASE 8: Instalar Git
# ========================================
echo "📚 FASE 8: Instalando Git..."

apt install -y git

git --version
echo "✅ Git instalado"
echo ""

# ========================================
# FASE 9: Configurar Swap (para 1GB RAM)
# ========================================
echo "💿 FASE 9: Configurando Swap..."

# Verificar se já existe swap
if [ $(swapon --show | wc -l) -eq 0 ]; then
    echo "Criando arquivo de swap de 2GB..."

    # Criar arquivo swap
    fallocate -l 2G /swapfile
    chmod 600 /swapfile
    mkswap /swapfile
    swapon /swapfile

    # Tornar permanente
    echo '/swapfile none swap sw 0 0' >> /etc/fstab

    # Configurar swappiness (usar swap menos frequentemente)
    sysctl vm.swappiness=10
    echo 'vm.swappiness=10' >> /etc/sysctl.conf

    echo "✅ Swap criado e ativado (2GB)"
else
    echo "✅ Swap já existe"
fi

# Mostrar swap
free -h
echo ""

# ========================================
# FASE 10: Criar Estrutura de Diretórios
# ========================================
echo "📁 FASE 10: Criando estrutura de diretórios..."

mkdir -p /opt/trading-platform
mkdir -p /var/log/trading-platform

echo "✅ Diretórios criados"
echo ""

# ========================================
# FASE 11: Instalar Dependências do Sistema
# ========================================
echo "🔧 FASE 11: Instalando dependências adicionais..."

apt install -y curl wget unzip htop nano vim

echo "✅ Dependências instaladas"
echo ""

# ========================================
# RESUMO FINAL
# ========================================
echo "========================================="
echo "✅ SETUP COMPLETO!"
echo "========================================="
echo ""
echo "📋 RESUMO:"
echo "  ✅ Python 3.11:   $(python3.11 --version)"
echo "  ✅ Node.js:       $(node --version)"
echo "  ✅ npm:           $(npm --version)"
echo "  ✅ PM2:           $(pm2 --version)"
echo "  ✅ Nginx:         Rodando"
echo "  ✅ Git:           $(git --version)"
echo "  ✅ Firewall:      Ativo (22, 80, 443)"
echo "  ✅ Swap:          2GB configurado"
echo ""
echo "💾 Uso de RAM:"
free -h
echo ""
echo "🎯 PRÓXIMO PASSO:"
echo "   1. Clone o repositório:"
echo "      cd /opt/trading-platform"
echo "      git clone https://github.com/Mvmmv86/GlobalAutomation.git"
echo ""
echo "   2. Configure o .env:"
echo "      cd GlobalAutomation"
echo "      cp deploy/.env.production.example apps/api-python/.env"
echo "      nano apps/api-python/.env"
echo ""
echo "   3. Execute o deploy do backend:"
echo "      bash deploy/03-DEPLOY-BACKEND.sh"
echo ""
echo "========================================="

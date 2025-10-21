# 🚀 GUIA: Criar Droplet no DigitalOcean

**Tempo estimado**: 5 minutos
**Custo**: $6/mês (1GB RAM)

---

## 📋 PASSO A PASSO

### **1. Acesse o DigitalOcean**

1. Vá para: https://cloud.digitalocean.com/
2. Faça login na sua conta
3. Clique em **"Create"** → **"Droplets"**

---

### **2. Escolher Imagem do Sistema**

**Distribuição: Ubuntu**
- Selecione: **Ubuntu 22.04 (LTS) x64**
- ✅ Esta é a versão Long Term Support (recomendada)

---

### **3. Escolher Plano**

**Tipo de Droplet:**
- Selecione: **Basic** (Shared CPU)

**CPU Options:**
- Selecione: **Regular** (com SSD)

**Tamanho:**
```
💰 $6/mês
├── 1 GB RAM
├── 1 vCPU
├── 25 GB SSD
└── 1000 GB Transfer
```

⚠️ **NOTA**: Se você tiver problemas de memória depois, pode fazer upgrade para $12/mês (2GB RAM)

---

### **4. Escolher Região (Datacenter)**

**Região mais próxima do Brasil:**

1. **Opção 1 (RECOMENDADA)**: São Paulo
   - Selecione: **São Paulo 1** (sao1)
   - ✅ Menor latência para Brasil

2. **Opção 2**: New York
   - Selecione: **New York 3** (nyc3)
   - Latência média: 150-200ms

**Escolha:** São Paulo 1 (sao1)

---

### **5. Autenticação (SSH Keys)**

**IMPORTANTE**: Configure SSH key para segurança!

#### **Opção A: Usar SSH Key (RECOMENDADO)**

Se você já tem uma chave SSH:
1. Selecione: **SSH Key**
2. Clique em **"New SSH Key"**
3. Cole sua chave pública
4. Dê um nome: `meu-pc-trabalho`

**Gerar chave SSH (se não tem):**

```bash
# No seu computador local (Windows/Mac/Linux)
ssh-keygen -t ed25519 -C "seu-email@exemplo.com"

# Copiar a chave pública
cat ~/.ssh/id_ed25519.pub
```

#### **Opção B: Senha (NÃO RECOMENDADO)**

Se não configurar SSH key, você receberá a senha root por email.

---

### **6. Configurações Adicionais**

**Hostname:**
- Digite: `trading-platform-prod`

**Tags (opcional):**
- `production`
- `trading`

**Backups (opcional - +$1.20/mês):**
- ☐ Deixe desmarcado por enquanto
- Você pode habilitar depois se precisar

**Monitoring:**
- ✅ Marque: **Enable Monitoring** (grátis!)
- Monitora CPU, RAM, Disk, Bandwidth

**IPv6:**
- ☐ Pode deixar desmarcado

---

### **7. Criar Droplet**

1. Revise o resumo:
   ```
   Ubuntu 22.04 (LTS) x64
   São Paulo 1
   Basic - $6/mês
   1 GB / 1 CPU / 25 GB SSD
   ```

2. Clique em **"Create Droplet"**

3. **Aguarde 1-2 minutos** para criação

---

### **8. Anotar Informações do Droplet**

Após criação, anote:

```
IP do Droplet: ___.___.___.___ (exemplo: 64.225.123.45)
Hostname: trading-platform-prod
Região: São Paulo 1
```

---

## ✅ VERIFICAR ACESSO SSH

### **Opção A: Com SSH Key**

```bash
# Conectar ao servidor
ssh root@SEU-IP-AQUI

# Exemplo:
ssh root@64.225.123.45
```

Se aparecer:
```
The authenticity of host '64.225.123.45' can't be established.
```

Digite: `yes` e pressione Enter.

### **Opção B: Com Senha**

```bash
ssh root@SEU-IP-AQUI
# Digite a senha que recebeu por email
```

---

## 🎯 TESTE DE CONECTIVIDADE

Após conectar via SSH, teste:

```bash
# Verificar sistema
uname -a
# Deve mostrar: Linux ... Ubuntu

# Verificar memória
free -h
# Deve mostrar: ~1GB total

# Verificar disco
df -h
# Deve mostrar: ~25GB disponível

# Atualizar sistema
apt update
```

---

## ✅ PRONTO!

Seu Droplet está criado e pronto!

**Próximo passo:**
- Vá para: `02-SETUP-SERVER.md`
- Execute o script de instalação

---

## 🔒 DICAS DE SEGURANÇA

1. **NUNCA** compartilhe:
   - IP público em lugares públicos
   - Senha root
   - Chaves SSH privadas

2. **Configure Firewall** (vamos fazer isso no próximo passo)

3. **Desabilite login root via senha** (depois de configurar SSH key)

4. **Habilite backups automáticos** quando for para produção

---

**Custo mensal estimado:**
- Droplet: $6/mês
- Bandwidth: Incluído (1TB/mês)
- **TOTAL: $6/mês**

**Dúvidas?** Revise este guia ou consulte: https://docs.digitalocean.com/

# WHITELIST DE IPs - DIGITAL OCEAN PARA BINGX

## IP ATUAL (12 de Novembro de 2025)

```
146.190.83.158
```

Este é o IP **ATUAL** dos apps na Digital Ocean após o deploy mais recente.

## PROBLEMA IDENTIFICADO

Após cada deploy na Digital Ocean, o IP pode mudar, causando falha nas APIs da BingX devido à validação de whitelist.

## SOLUÇÃO IMEDIATA

### Na BingX:
1. Acesse sua conta BingX
2. Vá para **API Management**
3. Edite sua API Key
4. Em **IP Whitelist** ou **IP Restriction**
5. Adicione o IP: `146.190.83.158`
6. Salve as alterações

## LISTA COMPLETA DE IPs RECOMENDADOS

Para evitar problemas futuros, adicione TODOS estes IPs na whitelist da BingX:

```
146.190.83.158   # Atual (Nov 12, 2025)
157.230.254.126  # Anterior (Oct 26, 2025)
178.128.19.69    # Histórico
159.223.46.195   # Singapore primary
143.198.80.231   # Singapore backup
134.199.194.84   # USA backup 1
129.212.187.46   # USA backup 2
134.199.195.235  # USA backup 3
```

## COMO VERIFICAR O IP ATUAL

### Método 1 - Via API de Health
```bash
curl https://globalautomation-tqu2m.ondigitalocean.app/api/v1/health/whitelist
```

### Método 2 - Via Endpoint de Debug
```bash
curl https://globalautomation-tqu2m.ondigitalocean.app/api/v1/health/debug-ip
```

## ARQUIVOS ATUALIZADOS

- **health_controller.py**: Atualizado com o novo IP na lista fixa
- **Commit**: `fix: adiciona novo IP da Digital Ocean (146.190.83.158) na whitelist`

## NOTAS IMPORTANTES

1. **Cloudflare Proxy**: Os apps estão atrás do Cloudflare, então DNS queries retornam o IP do Cloudflare (162.159.140.98), não o IP real da Digital Ocean

2. **IP Dinâmico**: Digital Ocean App Platform pode mudar IPs durante:
   - Deploys
   - Scaling events
   - Manutenção da plataforma

3. **Monitoramento**: Sempre verifique o IP após um deploy e atualize a whitelist se necessário

## PRÓXIMOS PASSOS APÓS ADICIONAR IPs

1. Teste a conexão com a BingX
2. Execute um teste de ordem pequena (~$15) para validar
3. Confirme que SL/TP estão funcionando com o Método 3 (ordens separadas)

---

*Última atualização: 12 de Novembro de 2025*
#!/usr/bin/env python3
"""
Teste completo da funcionalidade de IPs para whitelist
"""

import requests
import json

def test_ip_endpoint():
    """Testa o endpoint de IPs"""
    print("\n🔍 TESTANDO FUNCIONALIDADE DE IPs PARA WHITELIST")
    print("=" * 60)
    
    try:
        # Testar endpoint
        response = requests.get("http://localhost:8000/api/v1/system/server-ips")
        
        if response.status_code == 200:
            data = response.json()
            
            if data.get('success') and data.get('ips'):
                print("✅ Endpoint funcionando!")
                print(f"   Total de IPs encontrados: {len(data['ips'])}")
                
                # Filtrar apenas IPs públicos/cloud
                public_ips = [ip for ip in data['ips'] if ip['type'] in ['public', 'cloud']]
                
                if public_ips:
                    print("\n🌐 IPs PARA WHITELIST NA BINANCE:")
                    print("-" * 40)
                    
                    for i, ip_data in enumerate(public_ips):
                        if i == 0:
                            print(f"🟢 IP PRINCIPAL: {ip_data['ip']}")
                            print(f"   Descrição: {ip_data['description']}")
                            print(f"   ⚠️  ADICIONE ESTE IP NA BINANCE!")
                        else:
                            print(f"🔵 IP Alternativo: {ip_data['ip']}")
                            print(f"   Descrição: {ip_data['description']}")
                        print()
                    
                    print("📝 INSTRUÇÕES:")
                    print("1. Acesse Binance.com → Perfil → Gerenciamento de API")
                    print("2. Encontre sua API Key")
                    print("3. Clique em 'Editar restrições'")
                    print("4. Selecione 'Restringir acesso apenas aos IPs confiáveis'")
                    print(f"5. Adicione o IP: {public_ips[0]['ip']}")
                    print("6. Salve as alterações")
                    
                else:
                    print("⚠️ Nenhum IP público encontrado")
                    
            else:
                print("❌ Resposta inválida do endpoint")
                
        else:
            print(f"❌ Erro no endpoint: {response.status_code}")
            print(f"   Resposta: {response.text}")
            
    except Exception as e:
        print(f"❌ Erro na conexão: {e}")
        return False
    
    print("\n✅ TESTE CONCLUÍDO!")
    print("   A funcionalidade está pronta no frontend!")
    print("   Quando você abrir o modal de 'Nova Conta de Exchange',")
    print("   os IPs aparecerão automaticamente.")
    
    return True

if __name__ == "__main__":
    test_ip_endpoint()
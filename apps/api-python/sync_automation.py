#!/usr/bin/env python3
"""
Script para sincronização automática a cada 30 segundos
Mantém os dados sempre atualizados
"""

import asyncio
import time
import subprocess
import json
from datetime import datetime

def sync_account(account_id: str):
    """Sincroniza uma conta específica usando curl"""
    try:
        # Usar curl para sincronizar
        result = subprocess.run([
            'curl', '-s', '-X', 'POST',
            f'http://localhost:8000/api/v1/sync/balances/{account_id}'
        ], capture_output=True, text=True, timeout=45)

        if result.returncode == 0:
            try:
                response_data = json.loads(result.stdout)
                if response_data.get('success'):
                    print(f"✅ Account {account_id}: Synced {response_data.get('synced_count', 0)} balances")
                else:
                    print(f"⚠️ Sync failed for account {account_id}: {response_data}")
            except json.JSONDecodeError:
                print(f"❌ Invalid JSON response for account {account_id}")
        else:
            print(f"❌ Curl error for account {account_id}: {result.stderr}")

    except Exception as e:
        print(f"❌ Error syncing account {account_id}: {e}")

def sync_all_accounts():
    """Sincroniza todas as contas"""
    # Lista de contas para sincronizar (pode ser dinamizada depois)
    accounts = [
        "0bad440b-f800-46ff-812f-5c359969885e",  # Conta principal
    ]

    print(f"🔄 {datetime.now().strftime('%H:%M:%S')} - Iniciando sincronização automática...")

    for account_id in accounts:
        sync_account(account_id)

    print(f"✅ {datetime.now().strftime('%H:%M:%S')} - Sincronização concluída")

def main():
    """Loop principal de sincronização"""
    print("🚀 Iniciando sincronização automática a cada 30 segundos...")
    print("📝 Para parar, pressione Ctrl+C")

    while True:
        try:
            sync_all_accounts()
            time.sleep(30)  # Aguarda 30 segundos
        except KeyboardInterrupt:
            print("\n⏹️ Parando sincronização automática...")
            break
        except Exception as e:
            print(f"❌ Erro no loop principal: {e}")
            time.sleep(10)  # Aguarda 10 segundos em caso de erro

if __name__ == "__main__":
    main()
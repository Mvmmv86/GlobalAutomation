#!/usr/bin/env python3
"""
Script para limpar contas mock/testnet e configurar para sempre usar conta real mainnet
"""

import asyncio
import sys
sys.path.append('.')

from infrastructure.database.connection import database_manager
from sqlalchemy import text
import structlog

logger = structlog.get_logger()

# ID da conta real (mainnet) do usuário
REAL_ACCOUNT_ID = "78e6b4fa-9a71-4360-b808-f1cd7c98dcbe"  # Teste1 Binance
USER_ID = "550e8400-e29b-41d4-a716-446655440001"

# IDs de contas para remover (testnet e outras contas que não são a principal)
ACCOUNTS_TO_REMOVE = [
    "7edce3b4-8ba2-4275-b136-7a8b6b6e93ba",  # tests (testnet)
    "1cfb9b63-bdd1-470d-9763-92f32635d2d8",  # Teste Frontend Fix (testnet)
    "0f505abb-0260-4b73-8580-a6332f2ec37b",  # Test API Keys (testnet)
    "f42d8315-1a1e-4eb4-aef1-cbeda245f928",  # testeMarcus (testnet)
    "a91cf0e8-f9d1-409a-bd1b-e83a1ac55a68",  # Test Real Keys (testnet)
    "94b8a494-acd2-40dd-8773-63d7773ab8d1",  # Test Binance Testnet
    "770e8400-e29b-41d4-a716-446655440001",  # Demo Binance Testnet
    "770e8400-e29b-41d4-a716-446655440004",  # Admin Binance Live (outra conta)
    "770e8400-e29b-41d4-a716-446655440003",  # Trader Binance Testnet
    "770e8400-e29b-41d4-a716-446655440002",  # Demo Bybit Testnet
]

async def cleanup_mock_accounts():
    """Remove contas mock/testnet, mantendo apenas a conta real"""
    try:
        await database_manager.connect()
        
        async with database_manager.get_session() as session:
            # 1. Verificar contas existentes
            logger.info("🔍 Verificando contas existentes...")
            result = await session.execute(
                text("SELECT id, name, exchange, environment FROM exchange_accounts ORDER BY created_at")
            )
            accounts = result.fetchall()
            
            logger.info("Contas encontradas:")
            for acc in accounts:
                status = "✅ MANTER" if acc[0] == REAL_ACCOUNT_ID else "❌ REMOVER"
                logger.info(f"  {status} - {acc[1]} ({acc[2]} {acc[3]}) - {acc[0]}")
            
            # 2. Remover posições vinculadas às contas que serão removidas
            logger.info("🗑️ Removendo posições de contas mock...")
            for account_id in ACCOUNTS_TO_REMOVE:
                result = await session.execute(
                    text("DELETE FROM positions WHERE exchange_account_id = :account_id"),
                    {"account_id": account_id}
                )
                if result.rowcount > 0:
                    logger.info(f"  Removidas {result.rowcount} posições da conta {account_id}")
            
            # 3. Remover ordens vinculadas às contas que serão removidas
            logger.info("🗑️ Removendo ordens de contas mock...")
            for account_id in ACCOUNTS_TO_REMOVE:
                result = await session.execute(
                    text("DELETE FROM orders WHERE exchange_account_id = :account_id"),
                    {"account_id": account_id}
                )
                if result.rowcount > 0:
                    logger.info(f"  Removidas {result.rowcount} ordens da conta {account_id}")
            
            # 4. Remover as contas mock
            logger.info("🗑️ Removendo contas mock...")
            for account_id in ACCOUNTS_TO_REMOVE:
                result = await session.execute(
                    text("DELETE FROM exchange_accounts WHERE id = :account_id"),
                    {"account_id": account_id}
                )
                if result.rowcount > 0:
                    logger.info(f"  Removida conta {account_id}")
            
            # 5. Verificar que a conta real ainda existe
            result = await session.execute(
                text("SELECT name, exchange, environment FROM exchange_accounts WHERE id = :account_id"),
                {"account_id": REAL_ACCOUNT_ID}
            )
            real_account = result.fetchone()
            
            if real_account:
                logger.info(f"✅ Conta real confirmada: {real_account[0]} ({real_account[1]} {real_account[2]})")
            else:
                logger.error("❌ ERRO: Conta real não encontrada!")
                return False
            
            await session.commit()
            
            # 6. Verificar resultado final
            result = await session.execute(
                text("SELECT COUNT(*) FROM exchange_accounts")
            )
            final_count = result.fetchone()[0]
            
            logger.info(f"🎉 Limpeza concluída! {final_count} conta(s) restante(s)")
            
            return True
            
    except Exception as e:
        logger.error(f"❌ Erro na limpeza: {e}")
        return False
    finally:
        await database_manager.disconnect()

async def main():
    """Função principal"""
    logger.info("🧹 Iniciando limpeza de contas mock...")
    
    # Confirmação de segurança
    print("\n⚠️  ATENÇÃO: Este script irá:")
    print(f"   - Manter APENAS a conta: 'Teste1 Binance' (mainnet)")
    print(f"   - Remover {len(ACCOUNTS_TO_REMOVE)} contas testnet/mock")
    print(f"   - Remover todas as posições e ordens dessas contas")
    
    # Aguardar confirmação (automaticamente sim em script)
    success = await cleanup_mock_accounts()
    
    if success:
        logger.info("✅ Limpeza concluída com sucesso!")
        print("\n🎉 Sistema configurado para usar apenas conta real mainnet!")
    else:
        logger.error("❌ Falha na limpeza!")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
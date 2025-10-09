"""
Script para adicionar endpoint de modificação de SL/TP no orders_controller.py
"""

# Código do novo endpoint
new_endpoint = '''
@router.patch("/{position_id}/sltp")
async def update_position_sltp(
    position_id: str,
    update_data: dict,
    current_user=Depends(get_current_user)
):
    """
    Atualiza Stop Loss ou Take Profit de uma posição existente
    """
    logger.info(f"📝 Atualizando SL/TP da posição {position_id}")
    logger.info(f"📊 Dados: {update_data}")
    
    try:
        # 1. Buscar a posição no banco
        position = await transaction_db.fetchrow("""
            SELECT 
                p.*,
                ea.api_key,
                ea.api_secret,
                ea.testnet
            FROM positions p
            JOIN exchange_accounts ea ON p.exchange_account_id = ea.id
            WHERE p.id = $1
        """, position_id)
        
        if not position:
            raise HTTPException(status_code=404, detail="Posição não encontrada")
        
        # 2. Descriptografar credenciais
        api_key = decrypt_value(position['api_key'])
        api_secret = decrypt_value(position['api_secret'])
        
        # 3. Conectar à exchange
        connector = BinanceConnector(
            api_key=api_key,
            api_secret=api_secret,
            testnet=position['testnet']
        )
        
        # 4. Determinar qual ordem SL/TP precisa ser modificada
        order_type = update_data.get('type')  # 'stopLoss' ou 'takeProfit'
        new_price = update_data.get('price')
        
        if not order_type or not new_price:
            raise HTTPException(status_code=400, detail="Tipo e preço são obrigatórios")
        
        logger.info(f"🎯 Modificando {order_type} para ${new_price}")
        
        # 5. Buscar ordem SL/TP existente no banco
        sl_tp_type = 'stop_loss' if order_type == 'stopLoss' else 'take_profit'
        
        existing_order = await transaction_db.fetchrow("""
            SELECT id, external_id
            FROM orders
            WHERE symbol = $1
              AND client_order_id LIKE $2
              AND status IN ('new', 'open', 'pending')
            ORDER BY created_at DESC
            LIMIT 1
        """, position['symbol'], f"{sl_tp_type[:2]}_%")
        
        # 6. Cancelar ordem antiga se existir
        if existing_order and existing_order['external_id']:
            logger.info(f"🗑️ Cancelando ordem antiga: {existing_order['external_id']}")
            
            cancel_result = await connector.cancel_futures_order(
                symbol=position['symbol'],
                order_id=existing_order['external_id']
            )
            
            if cancel_result.get('success'):
                # Marcar ordem como cancelada no banco
                await transaction_db.execute("""
                    UPDATE orders
                    SET status = 'canceled',
                        updated_at = $1
                    WHERE id = $2
                """, datetime.utcnow(), existing_order['id'])
                
                logger.info(f"✅ Ordem antiga cancelada")
        
        # 7. Criar nova ordem SL/TP na Binance
        logger.info(f"📝 Criando nova ordem {order_type} @ ${new_price}")
        
        side = 'SELL' if position['side'] == 'long' else 'BUY'
        
        if order_type == 'stopLoss':
            order_params = {
                'symbol': position['symbol'].upper(),
                'side': side,
                'type': 'STOP_MARKET',
                'stopPrice': new_price,
                'closePosition': 'true'
            }
        else:  # takeProfit
            order_params = {
                'symbol': position['symbol'].upper(),
                'side': side,
                'type': 'TAKE_PROFIT_MARKET',
                'stopPrice': new_price,
                'closePosition': 'true'
            }
        
        logger.info(f"🎯 Parâmetros da ordem: {order_params}")
        
        order_result = await asyncio.to_thread(
            connector.client.futures_create_order,
            **order_params
        )
        
        new_order_id = str(order_result.get('orderId'))
        logger.info(f"✅ Nova ordem criada na Binance: {new_order_id}")
        
        # 8. Salvar nova ordem no banco
        client_order_id = f"{sl_tp_type[:2]}_{uuid.uuid4().hex[:16]}"
        
        db_order_id = await transaction_db.fetchval("""
            INSERT INTO orders (
                client_order_id,
                source,
                exchange_account_id,
                external_id,
                symbol,
                side,
                type,
                status,
                quantity,
                stop_price,
                filled_quantity,
                fees_paid,
                time_in_force,
                retry_count,
                reduce_only,
                post_only,
                created_at,
                updated_at
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $17)
            RETURNING id
        """,
            client_order_id,
            'PLATFORM',
            position['exchange_account_id'],
            new_order_id,
            position['symbol'],
            side.lower(),
            'market',  # Compatibilidade com enum
            'new',
            Decimal(str(position['size'])),
            Decimal(str(new_price)),
            Decimal('0'),
            Decimal('0'),
            'gtc',
            0,
            True,  # reduce_only
            False,
            datetime.utcnow()
        )
        
        logger.info(f"✅ Nova ordem salva no banco: {db_order_id}")
        
        return {
            "success": True,
            "message": f"{order_type} atualizado com sucesso",
            "order_id": new_order_id,
            "new_price": new_price
        }
        
    except BinanceAPIException as e:
        logger.error(f"❌ Erro da API Binance: {e}")
        raise HTTPException(status_code=400, detail=f"Erro da Binance: {e.message}")
    except Exception as e:
        logger.error(f"❌ Erro ao atualizar SL/TP: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
'''

print("✅ Código do endpoint criado!")
print("\n📍 Próximo passo: Adicionar manualmente no orders_controller.py")
print(f"\nTotal de linhas: {len(new_endpoint.split(chr(10)))}")

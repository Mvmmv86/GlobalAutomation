#!/usr/bin/env python3
"""
Exemplo de como converter payload TradingView para APIs das exchanges
"""

from typing import Dict, Any, Optional
from enum import Enum


class ExchangeType(str, Enum):
    BINANCE = "binance"
    BYBIT = "bybit"
    OKX = "okx"


class TradingViewPayloadAdapter:
    """Converte payload do TradingView para formato específico de cada exchange"""

    def __init__(self):
        self.adapters = {
            ExchangeType.BINANCE: self._adapt_binance,
            ExchangeType.BYBIT: self._adapt_bybit,
            ExchangeType.OKX: self._adapt_okx,
        }

    def adapt_payload(
        self, tv_payload: Dict[str, Any], exchange: ExchangeType
    ) -> Dict[str, Any]:
        """Adapta payload para exchange específica"""
        if exchange not in self.adapters:
            raise ValueError(f"Exchange {exchange} não suportada")

        return self.adapters[exchange](tv_payload)

    def _adapt_binance(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Adapta para Binance Futures API"""

        # Mapeamento básico
        binance_payload = {
            # Campos obrigatórios
            "symbol": payload["ticker"],
            "side": payload["action"].upper(),  # BUY/SELL
            "type": self._map_order_type_binance(payload.get("order_type", "market")),
            "quantity": str(payload["quantity"]),
            # Configurações de posição
            "positionSide": payload.get("position_side", "BOTH").upper(),
            "timeInForce": payload.get("time_in_force", "GTC"),
            # Risk management
            "reduceOnly": payload.get("reduce_only", False),
            "closePosition": payload.get("close_position", False),
        }

        # Adicionar preço se for limit order
        if payload.get("order_type") == "limit" and "price" in payload:
            binance_payload["price"] = str(payload["price"])

        # Stop Loss / Take Profit
        if payload.get("stop_loss", {}).get("enabled"):
            binance_payload["stopPrice"] = str(payload["stop_loss"]["price"])
            binance_payload["workingType"] = "CONTRACT_PRICE"

        # Configurações avançadas
        if "leverage" in payload:
            # Nota: leverage é configurado separadamente na Binance
            binance_payload["_leverage"] = payload["leverage"]

        if "margin_mode" in payload:
            binance_payload["_marginType"] = payload["margin_mode"].upper()

        return binance_payload

    def _adapt_bybit(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Adapta para Bybit V5 API"""

        bybit_payload = {
            # Identificação
            "category": "linear",  # Futures linear
            "symbol": payload["ticker"],
            "side": payload["action"].capitalize(),  # Buy/Sell
            "orderType": self._map_order_type_bybit(
                payload.get("order_type", "market")
            ),
            "qty": str(payload["quantity"]),
            # Configurações de posição
            "positionIdx": self._get_position_idx(payload.get("position_side")),
            "reduceOnly": payload.get("reduce_only", False),
            "closeOnTrigger": payload.get("close_position", False),
        }

        # Preço para limit orders
        if payload.get("order_type") == "limit" and "price" in payload:
            bybit_payload["price"] = str(payload["price"])

        # Stop Loss / Take Profit
        stop_loss = payload.get("stop_loss", {})
        if stop_loss.get("enabled"):
            bybit_payload["stopLoss"] = str(stop_loss["price"])
            bybit_payload["slTriggerBy"] = "LastPrice"

        take_profit = payload.get("take_profit", {})
        if take_profit.get("enabled"):
            bybit_payload["takeProfit"] = str(take_profit["price"])
            bybit_payload["tpTriggerBy"] = "LastPrice"

        # Configurações específicas
        if "leverage" in payload:
            bybit_payload["_leverage"] = str(payload["leverage"])

        if "margin_mode" in payload:
            bybit_payload["_marginMode"] = (
                1 if payload["margin_mode"] == "isolated" else 0
            )

        return bybit_payload

    def _adapt_okx(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Adapta para OKX API"""

        okx_payload = {
            # Identificação (formato específico OKX)
            "instId": self._map_symbol_okx(payload["ticker"]),
            "side": payload["action"].lower(),  # buy/sell
            "ordType": payload.get("order_type", "market").lower(),
            "sz": str(payload["quantity"]),
            # Configurações de trade
            "tdMode": payload.get("margin_mode", "isolated").lower(),
            "posSide": payload.get("position_side", "long").lower(),
            "ccy": "USDT",  # Currency padrão
        }

        # Preço para limit orders
        if payload.get("order_type") == "limit" and "price" in payload:
            okx_payload["px"] = str(payload["price"])

        # Stop Loss / Take Profit
        stop_loss = payload.get("stop_loss", {})
        if stop_loss.get("enabled"):
            okx_payload["slTriggerPx"] = str(stop_loss["price"])
            okx_payload["slOrdPx"] = "-1"  # Market price

        take_profit = payload.get("take_profit", {})
        if take_profit.get("enabled"):
            okx_payload["tpTriggerPx"] = str(take_profit["price"])
            okx_payload["tpOrdPx"] = "-1"  # Market price

        # Configurações específicas
        if "leverage" in payload:
            okx_payload["_lever"] = str(payload["leverage"])

        return okx_payload

    def _map_order_type_binance(self, order_type: str) -> str:
        """Mapeia tipos de ordem para Binance"""
        mapping = {
            "market": "MARKET",
            "limit": "LIMIT",
            "stop": "STOP_MARKET",
            "stop_limit": "STOP",
        }
        return mapping.get(order_type.lower(), "MARKET")

    def _map_order_type_bybit(self, order_type: str) -> str:
        """Mapeia tipos de ordem para Bybit"""
        mapping = {
            "market": "Market",
            "limit": "Limit",
            "stop": "Stop",
            "stop_limit": "StopLimit",
        }
        return mapping.get(order_type.lower(), "Market")

    def _get_position_idx(self, position_side: Optional[str]) -> int:
        """Mapeia position side para Bybit position index"""
        if not position_side:
            return 0  # One-way mode

        mapping = {
            "long": 1,
            "short": 2,
            "both": 0,
        }
        return mapping.get(position_side.lower(), 0)

    def _map_symbol_okx(self, ticker: str) -> str:
        """Converte ticker para formato OKX"""
        # Exemplo: BTCUSDT -> BTC-USDT-SWAP
        if ticker.endswith("USDT"):
            base = ticker[:-4]  # Remove USDT
            return f"{base}-USDT-SWAP"
        return ticker


# Exemplo de uso
if __name__ == "__main__":
    adapter = TradingViewPayloadAdapter()

    # Payload TradingView expandido
    tv_payload = {
        "ticker": "BTCUSDT",
        "action": "buy",
        "quantity": 0.1,
        "order_type": "market",
        "position_side": "long",
        "leverage": 10,
        "margin_mode": "isolated",
        "stop_loss": {"enabled": True, "price": 44000.00},
        "take_profit": {"enabled": True, "price": 46000.00},
    }

    print("📦 Payload TradingView:")
    print(tv_payload)
    print("\n" + "=" * 50)

    # Adaptar para cada exchange
    for exchange in ExchangeType:
        print(f"\n🏢 {exchange.value.upper()} Payload:")
        adapted = adapter.adapt_payload(tv_payload, exchange)
        print(adapted)

"""Factory for creating exchange adapters"""

from typing import Dict, Type
from infrastructure.external.exchange_adapters import (
    BaseExchangeAdapter,
    BinanceAdapter,
    BybitAdapter,
    ExchangeError,
)


class ExchangeAdapterFactory:
    """Factory for creating exchange adapters"""

    _adapters: Dict[str, Type[BaseExchangeAdapter]] = {
        "binance": BinanceAdapter,
        "bybit": BybitAdapter,
    }

    @classmethod
    def create_adapter(
        cls,
        exchange_name: str,
        api_key: str,
        api_secret: str,
        testnet: bool = False,
        passphrase: str = None,
        **kwargs,
    ) -> BaseExchangeAdapter:
        """Create an exchange adapter instance"""
        exchange_name = exchange_name.lower()

        if exchange_name not in cls._adapters:
            available = ", ".join(cls._adapters.keys())
            raise ExchangeError(
                f"Unsupported exchange: {exchange_name}. Available exchanges: {available}"
            )

        adapter_class = cls._adapters[exchange_name]

        # Create adapter with appropriate parameters
        # Most exchanges only need api_key, api_secret, testnet
        # Some (like KuCoin) also need passphrase
        try:
            if passphrase:
                # Try to create with passphrase first
                return adapter_class(
                    api_key, api_secret, testnet, passphrase=passphrase, **kwargs
                )
            else:
                return adapter_class(api_key, api_secret, testnet, **kwargs)
        except TypeError:
            # Fallback to basic parameters if adapter doesn't support extra params
            return adapter_class(api_key, api_secret, testnet)

    @classmethod
    def get_supported_exchanges(cls) -> list[str]:
        """Get list of supported exchanges"""
        return list(cls._adapters.keys())

    @classmethod
    def register_adapter(
        cls, exchange_name: str, adapter_class: Type[BaseExchangeAdapter]
    ) -> None:
        """Register a new adapter class"""
        cls._adapters[exchange_name.lower()] = adapter_class

    @classmethod
    def is_supported(cls, exchange_name: str) -> bool:
        """Check if exchange is supported"""
        return exchange_name.lower() in cls._adapters

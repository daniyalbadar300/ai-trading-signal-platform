"""Provider errors."""


class ProviderError(Exception):
    """Raised when a market data provider fails to deliver data."""


class SymbolNotFoundError(ProviderError):
    """Raised when the provider does not recognise a symbol."""

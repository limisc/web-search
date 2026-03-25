class ProviderError(Exception):
    def __init__(self, message: str, *, provider: str, error_type: str = "provider_error") -> None:
        super().__init__(message)
        self.provider = provider
        self.error_type = error_type

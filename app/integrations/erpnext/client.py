class ERPNextClient:
    def __init__(self, enabled: bool = False) -> None:
        self.enabled = enabled

    async def sync_customer(self, *_: object, **__: object) -> None:
        if not self.enabled:
            raise NotImplementedError("ERPNext integration is disabled.")
        raise NotImplementedError("ERPNext adapter is reserved for a future module.")


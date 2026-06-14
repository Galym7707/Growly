class BitrixClient:
    def __init__(self, enabled: bool = False) -> None:
        self.enabled = enabled

    async def send_lead(self, *_: object, **__: object) -> None:
        if not self.enabled:
            raise NotImplementedError("Bitrix24 integration is disabled.")
        raise NotImplementedError("Bitrix24 adapter is reserved for a future module.")


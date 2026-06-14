class InstagramClient:
    def __init__(self, enabled: bool = False) -> None:
        self.enabled = enabled

    async def publish(self, *_: object, **__: object) -> None:
        if not self.enabled:
            raise NotImplementedError("Instagram integration is disabled.")
        raise NotImplementedError(
            "Instagram publishing requires a future official API adapter."
        )


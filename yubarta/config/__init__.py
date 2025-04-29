from yubarta.config.settings import Settings


# Inspired by Django
class LazySettings:
    _wrapped = None

    def __getattr__(self, name):
        if self._wrapped is None:
            self._wrapped = Settings()
        return getattr(self._wrapped, name)

    def configure(self, **kwargs):
        self._wrapped = Settings(**kwargs)


settings = LazySettings()

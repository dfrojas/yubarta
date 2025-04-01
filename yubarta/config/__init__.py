from importlib import import_module

# Inspired by Django
class LazySettings:
    def __getattr__(self, name):
        settings_module = import_module("yubarta.config.settings")
        return getattr(settings_module, name)

settings = LazySettings()

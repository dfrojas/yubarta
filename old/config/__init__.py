from typing import Any, Optional

from yubarta.config.settings import Settings


# Inspired by Django
class LazySettings:
    """Lazily‐instantiated proxy around :class:`Settings`.

    This is conceptually similar to Django's ``django.conf.settings``: a global
    settings object that defers instantiation until it is first accessed.  It
    helps avoid configuration overhead during module import time, while keeping
    the convenience of a globally available configuration object.
    """

    _wrapped: Optional[Settings] = None

    def __getattr__(self, name: str) -> Any:  # noqa: D401
        # The first attribute access triggers instantiation of ``Settings``.
        if self._wrapped is None:
            # Pydantic's BaseSettings pulls values from environment variables,
            # therefore a parameter-less construction is perfectly valid at
            # runtime.  However, MyPy is unaware of this mechanism and will
            # complain about the required fields, so we silence it explicitly.
            self._wrapped = Settings()  # type: ignore[call-arg]
        return getattr(self._wrapped, name)

    def configure(self, **kwargs: Any) -> None:
        """Override the underlying :class:`Settings` instance.

        This can be used by tests to inject custom configuration (e.g.
        ``settings.configure(_env_file=".env.test")``).
        """
        self._wrapped = Settings(**kwargs)


# A module-level singleton that is imported throughout the codebase.
settings = LazySettings()

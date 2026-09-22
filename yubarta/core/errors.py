class InvalidTransitionError(ValueError):
    pass


class ConcurrentModificationError(RuntimeError):
    pass


class ConfigurationError(ValueError):
    pass

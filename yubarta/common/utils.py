import hashlib


def generate_fingerprint(source: str, timestamp: str) -> str:
    """
    I choose grouped partition strategy key for Kafka. Like this, we can have more information
    about deduplication.

    TODO: Maybe in the future, the user will be able to choose the partition strategy.
    """
    fingerprint = f"{source}"
    return hashlib.sha256(fingerprint.encode()).hexdigest()

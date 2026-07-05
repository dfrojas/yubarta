from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # APP
    APP_ENV: str = "dev"
    INVENTORY_PATH: str = "inventory.yaml"

    # DB
    DB_USER: str
    DB_PASSWORD: str
    DB_HOST: str
    DB_PORT: int
    DB_NAME: str

    # Kafka
    KAFKA_BOOTSTRAP_SERVERS: str = "kafka:9092"
    KAFKA_ALERT_TOPIC: str = "alerts"
    KAFKA_CONSUMER_GROUP: str = "alert_processor"
    KAFKA_MAX_BATCH_SIZE: int = 1048576
    KAFKA_MAX_WAIT_MS: int = 500
    KAFKA_COMPRESSION_TYPE: str = "gzip"
    KAFKA_ACKS: str = "all"
    KAFKA_RETRIES: int = 3
    KAFKA_RETRY_BACKOFF_MS: int = 100

    @property
    def DATABASE_URI(self) -> str:
        return f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    model_config = SettingsConfigDict(env_file=".env")

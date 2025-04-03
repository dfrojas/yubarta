API_URL = "http://localhost:8080"

DIRECTOR_POLLING_INTERVAL = 1.0
DIRECTOR_BATCH_SIZE = 10

DATABASE_CONFIG = {
    "ENGINE": "postgresql",
    "NAME": "yubarta",
    "USER": "yubarta",
    "PASSWORD": "password",
    "HOST": "postgres",
    "PORT": "5432",
}

def build_database_uri(db_config: dict) -> str:
    """Build a SQLAlchemy connection URL from database configuration dictionary."""
    engine = db_config["ENGINE"]
    
    # For async SQLAlchemy, use asyncpg driver
    if engine == "postgresql":
        engine = "postgresql+asyncpg"
    
    user = db_config["USER"]
    password = db_config["PASSWORD"]
    host = db_config["HOST"]
    port = db_config["PORT"]
    name = db_config["NAME"]
    
    return f"{engine}://{user}:{password}@{host}:{port}/{name}"

DATABASE_URI = build_database_uri(DATABASE_CONFIG)

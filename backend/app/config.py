from pydantic_settings import BaseSettings
from pydantic import model_validator


class Settings(BaseSettings):
    # Railway proporciona DATABASE_URL completa; para dev local se construye desde los vars individuales
    database_url: str = ""
    db_user: str = "postgres"
    db_password: str = "postgres"
    db_host: str = "localhost"
    db_port: int = 5432
    db_name: str = "fichajes_db"

    secret_key: str = "change-me-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    device_api_key: str = "device-secret-token"

    # Orígenes CORS permitidos, separados por coma
    allowed_origins: str = "http://localhost:5173"

    # Usuario admin inicial (usado por seed.py en el primer despliegue)
    admin_username: str = "admin"
    admin_password: str = ""

    @model_validator(mode="after")
    def build_database_url(self):
        import os
        # Leer directamente de os.environ para no depender del orden de carga de pydantic-settings
        url = os.environ.get("DATABASE_URL", "").strip()

        if not url:
            # Fallback: Railway también inyecta PGHOST, PGPORT, PGUSER, PGPASSWORD, PGDATABASE
            pg_host = os.environ.get("PGHOST", "")
            pg_port = os.environ.get("PGPORT", "5432")
            pg_user = os.environ.get("PGUSER", "")
            pg_password = os.environ.get("PGPASSWORD", "")
            pg_db = os.environ.get("PGDATABASE", "")

            if pg_host and pg_user and pg_password and pg_db:
                url = f"postgresql://{pg_user}:{pg_password}@{pg_host}:{pg_port}/{pg_db}"

        if not url:
            # Último fallback: variables individuales DB_* (dev local)
            url = (
                f"postgresql://{self.db_user}:{self.db_password}"
                f"@{self.db_host}:{self.db_port}/{self.db_name}"
            )

        # Railway a veces usa postgres:// en lugar de postgresql://
        if url.startswith("postgres://"):
            url = "postgresql://" + url[len("postgres://"):]

        self.database_url = url
        return self

    model_config = {"env_file": ".env"}


settings = Settings()

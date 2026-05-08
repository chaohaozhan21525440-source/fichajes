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
        if not self.database_url:
            self.database_url = (
                f"postgresql://{self.db_user}:{self.db_password}"
                f"@{self.db_host}:{self.db_port}/{self.db_name}"
            )
        # Railway a veces devuelve postgres:// en lugar de postgresql://
        if self.database_url.startswith("postgres://"):
            self.database_url = "postgresql://" + self.database_url[len("postgres://"):]
        return self

    model_config = {"env_file": ".env"}


settings = Settings()

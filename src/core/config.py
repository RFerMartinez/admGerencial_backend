from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import PostgresDsn, SecretStr

# Ruta dinámica del archivo .env resolviendo 3 niveles hacia arriba (src/core/config.py -> core -> src -> root)
env_path = Path(__file__).resolve().parent.parent.parent / ".env"

class Settings(BaseSettings):
    # -- CONFIG PARA PROYECTO
    PROJECT_TITLE: str
    PROJECT_NAME: str
    PROJECT_DESCRIPTION: str

    # -- CONFIG PARA BASE DE DATOS
    PSQL_SERVER: str
    PSQL_USER: str
    PSQL_PASSWORD: SecretStr
    PSQL_DB: str
    PSQL_PORT: int

    # -- JWT
    SECRET_KEY: str
    ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int
    REFRESH_TOKEN_EXPIRE_DAYS: int

    @property
    def DATABASE_URL(self) -> PostgresDsn:
        return PostgresDsn.build(
            scheme="postgresql",
            username=self.PSQL_USER,
            password=self.PSQL_PASSWORD.get_secret_value(),
            host=self.PSQL_SERVER,
            port=self.PSQL_PORT,
            path=self.PSQL_DB
        )
    
    # Configuración de Pydantic V2 para leer el .env
    model_config = SettingsConfigDict(env_file=env_path, case_sensitive=True)

# módulo para exportar
settings = Settings()
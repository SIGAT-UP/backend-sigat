"""Configuración de la aplicación, leída de variables de entorno."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Variables de entorno de la API.

    Los nombres se mapean sin distinguir mayúsculas: DATABASE_URL -> database_url.
    En Coolify se cargan en Environment Variables, nunca en el repositorio.
    """

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    env: str = "local"
    database_url: str = "postgresql+psycopg://ica:ica_local@localhost:5432/ica"
    jwt_secret: str = "cambiar-por-un-secreto-largo"
    jwt_algorithm: str = "HS256"
    cors_origins: str = "http://localhost:8080"

    @property
    def cors_origin_list(self) -> list[str]:
        return [origen.strip() for origen in self.cors_origins.split(",") if origen.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()

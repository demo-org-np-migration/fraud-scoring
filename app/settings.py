"""Configuración por variables de entorno. Nada de valores hardcodeados: todo sale
del ConfigMap/Secret que arma Kustomize (ver deploy/base y deploy/overlays/*)."""
import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    service_name: str
    env: str
    port: int
    log_level: str
    redis_url: str
    keycloak_issuer: str
    sentinel_url: str
    sentinel_api_key: str


def load_settings() -> Settings:
    return Settings(
        service_name=os.environ.get("SERVICE_NAME", "fraud-scoring"),
        env=os.environ.get("ENV", "staging"),
        port=int(os.environ.get("PORT", "8080")),
        log_level=os.environ.get("LOG_LEVEL", "info"),
        redis_url=os.environ.get("REDIS_URL", "redis://redis:6379/0"),
        keycloak_issuer=os.environ["KEYCLOAK_ISSUER"],
        sentinel_url=os.environ["SENTINEL_URL"],
        sentinel_api_key=os.environ.get("SENTINEL_API_KEY", ""),
    )


settings = load_settings()

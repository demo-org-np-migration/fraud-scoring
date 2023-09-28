import os

# Settings se leen al importar app.settings, así que hay que setear las env vars
# obligatorias ANTES de que cualquier test importe algo de `app`.
os.environ.setdefault("SERVICE_NAME", "fraud-scoring")
os.environ.setdefault("ENV", "test")
os.environ.setdefault("PORT", "8080")
os.environ.setdefault("LOG_LEVEL", "info")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("KEYCLOAK_ISSUER", "http://keycloak.platform.svc:8080/realms/cauri-staging")
os.environ.setdefault("SENTINEL_URL", "http://sandbox.sentinel-fraud.io")
os.environ.setdefault("SENTINEL_API_KEY", "test-key")

# fraud-scoring

Scoring de fraude para pagos. Lo mantiene el equipo de risk. Si `payments-api` te mandó
para acá porque un pago quedó en `review` o `reject`, la explicación de los números está
más abajo y en [`notebooks/umbrales.md`](notebooks/umbrales.md).

## Qué hace

`payments-api` nos llama antes de mover plata. Nosotros combinamos dos señales:

1. **Velocidad**: cuántas veces vimos la cuenta origen en los últimos 10 minutos
   (contador en Redis, `velocity:<from_account>`, con TTL de 600s).
2. **Sentinel**: el vendor antifraude nos devuelve un `risk` entre 0 y 1 para la
   operación (`POST /v2/assess`).

Con eso armamos un score:

```
score = 0.6 * sentinel.risk + 0.4 * min(velocidad / 10, 1)
```

Y una decisión:

| score | decisión |
|---|---|
| `>= 0.85` | `reject` |
| `>= 0.6` | `review` |
| `< 0.6` | `approve` |

Los umbrales salen de un análisis que hicimos con Nico sobre transacciones históricas.
El detalle (por qué 0.6 y no 0.5, por qué el peso 60/40) está en el notebook, no acá:
esto es el README de cómo correr el servicio, no el paper.

## Endpoints

- `POST /v1/score` — lo llama `payments-api` con un token de servicio (rol `service`).
  Body: `{payment_id, from_account, to_account, amount, currency}`. Devuelve
  `{score, decision, signals}`, donde `signals` es algo como
  `["velocity:3", "sentinel:0.42"]` para que backoffice no tenga que adivinar por qué
  se rechazó algo.
- `GET /v1/rules` — cualquier token válido del realm. Devuelve los umbrales actuales,
  útil para que el dashboard de ops no los tenga hardcodeados también.
- `GET /health`, `GET /metrics` — públicos, sin auth.

No tenemos base de datos propia. Todo el estado (los contadores de velocidad) vive en
Redis y expira solo.

## Correr local

Necesitás un Redis:

```
docker run --rm -p 6379:6379 redis:7-alpine
```

Variables de entorno (ver `app/settings.py`):

```
export SERVICE_NAME=fraud-scoring
export ENV=staging
export PORT=8080
export LOG_LEVEL=info
export REDIS_URL=redis://localhost:6379/0
export KEYCLOAK_ISSUER=http://keycloak.platform.svc:8080/realms/cauri-staging
export SENTINEL_URL=http://sandbox.sentinel-fraud.io
export SENTINEL_API_KEY=lo-que-sea-en-local
```

Instalar dependencias y levantar:

```
uv sync --group dev
uv run uvicorn app.main:app --reload --port 8080
```

## Tests

```
uv run pytest
uv run ruff check .
```

`test_scoring.py` prueba la fórmula y los umbrales sin red (Sentinel mockeado).
`test_api.py` prueba que sin token todo lo protegido devuelve `401`, y un happy path
con Sentinel (`respx`) y Redis (`fakeredis`) mockeados.

## Entornos

Desplegamos con Kustomize (`deploy/base` + `deploy/overlays/{staging,prod}`), Argo CD
sincroniza cada overlay a su namespace. La única diferencia entre entornos es el
ConfigMap: `KEYCLOAK_ISSUER` apunta al realm de cada uno, y **staging usa el sandbox de
Sentinel** para no ensuciar las métricas de riesgo del vendor con tráfico de pruebas —
prod es el único que le pega al Sentinel real.

## Deploy

`build.yml` en cada push a `main`: build y push de la imagen a `ghcr.io`, y un
`kustomize edit set image` sobre `deploy/overlays/staging` con commit automático al
propio repo. Un tag `v*` hace lo mismo sobre `deploy/overlays/prod`. Argo CD toma esos
overlays.

— Valentina

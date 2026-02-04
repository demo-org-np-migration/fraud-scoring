"""401 sin token en los endpoints protegidos, y un happy path con Sentinel/Redis
mockeados (respx + fakeredis) para no pegarle a nada real."""
import fakeredis.aioredis
import respx
from fastapi.testclient import TestClient
from httpx import Response

from app import velocity
from app.auth import require_service_role, require_token
from app.main import app
from app.settings import settings

client = TestClient(app)


def test_health_is_public():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_score_without_token_is_401():
    resp = client.post(
        "/v1/score",
        json={
            "payment_id": "p1",
            "from_account": "acc-1",
            "to_account": "acc-2",
            "amount": "100.00",
            "currency": "ARS",
        },
    )
    assert resp.status_code == 401


def test_rules_without_token_is_401():
    resp = client.get("/v1/rules")
    assert resp.status_code == 401
    # las convenciones internas de API §1: el body de error es plano, {"error": {"code", "message"}},
    # no el {"detail": {...}} que arma FastAPI por defecto.
    body = resp.json()
    assert body["error"]["code"] == "unauthorized"
    assert "message" in body["error"]


def test_score_with_invalid_body_is_422_with_contract_envelope():
    app.dependency_overrides[require_service_role] = lambda: {"realm_access": {"roles": ["service"]}}
    try:
        resp = client.post("/v1/score", json={"payment_id": "p1"})  # faltan campos requeridos
        assert resp.status_code == 422
        body = resp.json()
        assert body["error"]["code"] == "validation_error"
        assert "message" in body["error"]
    finally:
        app.dependency_overrides.pop(require_service_role, None)


def test_score_happy_path_uses_vendor_and_velocity(monkeypatch):
    fake_redis = fakeredis.aioredis.FakeRedis(decode_responses=True)
    monkeypatch.setattr(velocity, "get_redis_client", lambda: fake_redis)

    app.dependency_overrides[require_service_role] = lambda: {"realm_access": {"roles": ["service"]}}
    try:
        with respx.mock(assert_all_called=True) as respx_mock:
            respx_mock.post(f"{settings.sentinel_url}/v2/assess").mock(
                return_value=Response(200, json={"risk": 0.1, "signals": []})
            )
            resp = client.post(
                "/v1/score",
                json={
                    "payment_id": "p1",
                    "from_account": "acc-1",
                    "to_account": "acc-2",
                    "amount": "100.00",
                    "currency": "ARS",
                },
            )
        assert resp.status_code == 200
        body = resp.json()
        assert body["decision"] == "approve"
        assert body["signals"] == ["velocity:1", "sentinel:0.1"]
    finally:
        app.dependency_overrides.pop(require_service_role, None)


def test_rules_with_any_valid_token():
    app.dependency_overrides[require_token] = lambda: {"sub": "someone"}
    try:
        resp = client.get("/v1/rules")
        assert resp.status_code == 200
        names = {r["name"] for r in resp.json()}
        assert names == {"reject", "review"}
    finally:
        app.dependency_overrides.pop(require_token, None)

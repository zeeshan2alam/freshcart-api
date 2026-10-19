import os
import tempfile

# must be set before the app modules are imported
os.environ["DATABASE_URL"] = f"sqlite:///{tempfile.mkdtemp()}/test.db"
os.environ["SECRET_KEY"] = "test-secret-key-that-is-at-least-32-bytes-long"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from main import app  # noqa: E402


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def login(client, email, password):
    r = client.post("/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture(scope="module")
def admin(client):
    return login(client, "admin@freshcart.com", "admin123")


@pytest.fixture(scope="module")
def user(client):
    return login(client, "user@freshcart.com", "user123")


ADDRESS = dict(customer_name="Test User", phone="9876543210", address="12 Park Street", city="Mumbai", pincode="400001")


def product_named(client, name):
    return next(p for p in client.get("/products").json() if p["name"] == name)


def test_health_and_seed(client):
    assert client.get("/health").json()["status"] == "ok"
    assert len(client.get("/products").json()) >= 10
    assert any(o["code"] == "FRESH10" for o in client.get("/offers").json())


def test_register_login_me(client):
    r = client.post("/auth/register", json={"name": "Asha", "email": "asha@example.com", "password": "secret1"})
    assert r.status_code == 201 and r.json()["user"]["role"] == "customer"
    assert client.post("/auth/register", json={"name": "Asha", "email": "ASHA@example.com", "password": "secret1"}).status_code == 409
    h = login(client, "asha@example.com", "secret1")
    assert client.get("/auth/me", headers=h).json()["email"] == "asha@example.com"
    assert client.post("/auth/login", json={"email": "asha@example.com", "password": "wrong"}).status_code == 401
    assert client.get("/auth/me").status_code == 401


def test_short_password_rejected(client):
    r = client.post("/auth/register", json={"name": "Bob", "email": "bob@example.com", "password": "123"})
    assert r.status_code == 422


def test_product_crud_is_admin_only(client, admin, user):
    body = {"name": "Mango", "category": "Fruits", "unit": "kg", "price": 150, "stock": 10, "emoji": "🥭"}
    assert client.post("/products", json=body).status_code == 401
    assert client.post("/products", json=body, headers=user).status_code == 403
    created = client.post("/products", json=body, headers=admin)
    assert created.status_code == 201
    pid = created.json()["id"]
    upd = client.put(f"/products/{pid}", json={**body, "price": 160}, headers=admin)
    assert upd.json()["price"] == 160
    assert client.delete(f"/products/{pid}", headers=admin).status_code == 204
    assert client.get(f"/products/{pid}").status_code == 404


def test_order_flow_prices_stock_and_coupon(client, admin, user):
    rice = product_named(client, "Basmati Rice")  # ₹120/kg
    before = rice["stock"]
    r = client.post("/orders", headers=user, json={**ADDRESS, "method": "upi", "coupon": "fresh10",
                                                    "items": [{"product_id": rice["id"], "qty": 2}]})
    assert r.status_code == 201, r.text
    o = r.json()
    assert (o["subtotal"], o["discount"], o["delivery"], o["total"]) == (240, 24, 40, 256)  # <₹500 pays delivery
    assert o["status"] == "Paid" and o["code"].startswith("FC")
    assert product_named(client, "Basmati Rice")["stock"] == before - 2

    big = client.post("/orders", headers=user, json={**ADDRESS, "method": "cod",
                                                      "items": [{"product_id": rice["id"], "qty": 5}]}).json()
    assert big["delivery"] == 0 and big["status"].startswith("Placed")  # ₹600 → free delivery

    mine = client.get("/orders", headers=user).json()
    assert o["code"] in {x["code"] for x in mine}
    assert all(x["user_email"] == "user@freshcart.com" for x in mine)
    assert len(client.get("/orders", headers=admin).json()) > len(mine)


def test_order_rejections(client, user, admin):
    rice = product_named(client, "Basmati Rice")
    paneer = product_named(client, "Paneer")  # stock 0
    base = {**ADDRESS, "method": "cod"}
    assert client.post("/orders", headers=user, json={**base, "items": [{"product_id": paneer["id"], "qty": 1}]}).status_code == 409
    assert client.post("/orders", headers=user, json={**base, "coupon": "NOPE", "items": [{"product_id": rice["id"], "qty": 1}]}).status_code == 400
    assert client.post("/orders", headers=user, json={**base, "phone": "123", "items": [{"product_id": rice["id"], "qty": 1}]}).status_code == 422
    assert client.post("/orders", headers=user, json={**base, "items": [{"product_id": 99999, "qty": 1}]}).status_code == 404
    assert client.post("/orders", headers=admin, json={**base, "items": [{"product_id": rice["id"], "qty": 1}]}).status_code == 403


def test_offers_admin_flow(client, admin, user):
    body = {"text": "Weekend Sale", "emoji": "🛍️", "percent": 15, "code": "wknd15", "theme": "purple"}
    assert client.post("/offers", json=body, headers=user).status_code == 403
    created = client.post("/offers", json=body, headers=admin)
    assert created.status_code == 201 and created.json()["code"] == "WKND15"
    assert client.post("/offers", json=body, headers=admin).status_code == 409
    assert client.post("/offers", json={"text": "x", "code": "ABC"}, headers=admin).status_code == 422  # code needs a %
    oid = created.json()["id"]
    assert client.post("/coupons/validate", json={"code": "wknd15"}).json() == {"valid": True, "code": "WKND15", "percent": 15}
    client.patch(f"/offers/{oid}", json={"active": False}, headers=admin)
    assert oid not in [o["id"] for o in client.get("/offers").json()]
    assert oid in [o["id"] for o in client.get("/offers/all", headers=admin).json()]
    assert client.post("/coupons/validate", json={"code": "WKND15"}).json()["valid"] is False
    assert client.delete(f"/offers/{oid}", headers=admin).status_code == 204


def test_clear_sample_orders(client, admin, user):
    assert any(o["is_sample"] for o in client.get("/orders", headers=admin).json())
    assert client.delete("/orders/sample", headers=user).status_code == 403
    assert client.delete("/orders/sample", headers=admin).status_code == 204
    assert not any(o["is_sample"] for o in client.get("/orders", headers=admin).json())

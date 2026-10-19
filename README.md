# 🛒 FreshCart API

FastAPI backend for the **FreshCart** grocery store: JWT login, products, offers & coupons, orders with server-side pricing and stock control.

- ☁️ Live API: https://freshcart-api-havl.onrender.com (docs at `/docs`) — free Render instance, first request after idle takes ~30–60 s
- 🖥️ Frontend: https://github.com/zeeshan2alam/freshcart-grocery-store
- 🌐 Live frontend: https://zeeshan2alam.github.io/freshcart-grocery-store/
- 📖 Interactive docs: `/docs` on the running API (Swagger UI)

**Stack:** FastAPI · SQLAlchemy 2 · SQLite · PyJWT · Pydantic v2

## Run locally

```bash
python -m venv .venv
.venv\Scripts\activate            # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload
```

Open http://127.0.0.1:8000/docs. On first start the database is created and seeded with an admin, a demo customer, 10 products, a `FRESH10` offer and 30 days of sample orders (flagged `is_sample`).

| Role | Email | Password |
|---|---|---|
| Admin | `admin@freshcart.com` | `admin123` |
| Customer | `user@freshcart.com` | `user123` |

> ⚠️ These are demo credentials. For anything real, set `ADMIN_PASSWORD`, `SECRET_KEY` and `SEED_DEMO_DATA=false` (see `.env.example`).

## Endpoints

| Method | Path | Who | What |
|---|---|---|---|
| GET | `/health` | public | liveness check |
| POST | `/auth/register` | public | create a customer account → token |
| POST | `/auth/login` | public | email + password → token |
| GET | `/auth/me` | logged in | current user |
| GET | `/products` | public | list (`?q=` search, `?category=`) |
| GET | `/products/{id}` | public | one product |
| POST / PUT / DELETE | `/products[/{id}]` | admin | manage products |
| GET | `/offers` | public | active offers (sale marquee) |
| GET | `/offers/all` | admin | all offers |
| POST / PATCH / DELETE | `/offers[/{id}]` | admin | launch, pause/resume, remove |
| POST | `/coupons/validate` | public | `{code}` → `{valid, percent}` |
| POST | `/orders` | customer | place an order |
| GET | `/orders` | logged in | own orders (admin: everyone's) |
| DELETE | `/orders/sample` | admin | remove seeded sample orders |

Send the token as `Authorization: Bearer <token>`.

**Order rules (enforced on the server):** prices come from the database, never the client · coupon discount is applied by the server · delivery is ₹40, free from ₹500 · stock is checked and decremented in the same transaction · payment is **simulated** (only the method is stored, never card / UPI details).

## Tests

```bash
pip install -r requirements-dev.txt
pytest
```

## Configuration

Environment variables, all optional (details in `.env.example`): `SECRET_KEY`, `DATABASE_URL`, `CORS_ORIGINS`, `ADMIN_EMAIL`, `ADMIN_PASSWORD`, `SEED_DEMO_DATA`, `TOKEN_EXPIRE_MINUTES`.

## Deploy on Render

Create a **Web Service** from this repo (or use the included `render.yaml` Blueprint):

- Build command: `pip install -r requirements.txt`
- Start command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
- Health check path: `/health`

On Render's free plan the disk is ephemeral and the service sleeps when idle, so the SQLite data resets on restart and the first request after a sleep takes ~30 s. For permanent data, point `DATABASE_URL` at a managed Postgres.

---

Designed & built with 💚 by **Zeeshan Alam**

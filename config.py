"""Settings, read from environment variables (see .env.example)."""
import os
import secrets

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./freshcart.db")
# No guessable default: without SECRET_KEY a random one is generated per start (logins reset on restart).
SECRET_KEY = os.getenv("SECRET_KEY") or secrets.token_urlsafe(48)
TOKEN_EXPIRE_MINUTES = int(os.getenv("TOKEN_EXPIRE_MINUTES", "720"))
CORS_ORIGINS = [o.strip() for o in os.getenv("CORS_ORIGINS", "*").split(",") if o.strip()]

ADMIN_NAME = os.getenv("ADMIN_NAME", "Admin")
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "admin@freshcart.com").lower()
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")
SEED_DEMO_DATA = os.getenv("SEED_DEMO_DATA", "true").lower() == "true"

# shop rules (kept in sync with the frontend)
FREE_DELIVERY_ABOVE = 500
DELIVERY_FEE = 40

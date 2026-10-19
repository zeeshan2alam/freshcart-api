from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

import auth
import config
import offers
import orders
import products
import seed
from database import Base, engine


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(engine)
    seed.run()
    yield


app = FastAPI(
    title="FreshCart API",
    version="1.0.0",
    description="Backend for the FreshCart grocery store. Designed & built by Zeeshan Alam.",
    lifespan=lifespan,
)

# Auth uses a Bearer token (not cookies), so a wildcard origin is safe; tighten via CORS_ORIGINS in production.
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)

for module in (auth, products, offers, orders):
    app.include_router(module.router)


@app.get("/health", tags=["meta"])
def health():
    return {"status": "ok", "service": "freshcart-api", "version": app.version}


@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse("/docs")

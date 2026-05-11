from __future__ import annotations

import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware

from apps.api_gateway.routes import admin_email, admin_nurture, appointments, dashboard, health, lead_events, leads, messages, sequences, workers
from shared.config.settings import get_settings
from shared.db.session import init_db, seed_defaults

settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    if settings.enable_seeding:
        seed_defaults()
    yield


def create_app() -> FastAPI:
    app = FastAPI(title=settings.app_name, debug=settings.debug, lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(GZipMiddleware, minimum_size=1024)
    if settings.trusted_hosts and settings.trusted_hosts != ["*"]:
        app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.trusted_hosts)

    @app.middleware("http")
    async def request_context_middleware(request: Request, call_next):
        request_id = request.headers.get(settings.request_id_header_name) or str(uuid.uuid4())
        response: Response = await call_next(request)
        response.headers[settings.request_id_header_name] = request_id
        return response

    app.include_router(health.router)
    app.include_router(workers.router)
    app.include_router(leads.router)
    app.include_router(lead_events.router)
    app.include_router(sequences.router)
    app.include_router(messages.router)
    app.include_router(appointments.router)
    app.include_router(dashboard.router)
    app.include_router(admin_email.router)
    app.include_router(admin_nurture.router)
    return app


app = create_app()

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import models  # noqa: F401  — register tables on Base
from app.db import Base, engine
from app.routes import (
    activity,
    admin,
    businesses,
    compile as compile_route,
    conversations,
    health,
    rules,
    test_cases,
)
from app.services import seed

log = logging.getLogger("guardrails")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")


@asynccontextmanager
async def lifespan(_: FastAPI):
    log.info("guardrails backend starting")
    Base.metadata.create_all(bind=engine)
    seed.run_if_empty()
    yield
    log.info("guardrails backend stopping")


app = FastAPI(title="AI Guardrails", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(businesses.router)
app.include_router(rules.router)
app.include_router(compile_route.router)
app.include_router(conversations.router)
app.include_router(activity.router)
app.include_router(test_cases.router)
app.include_router(admin.router)

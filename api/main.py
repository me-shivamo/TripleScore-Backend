import os
import django

# Must happen before any Django ORM imports
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routers import auth, dashboard, nova, diagnostic

ALLOWED_ORIGINS = [
    o.strip()
    for o in os.environ.get("ALLOWED_ORIGINS", "http://localhost:3000").split(",")
    if o.strip()
]

app = FastAPI(
    title="TripleScore API",
    description="Backend API for TripleScore — AI-powered JEE prep platform",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])
app.include_router(nova.router, prefix="/nova", tags=["nova"])
app.include_router(diagnostic.router, prefix="/diagnostic", tags=["diagnostic"])


@app.get("/health")
async def health():
    return {"status": "ok"}

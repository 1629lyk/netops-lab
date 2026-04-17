"""
main.py — FastAPI application entry point.
"""

from fastapi import FastAPI
from src.api.routers import health, devices, configs, compliance
from src.database.session import init_db

app = FastAPI(
    title="NetOps Automation Hub",
    description="Enterprise network automation API — backup, compliance, and device management.",
    version="1.0.0"
)

# Create tables on startup
@app.on_event("startup")
def startup():
    init_db()

# Mount routers
app.include_router(health.router)
app.include_router(devices.router)
app.include_router(configs.router)
app.include_router(compliance.router)

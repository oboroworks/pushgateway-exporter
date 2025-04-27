from fastapi import FastAPI
from src.router import router

def create_app() -> FastAPI:
    app = FastAPI(
        title="Heartbeat Exporter",
        version="0.1.0",
        description="Heartbeat monitoring exporter"
    )
    app.include_router(router)
    return app
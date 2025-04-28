# Copyright (c) 2025, Oboro Works LLC
# All rights reserved.
#
# This source code is licensed under the BSD 3-Clause License found in the
# LICENSE file in the root directory of this source tree.

from fastapi import FastAPI
from src.router import router

def create_app() -> FastAPI:
    app = FastAPI(
        title="Heartbeat Exporter",
        version="0.0.3",
        description="Heartbeat monitoring exporter"
    )
    app.include_router(router)
    return app
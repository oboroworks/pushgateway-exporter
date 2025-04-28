# Copyright (c) 2025, Oboro Works LLC
# All rights reserved.
#
# This source code is licensed under the BSD 3-Clause License found in the
# LICENSE file in the root directory of this source tree.

import json

from fastapi import APIRouter, HTTPException, Request, Response
from src.globals import scraper
from src.utils import json_default_serializer

router = APIRouter()

@router.get("/")
async def get_system_info(request: Request) -> Response:
    return Response(
        content=f'{json.dumps(await scraper.get_configuration(), indent=2, default=json_default_serializer)}\n',
        media_type="application/json",
        status_code=200
    )


@router.get("/probe")
async def probe_service(request: Request):
    if scraper is None:
        raise HTTPException(status_code=500, detail={"error": "Scraper not initialized"})

    service_name = request.query_params.get("target")
    if not service_name:
        raise HTTPException(status_code=400, detail={"error": "Missing 'target' query parameter"})

    status = await scraper.get_service_status(service_name)

    probe_output = (
        "# HELP probe_success Was the probe successful\n"
        "# TYPE probe_success gauge\n"
        f"probe_success {status}\n"
    )
    return Response(content=probe_output, media_type="text/plain; version=0.0.4", status_code=200)

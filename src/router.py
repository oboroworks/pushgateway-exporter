from fastapi import APIRouter, HTTPException, Request, Response
from src.globals import scraper

router = APIRouter()

@router.get("/probe")
async def probe_service(request: Request):
    if scraper is None:
        raise HTTPException(status_code=500, detail={"error": "Scraper not initialized"})

    service_name = request.query_params.get("target")
    if not service_name:
        raise HTTPException(status_code=400, detail={"error": "Missing 'target' query parameter"})

    try:
        status = await scraper.get_service_status(service_name)
    except FileNotFoundError as e:
        probe_output = (
            "# HELP probe_success Was the probe successful\n"
            "# TYPE probe_success gauge\n"
            "probe_success 0\n"
        )
        return Response(content=probe_output, media_type="text/plain; version=0.0.4", status_code=200)

    probe_output = (
        "# HELP probe_success Was the probe successful\n"
        "# TYPE probe_success gauge\n"
        f"probe_success {status}\n"
    )
    return Response(content=probe_output, media_type="text/plain; version=0.0.4", status_code=200)

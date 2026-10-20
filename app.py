"""Run `python app.py` to serve the complete note that app with Python."""
from __future__ import annotations

import argparse
from pathlib import Path

import uvicorn
from fastapi import FastAPI, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.concurrency import run_in_threadpool

from server.documents import DocumentError, MAX_BYTES, import_document

ROOT = Path(__file__).resolve().parent
app = FastAPI(title="note that", version="2.0.0")


@app.get("/api/health")
def health():
    return {"status": "ok", "backend": "python", "formats": ["pdf", "pptx", "png", "jpg", "jpeg", "webp"]}


@app.post("/api/import")
async def upload_document(request: Request, file: UploadFile):
    # Browser uploads are same-origin. Prevent cross-site form submissions from
    # consuming this local application's document-processing resources.
    origin = request.headers.get("origin")
    if origin and origin.rstrip("/") != str(request.base_url).rstrip("/"):
        raise HTTPException(status_code=403, detail="Please import from this app’s own page.")
    try:
        data = await file.read(MAX_BYTES + 1)
        if len(data) > MAX_BYTES:
            raise HTTPException(status_code=413, detail="Please choose a file under 100 MB.")
        return await run_in_threadpool(import_document, file.filename or "document", data)
    except DocumentError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    finally:
        await file.close()


# API paths must never fall through to the frontend HTML.
@app.get("/api/{path:path}", include_in_schema=False)
def unknown_api(path: str):
    return JSONResponse({"detail": "API endpoint not found."}, status_code=404)


if (ROOT / "dist").is_dir():
    app.mount("/", StaticFiles(directory=ROOT / "dist", html=True), name="frontend")
else:
    @app.get("/")
    def build_first():
        return JSONResponse({"detail": "Run npm ci && npm run build first, then restart Python."}, status_code=503)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="A calmer place to study your slides.")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", default=5173, type=int)
    args = parser.parse_args()
    uvicorn.run(app, host=args.host, port=args.port)

from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import FileResponse

router = APIRouter(tags=["dashboard"])

_BASE_DIR = Path(__file__).resolve().parents[1]
_WEB_DIR = _BASE_DIR / "web"
_INDEX_FILE = _WEB_DIR / "index.html"
_TOKEN_FILE = _WEB_DIR / "token.html"


@router.get("/")
def dashboard_home() -> FileResponse:
    return FileResponse(_INDEX_FILE)


@router.get("/token")
def token_detail_page() -> FileResponse:
    return FileResponse(_TOKEN_FILE)

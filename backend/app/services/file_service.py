import re
from pathlib import Path
from fastapi import HTTPException, UploadFile
from app.core.config import DATA_ROOT, settings

ALLOWED = {"matrix": {".docx"}, "xslt": {".xsl", ".xslt"}, "xsd": {".xsd"}, "xml": {".xml"}, "sample_xslt": {".xsl", ".xslt"}}
def safe_name(name: str) -> str:
    name = Path(name or "upload.bin").name
    return re.sub(r"[^A-Za-z0-9._-]", "_", name)[:120] or "upload.bin"

async def save_upload(upload: UploadFile, destination: Path, kind: str) -> Path:
    suffix = Path(upload.filename or "").suffix.lower()
    if suffix not in ALLOWED[kind]:
        raise HTTPException(400, f"Unsupported file type for {kind}. Allowed: {', '.join(sorted(ALLOWED[kind]))}")
    destination.mkdir(parents=True, exist_ok=True)
    target = destination / safe_name(upload.filename or "upload")
    total = 0
    with target.open("wb") as out:
        while chunk := await upload.read(1024 * 1024):
            total += len(chunk)
            if total > settings.upload_max_size_mb * 1024 * 1024:
                out.close(); target.unlink(missing_ok=True)
                raise HTTPException(413, f"File exceeds {settings.upload_max_size_mb} MB limit")
            out.write(chunk)
    if total == 0:
        target.unlink(missing_ok=True)
        raise HTTPException(400, "Uploaded file is empty")
    return target



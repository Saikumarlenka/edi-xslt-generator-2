from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    gemini_api_key: str = ""
    gemini_model: str = "gemini-3.8-flash"
    gemini_fallback_model: str = "gemini-3.8-flash"
    app_env: str = "development"
    backend_host: str = "127.0.0.1"
    backend_port: int = 8000
    frontend_origin: str = "http://localhost:5173"
    upload_max_size_mb: int = 25
    data_dir: str = "./data"
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", case_sensitive=False)

settings = Settings()
DATA_ROOT = Path(settings.data_dir).resolve()
DATA_ROOT.mkdir(parents=True, exist_ok=True)

# Seed the supplied reference assets into the application's runtime reference store.
# They remain editable through the Reference Library UI; uploads replace these copies.
def seed_supplied_references() -> None:
    import shutil
    project_root = Path(__file__).resolve().parents[3]
    archive = project_root / "reference-files"
    if not archive.exists():
        return
    mapping = {
        "210": {
            "210_standard_base.xsl": "standard_xslt",
            "InvoiceCanonicalSchema.xsd": "canonical_xsd",
            "X12_00401_210.xsd": "edi_xsd",
            "210_canonical_test.xml": "canonical_xml",
            "210_mapping_matrix_Sonoco_RXO.docx": "matrix",
        },
        "214": {"214_standard_base.xsl": "standard_xslt"},
    }
    for transaction, files in mapping.items():
        source_dir = archive / transaction
        target_dir = DATA_ROOT / "references" / transaction
        target_dir.mkdir(parents=True, exist_ok=True)
        for filename, key in files.items():
            source = source_dir / filename
            target = target_dir / key
            if source.exists():
                should_copy = not target.exists()
                if not should_copy and key == "standard_xslt":
                    try:
                        content = target.read_text(encoding="utf-8", errors="ignore")
                        if "<msxsl:script" in content or "LoadType" in content or "<B304>PP</B304>" in content:
                            should_copy = True
                        elif source.stat().st_mtime > target.stat().st_mtime:
                            should_copy = True
                    except Exception:
                        should_copy = True
                if should_copy:
                    shutil.copy2(source, target)

seed_supplied_references()

# Backend — EDI XSLT Generator

## Requirements
- Python 3.11+
- LibreOffice (`libreoffice`/`soffice`) on PATH. It is used only to convert DOCX to PDF so Gemini can read the document; Python does not extract DOCX text/tables.
- Google Gemini API key from Google AI Studio.

## Run
```bash
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
copy .env.example .env   # Windows; use cp on macOS/Linux
# Set GEMINI_API_KEY in .env
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```
Open http://127.0.0.1:8000/docs.

## Reference upload keys
For each transaction `210` and `214`, upload these `kind` values to `POST /api/reference-files/{transaction}?kind=...`:
- `standard_xslt` (`.xsl` or `.xslt`)
- `canonical_xsd` (`.xsd`)
- `edi_xsd` (`.xsd`)
- `canonical_xml` (`.xml`)
- optional `sample_xslt` (repeat upload)
- optional `matrix` (`.docx`; generation endpoint also accepts matrix directly)

The stored file slots are `data/references/{210|214}/standard_xslt`, `canonical_xsd`, `edi_xsd`, and `canonical_xml`.

## Important implementation boundary
This is a runnable foundation with Gemini-driven matrix interpretation, schema/XSLT analysis, job tracking, review JSON, and validation. The patch service deliberately does **not** automatically inject model-generated XSLT into arbitrary production maps. Map structures and extension functions differ, and blind insertion can corrupt segment ordering or business logic. It preserves the standard map and reports proposals as unresolved until a map-specific, tested structural patch strategy is implemented. Do not treat a completed job as proof that mapping coverage is complete. Inspect the job report and generated artifacts.

Gemini File API is used with PDF input after LibreOffice conversion. This preserves rendered table layout and reading order better than text extraction, but complex merged tables may still require human review. API file input/model support and quotas can change; verify current Google AI Studio documentation and your model access.

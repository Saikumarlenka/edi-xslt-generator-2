# EDI Studio — AI-assisted EDI 210 / 214 XSLT Generator

React + Vite + JavaScript frontend; FastAPI + Python backend; Gemini through Google's `google-genai` SDK; secure XML/XSD/XSLT processing with `lxml`; Monaco editor and baseline diff review.

## Current status — read before using generated maps

This project is **not yet a fully autonomous, production-ready XSLT generator**. It interprets a matrix with Gemini, analyzes supplied schemas and the baseline map, and applies only constrained XPath/test replacements or records a verified reuse candidate. It does not yet safely insert new EDI segments/templates or add missing null guards automatically. Unsupported requirements remain unresolved rather than being falsely reported as implemented.

The application now checks:
- XSLT XML well-formedness and compilation with `lxml/libxslt`.
- Preservation of baseline namespaces, template signatures, helper/template inventory, and literal output segment sequence.
- Canonical input XSD compatibility and validation where the schema namespace matches the test XML.
- Transformation execution and destination XSD compatibility where the schema namespace matches the output.
- Local X12 structure checks: transaction root, ST/SE presence, ST01 transaction code, ST02/SE02 match, and SE01 segment count.
- A static null/empty-value guard audit.
- Mapping-level applied/reused/unresolved patch traceability.

**Important limitations:**
- These local X12 checks are **Stedi-style checks, not official Stedi validation**. No Stedi API or account is connected. Official validation requires a supported Stedi workflow and validating the actual serialized X12 EDI representation, not just the BizTalk XML wrapper.
- The supplied 210 test run exposed real reference issues: the canonical XSD has no `targetNamespace`, while the sample XML uses `http://Echo.BSSR.Internal.Canonical.InvoiceV2`; the supplied EDI XSD targets `http://schemas.microsoft.com/BizTalk/EDI/X12/2006`, while the XSLT output wrapper uses `http://Echo.BSSR.Schemas.EDI.X12_00401.EDI210/v1.0`. These schemas therefore cannot directly validate those XML roots as supplied.
- The supplied 210 map/test run produced `SE01=210` while the output contained 10 transaction-level segments including ST and SE. The local X12 check correctly fails this. Review whether BizTalk's EDI assembler owns final SE01 calculation in your deployment; do not deploy the generated XML as valid X12 until this is resolved.
- `lxml/libxslt` is not a replacement for the BizTalk runtime. Maps that depend on proprietary `userCSharp` extension functions or BizTalk-specific behavior require runtime testing in BizTalk.
- 214 is not generation-ready until its matrix, canonical Status XSD, EDI 214 XSD, and canonical Status test XML are supplied.

## Requirements
- Python 3.11+
- Node.js 18+
- LibreOffice installed and available as `libreoffice` or `soffice` (DOCX-to-PDF conversion; Python does not extract or interpret DOCX tables)
- Gemini API key from Google AI Studio

## Quick start

### 1. Backend
```bash
cd backend
python -m venv .venv
# Windows PowerShell: .venv\Scripts\Activate.ps1
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
# Windows: copy .env.example .env
# macOS/Linux: cp .env.example .env
```
Edit `backend/.env` and set `GEMINI_API_KEY`. Keep the key on the backend only. Set `GEMINI_MODEL` to a model enabled for your key and current quota.

Run from the `backend` directory:
```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```
API docs: http://127.0.0.1:8000/docs

On startup, supplied reference files are copied into `backend/data/references/` if an active file does not already exist. Uploading through Reference Library replaces the active copy. The source archive remains under `reference-files/`.

### 2. Frontend
In a second terminal:
```bash
cd frontend
npm install
npm run dev
```
Open http://127.0.0.1:5173.

## Workflow
1. Select EDI 210 or 214.
2. Check Reference Library readiness and upload missing references.
3. Upload the relevant matrix DOCX and start analysis.
4. Review Gemini's structured mapping, patch results, validation report, baseline diff, and all unresolved rows.
5. Do not use output in production unless required mappings are implemented, reference/schema mismatches are corrected, and validation succeeds in the real integration runtime.

## Mapping and patch safety
- The matrix is authoritative for business mapping rules, constants, conditions, qualifiers, and exceptions.
- The standard XSLT is authoritative for segment order, namespaces, template patterns, helper templates, and existing BizTalk C# extension-function conventions.
- Only uniquely targeted `replace_select`, `replace_test`, or `reuse_existing` proposals are considered. XSLT compilation is a hard gate; on compile failure the baseline is restored.
- New segments, new templates, reordering, and missing null guards are not silently injected; they remain unresolved until a specific tested structural patch rule is implemented.
- The application does not claim 100% coverage when mappings are unresolved or validation fails.

## Tests
```bash
cd backend
pip install -r requirements.txt
pip install pytest
pytest -q
```
Automated tests use local fixtures and do not call Gemini. Live Gemini usage, quota, and actual BizTalk/Stedi runtime validation must be tested separately.

## Gemini API key
1. Copy `backend/.env.example` to `backend/.env`.
2. Set `GEMINI_API_KEY=your_actual_key`.
3. Restart the backend.

Never put the key in frontend files, commit it, or share it in chat.
